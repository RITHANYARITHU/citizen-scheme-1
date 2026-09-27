"""MCP tools for querying schemes and preparing draft applications."""

from __future__ import annotations

from typing import Any

from database.db import check_eligibility, get_scheme, list_schemes, search_schemes
from utils.drafts import create_application_draft


def find_schemes(query: str, limit: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "id": scheme["id"],
            "name": scheme["name"],
            "name_ta": scheme["name_ta"],
            "summary": scheme["summary"],
            "source_url": scheme["source_url"],
            "application_url": scheme["application_url"],
        }
        for scheme in search_schemes(query, limit=limit)
    ]


def assess_eligibility(scheme_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    scheme = get_scheme(scheme_id)
    if scheme is None:
        raise ValueError(f"Unknown scheme id: {scheme_id}")
    return {
        "scheme_id": scheme_id,
        "scheme_name": scheme["name"],
        "result": check_eligibility(scheme, profile),
        "notice": "Indicative demo rules only; confirm current eligibility with the official department.",
    }


def list_documents(scheme_name: str, citizen_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the scheme's document checklist without collecting sensitive identifiers."""
    scheme = get_scheme(scheme_name)
    if scheme is None:
        matches = [item for item in list_schemes() if item["name"].casefold() == scheme_name.casefold()]
        scheme = matches[0] if matches else None
    if scheme is None:
        raise ValueError(f"Unknown scheme: {scheme_name}")
    return {
        "scheme_name": scheme["name"],
        "required_documents": scheme["documents"],
        "optional_documents": [],
        "document_notes": "Confirm the current checklist with the official department. Do not share Aadhaar, OTP, PIN, or bank credentials here.",
    }


_list_documents = list_documents


def prepare_application_draft(
    scheme_id: str,
    profile: dict[str, Any],
    language: str = "en",
) -> dict[str, str]:
    scheme = get_scheme(scheme_id)
    if scheme is None:
        raise ValueError(f"Unknown scheme id: {scheme_id}")
    return {
        "scheme_id": scheme_id,
        "draft": create_application_draft(scheme, profile, language),
    }


def create_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("The MCP server requires the 'mcp' package. Install project requirements first.") from exc

    server = FastMCP("citizen-scheme-assistant")

    @server.tool()
    def check_eligibility(
        scheme_name: str, citizen_profile: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate a profile against the catalog's indicative criteria."""
        return assess_eligibility(scheme_name, citizen_profile)

    @server.tool()
    def list_documents(
        scheme_name: str, citizen_profile: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """List required and optional documents for a scheme."""
        return _list_documents(scheme_name, citizen_profile)

    @server.tool()
    def fill_application_draft(
        scheme_name: str,
        citizen_profile: dict[str, Any],
        language: str = "en",
    ) -> dict[str, str]:
        """Prepare an editable English or Tamil application letter draft."""
        return prepare_application_draft(scheme_name, citizen_profile, language)

    return server


def serve() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    serve()
