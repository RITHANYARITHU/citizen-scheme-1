"""LangGraph workflow with a dependency-free equivalent for offline smoke tests."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from database.db import check_eligibility, get_scheme, has_eligibility_details
from rag.store import get_rag_store
from utils.drafts import create_application_draft
from utils.i18n import localize_eligibility_text, message
from web_search.tavily_search import search_web

logger = logging.getLogger(__name__)


class AssistantState(TypedDict, total=False):
    question: str
    profile: dict[str, Any]
    language: str
    requested_scheme_id: str
    request_draft: bool
    enable_web_search: bool
    route: str
    retrieved: list[dict[str, Any]]
    checks: list[dict[str, Any]]
    web: dict[str, Any]
    answer: str
    draft: str


def classify_node(state: AssistantState) -> AssistantState:
    question = state.get("question", "").casefold()
    draft_words = ("draft", "application letter", "விண்ணப்ப வரைவு", "விண்ணப்பம் எழுத")
    want_draft = state.get("request_draft", False) or any(word in question for word in draft_words)
    if want_draft:
        return {"route": "draft"}
    return {"route": "answer" if has_eligibility_details(state.get("profile", {})) else "collect_profile"}


def collect_profile_node(state: AssistantState) -> AssistantState:
    return {
        "checks": [],
        "answer": message(state.get("language", "en"), "enter_profile"),
    }


def retrieve_node(state: AssistantState) -> AssistantState:
    store = get_rag_store()
    results = store.query(state.get("question", ""), limit=5)
    return {"retrieved": results}


def eligibility_node(state: AssistantState) -> AssistantState:
    profile = state.get("profile", {})
    checks = []
    for result in state.get("retrieved", []):
        scheme = result["metadata"]
        checks.append(
            {
                "scheme_id": scheme["id"],
                "scheme_name": scheme["name"],
                "scheme_name_ta": scheme["name_ta"],
                "source_url": scheme["source_url"],
                **check_eligibility(scheme, profile),
            }
        )
    return {"checks": checks}


def web_node(state: AssistantState) -> AssistantState:
    if not state.get("enable_web_search", True):
        return {"web": {"available": False, "results": [], "message": "Web search was not requested."}}
    return {"web": search_web(state.get("question", ""))}


def respond_node(state: AssistantState) -> AssistantState:
    language = state.get("language", "en")
    checks = state.get("checks", [])
    status_for = {
        "possibly_eligible": message(language, "eligible"),
        "unlikely_eligible": message(language, "not_eligible"),
        "needs_more_information": message(language, "need_info"),
        "already_applied": message(language, "applied_status"),
    }
    eligible = [item for item in checks if item["status"] == "possibly_eligible"]
    incomplete = [item for item in checks if item["status"] == "needs_more_information"]
    applied = [item for item in checks if item["status"] == "already_applied"]
    unmatched = [item for item in checks if item["status"] == "unlikely_eligible"]
    lines = []
    for key, group in (
        ("eligible_heading", eligible),
        ("more_details_heading", incomplete),
        ("applied_heading", applied),
        ("not_eligible_heading", unmatched),
    ):
        if not group and key != "eligible_heading":
            continue
        lines.append(f"### {message(language, key)}")
        if not group:
            lines.append(message(language, "no_eligible"))
        for check in group:
            name = check["scheme_name_ta"] if language.lower().startswith("ta") else check["scheme_name"]
            lines.append(f"**{name}** — {status_for[check['status']]}")
            lines.extend(f"- {localize_eligibility_text(reason, language)}" for reason in check["reasons"])
            if check["missing_information"]:
                missing = ", ".join(
                    localize_eligibility_text(item, language) for item in check["missing_information"]
                )
                lines.append(f"{message(language, 'missing_label')}: {missing}")
            lines.append(f"[{message(language, 'official_info')}]({check['source_url']})")
            lines.append("")
    web = state.get("web", {})
    if web.get("results"):
        lines.append("### Recent web results")
        for result in web["results"]:
            lines.append(f"- [{result['title']}]({result['url']}): {result['content'][:280]}")
        lines.append("")
    elif web.get("message"):
        status = web["message"]
        if language.lower().startswith("ta") and not web.get("available"):
            status = message(language, "web_unavailable")
        lines.append(f"_{message(language, 'web_search')}: {status}_")
        lines.append("")
    lines.append(message(language, "disclaimer"))
    return {"answer": "\n".join(lines)}


def draft_node(state: AssistantState) -> AssistantState:
    scheme_id = state.get("requested_scheme_id", "")
    scheme = get_scheme(scheme_id) if scheme_id else None
    if scheme is None:
        retrieved = get_rag_store().query(state.get("question", ""), limit=1)
        scheme = retrieved[0]["metadata"] if retrieved else None
    if scheme is None:
        raise ValueError("No scheme is available to prepare an application draft.")
    draft = create_application_draft(
        scheme,
        state.get("profile", {}),
        state.get("language", "en"),
    )
    return {"draft": draft, "retrieved": [{"metadata": scheme, "id": scheme["id"], "score": 1.0}]}


def _build_langgraph():
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(AssistantState)
    builder.add_node("classify", classify_node)
    builder.add_node("collect_profile", collect_profile_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("eligibility", eligibility_node)
    builder.add_node("web_search", web_node)
    builder.add_node("respond", respond_node)
    builder.add_node("draft", draft_node)
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        lambda state: state["route"],
        {"draft": "draft", "answer": "retrieve", "collect_profile": "collect_profile"},
    )
    builder.add_edge("retrieve", "eligibility")
    builder.add_edge("eligibility", "web_search")
    builder.add_edge("web_search", "respond")
    builder.add_edge("respond", END)
    builder.add_edge("draft", END)
    builder.add_edge("collect_profile", END)
    return builder.compile()


class _LocalWorkflow:
    """Same node routing when LangGraph has not been installed yet."""

    def invoke(self, state: AssistantState) -> AssistantState:
        current = dict(state)
        current.update(classify_node(current))
        if current["route"] == "draft":
            current.update(draft_node(current))
            return current
        if current["route"] == "collect_profile":
            current.update(collect_profile_node(current))
            return current
        for node in (retrieve_node, eligibility_node, web_node, respond_node):
            current.update(node(current))
        return current


def build_workflow():
    try:
        return _build_langgraph()
    except ImportError:
        logger.info("LangGraph is not installed; using the equivalent local workflow runner.")
        return _LocalWorkflow()


def run_assistant(
    question: str,
    profile: dict[str, Any] | None = None,
    language: str = "en",
    requested_scheme_id: str = "",
    request_draft: bool = False,
    enable_web_search: bool = True,
) -> AssistantState:
    graph = build_workflow()
    return graph.invoke(
        {
            "question": question,
            "profile": profile or {},
            "language": language,
            "requested_scheme_id": requested_scheme_id,
            "request_draft": request_draft,
            "enable_web_search": enable_web_search,
        }
    )
