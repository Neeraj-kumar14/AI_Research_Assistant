import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


def search_web(query: str):

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=5
    )

    context = ""

    sources = []

    for result in response["results"]:

        context += (
            f"Title: {result['title']}\n"
            f"Content: {result['content']}\n\n"
        )

        sources.append(result["url"])

    return context, sources

if __name__ == "__main__":

    context, sources = search_web(
        "Best coding model in 2026"
    )

    print(context)

    print(sources)