from __future__ import annotations
import requests

_DDG_URL = "https://api.duckduckgo.com/"
_TIMEOUT = 8


def search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search DuckDuckGo and return up to max_results text snippets.

    Returns a list of {"title": ..., "snippet": ..., "url": ...} dicts.
    Falls back to an empty list on any network error.
    """
    params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
    try:
        resp = requests.get(_DDG_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results: list[dict[str, str]] = []
    # Instant answer
    if data.get("AbstractText"):
        results.append(
            {
                "title": data.get("Heading", ""),
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL", ""),
            }
        )
    # Related topics
    for topic in data.get("RelatedTopics", []):
        if len(results) >= max_results:
            break
        if "Text" in topic:
            results.append(
                {
                    "title": topic.get("Text", "")[:80],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                }
            )

    return results[:max_results]
