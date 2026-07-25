import os
import logging

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

logger = logging.getLogger(__name__)


client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


class WebSearchError(Exception):
    """Raised when the web search fallback fails. Callers (app.py) can
    catch this specifically to show a friendly message, same as the
    existing Groq error handling."""


def search_web(query: str):
    """Search the web via Tavily and return (context, source_urls).

    Network calls to a third-party API can fail for all sorts of
    reasons (bad/missing key, Tavily outage, timeout, query rejected).
    Previously any of these would raise an unhandled exception all the
    way up through app.py's Hybrid-mode fallback path. We now catch
    everything here, log the real error server-side, and raise a
    single clear WebSearchError so the UI can show a friendly message
    instead of a raw traceback.
    """
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5
        )
    except Exception as e:
        logger.exception("Tavily web search failed for query: %r", query)
        raise WebSearchError(
            "Web search is temporarily unavailable. Please try again in a moment."
        ) from e

    context = ""
    sources = []

    for result in response.get("results", []):
        title = result.get("title", "")
        content = result.get("content", "")
        url = result.get("url")

        context += f"Title: {title}\nContent: {content}\n\n"

        if url:
            sources.append(url)

    return context, sources


if __name__ == "__main__":

    context, sources = search_web(
        "Best coding model in 2026"
    )

    print(context)

    print(sources)
