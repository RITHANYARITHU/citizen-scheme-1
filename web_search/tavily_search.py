"""Tavily web search with a visible, non-fatal offline fallback."""

from __future__ import annotations

import logging
from typing import Any

from config import get_settings

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 4) -> dict[str, Any]:
    settings = get_settings()
    if settings.demo_mode:
        return {
            "available": False,
            "results": [],
            "message": "Demo mode is enabled; using local scheme information only.",
        }
    if not settings.tavily_api_key:
        return {
            "available": False,
            "results": [],
            "message": "Tavily key is not configured; using the local scheme database.",
        }
    try:
        from tavily import TavilyClient
    except ImportError:
        message = "Tavily search is configured but tavily-python is not installed."
        logger.warning(message)
        return {"available": False, "results": [], "message": message}
    try:
        response = TavilyClient(api_key=settings.tavily_api_key).search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=False,
        )
    except Exception as exc:
        logger.warning("Tavily request failed: %s", exc)
        return {
            "available": False,
            "results": [],
            "message": f"Tavily request failed; local results are still available ({type(exc).__name__}).",
        }
    results = [
        {
            "title": item.get("title", "Web result"),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        }
        for item in response.get("results", [])
    ]
    return {
        "available": True,
        "results": results,
        "message": "Tavily search completed." if results else "Tavily returned no results.",
    }
