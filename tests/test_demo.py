from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from database.db import check_eligibility, initialize_database, list_schemes
from graph.workflow import run_assistant
from mcp_server.server import (
    assess_eligibility,
    create_server,
    find_schemes,
    list_documents,
    prepare_application_draft,
)
from rag.store import ChromaCompatibleStore, LocalRAGStore
from utils.drafts import create_application_draft
from web_search.tavily_search import search_web


def test_database_seeds_and_is_idempotent(tmp_path):
    db_path = tmp_path / "schemes.sqlite3"
    initialize_database(db_path)
    initialize_database(db_path)
    schemes = list_schemes(db_path)
    assert len(schemes) >= 8
    assert len({scheme["id"] for scheme in schemes}) == len(schemes)


def test_local_retrieval_finds_student_schemes(tmp_path):
    results = LocalRAGStore(tmp_path / "schemes.sqlite3").query("Tamil Nadu student scholarship", limit=3)
    assert results
    assert any("student" in item["metadata"]["tags"] for item in results)


def test_chroma_compatible_retrieval_uses_local_embeddings(tmp_path):
    pytest.importorskip("chromadb")
    store = ChromaCompatibleStore(tmp_path / "chroma", tmp_path / "schemes.sqlite3")
    results = store.query("student scholarship", limit=3)
    assert results
    assert all(item["metadata"]["source_url"].startswith("https://") for item in results)


def test_unknown_eligibility_data_stays_unknown(tmp_path):
    schemes = list_schemes(tmp_path / "schemes.sqlite3")
    scheme = next(item for item in schemes if item["id"] == "pudhumai-penn")
    result = check_eligibility(scheme, {})
    assert result["status"] == "needs_more_information"
    assert "state" in result["missing_information"]
    assert "government school background" in result["missing_information"]

    scholarship = next(item for item in schemes if item["id"] == "post-matric-scholarship-sc")
    scholarship_result = check_eligibility(scholarship, {"category": "SC", "is_student": True})
    assert "studying beyond matriculation" in scholarship_result["missing_information"]


def test_known_negative_eligibility_check_is_not_reported_as_possible(tmp_path):
    scheme = next(item for item in list_schemes(tmp_path / "schemes.sqlite3") if item["id"] == "pmjay")
    result = check_eligibility(scheme, {"beneficiary_database_match": False})
    assert result["status"] == "unlikely_eligible"
    assert result["reasons"] == ["A beneficiary database match is required"]


def test_prior_application_blocks_only_that_scheme(tmp_path):
    schemes = {item["id"]: item for item in list_schemes(tmp_path / "schemes.sqlite3")}
    profile = {
        "occupation": "farmer",
        "has_land": True,
        "previously_applied_scheme_ids": ["pm-kisan"],
    }
    prior = check_eligibility(schemes["pm-kisan"], profile)
    assert prior["status"] == "already_applied"
    assert "already applied" in prior["reasons"][0].lower()
    assert "official" in prior["reasons"][0].lower()
    assert check_eligibility(schemes["tn-farmer-subsidy"], profile)["status"] != "already_applied"


def test_no_profile_does_not_return_eligible_list(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "empty-profile.sqlite3"))
    response = run_assistant("student scholarship", {}, "en", enable_web_search=False)
    assert response["checks"] == []
    assert "profile" in response["answer"].lower()
    assert "potentially relevant" not in response["answer"].lower()
    prior_only = run_assistant(
        "farmer",
        {"previously_applied_scheme_ids": ["pm-kisan"], "name": "Demo Person"},
        "en",
        enable_web_search=False,
    )
    assert prior_only["checks"] == []


def test_workflow_separates_eligible_incomplete_and_prior_applications(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "prior.sqlite3"))
    response = run_assistant(
        "farmer",
        {"occupation": "farmer", "has_land": True, "previously_applied_scheme_ids": ["pm-kisan"]},
        "en",
        enable_web_search=False,
    )
    assert any(item["scheme_id"] == "pm-kisan" and item["status"] == "already_applied" for item in response["checks"])
    assert "Previously applied" in response["answer"]
    assert "Not eligible for a new application" in response["answer"]
    assert "Need more details" in response["answer"]
    eligible_section = response["answer"].split("### Eligible schemes")[1].split("### Need more details")[0]
    assert "PM-KISAN" not in eligible_section
    new_applicant = run_assistant(
        "farmer", {"occupation": "farmer", "has_land": True, "state": "Tamil Nadu"},
        "en", enable_web_search=False,
    )
    eligible_section = new_applicant["answer"].split("### Eligible schemes")[1].split("_Web search")[0]
    assert "PM-KISAN" in eligible_section
    assert "Previously applied" not in new_applicant["answer"]


def test_tamil_explains_prior_application(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "tamil.sqlite3"))
    response = run_assistant(
        "farmer", {"occupation": "farmer", "previously_applied_scheme_ids": ["pm-kisan"]},
        "ta", enable_web_search=False,
    )
    assert "முன்பே விண்ணப்பித்த திட்டங்கள்" in response["answer"]
    assert "முன்பே விண்ணப்பித்ததாக" in response["answer"]


def test_eligibility_rejects_malformed_structured_profile(tmp_path):
    scheme = next(item for item in list_schemes(tmp_path / "schemes.sqlite3") if item["id"] == "pm-kisan")
    with pytest.raises(ValueError, match="profile.has_land must be a boolean"):
        check_eligibility(scheme, {"occupation": "farmer", "has_land": "no"})


def test_draft_uses_profile_and_official_link(tmp_path):
    scheme = next(item for item in list_schemes(tmp_path / "schemes.sqlite3") if item["id"] == "pm-kisan")
    draft = create_application_draft(scheme, {"name": "Demo Applicant", "age": 40}, "en")
    assert "Demo Applicant" in draft
    assert scheme["application_url"] in draft
    assert "விண்ணப்ப" in create_application_draft(scheme, {}, "ta")


def test_workflow_answer_and_conditional_draft_routes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "flow.sqlite3"))
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    response = run_assistant("student scholarship", {"is_student": True}, "en", enable_web_search=False)
    assert response["route"] == "answer"
    assert response["checks"]
    assert "Official information" in response["answer"]

    draft = run_assistant(
        "application draft",
        {"name": "Test User"},
        "ta",
        requested_scheme_id="pm-kisan",
        request_draft=True,
        enable_web_search=False,
    )
    assert draft["route"] == "draft"
    assert "Test User" in draft["draft"]
    assert "வரைவு" in draft["draft"]


def test_tavily_missing_key_is_local_fallback(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("DEMO_MODE", "false")
    result = search_web("housing support")
    assert result["available"] is False
    assert result["results"] == []
    assert "not configured" in result["message"].lower()


def test_demo_mode_never_calls_tavily_even_if_key_is_present(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("TAVILY_API_KEY", "placeholder")
    result = search_web("housing support")
    assert result["available"] is False
    assert "demo mode" in result["message"].lower()


def test_tavily_request_error_keeps_local_fallback(monkeypatch):
    class BrokenClient:
        def __init__(self, api_key):
            self.api_key = api_key

        def search(self, **kwargs):
            raise TimeoutError("offline test")

    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("TAVILY_API_KEY", "placeholder")
    monkeypatch.setitem(sys.modules, "tavily", SimpleNamespace(TavilyClient=BrokenClient))
    result = search_web("housing support")
    assert result["available"] is False
    assert result["results"] == []
    assert "TimeoutError" in result["message"]


def test_mcp_tools_use_local_seed_data():
    results = find_schemes("student scholarship", limit=3)
    assert results
    assert all(item["application_url"].startswith("https://") for item in results)

    eligibility = assess_eligibility("pudhumai-penn", {"state": "Tamil Nadu", "gender": "female"})
    assert eligibility["result"]["status"] == "needs_more_information"
    assert prepare_application_draft("pm-kisan", {"name": "MCP User"})["draft"].find("MCP User") >= 0


def test_mcp_server_registers_all_tools():
    server = create_server()
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == {
        "check_eligibility",
        "list_documents",
        "fill_application_draft",
    }


def test_mcp_document_tool_returns_required_documents():
    result = list_documents("pm-kisan", {})
    assert result["required_documents"]
    assert "scheme_name" in result
