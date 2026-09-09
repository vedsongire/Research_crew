"""
DuckDuckGo Search Tool for Multi-Agent Research Crew.

WHY IS THIS STRUCTURED AS A LANGCHAIN @tool?
-------------------------------------------
1. Tool Abstraction:
   Large Language Models (LLMs) cannot browse the live web on their own. To give an LLM
   access to external capabilities (like web search), we define a "tool".

2. Automatic Schema Generation:
   The LangChain `@tool` decorator inspects the function's name, type annotations,
   and docstring to automatically produce an OpenAI/Anthropic-compatible tool schema
   (JSON schema). For example:
   {
       "name": "search_tool",
       "description": "Searches the web using DuckDuckGo...",
       "parameters": {
           "type": "object",
           "properties": {
               "query": {"type": "string", "description": "The search query string"}
           },
           "required": ["query"]
       }
   }

WHAT WILL THE LLM SEE?
----------------------
1. System Prompt / Tool Schema:
   Before execution, the LLM receives the tool's name, description, and argument schema.
   When the LLM determines it needs up-to-date web information to fulfill a task, it
   generates a structured tool call: `search_tool(query="...")`.

2. Tool Execution Output:
   The framework executes this function with the LLM's arguments and feeds the return
   string directly back into the LLM's conversation context as an observation.
   The LLM will see a clean, formatted list of the top search results, each containing:
   - Title: The headline of the web page.
   - URL: The direct link to the source (essential for citation).
   - Snippet: A summary of the page content answering or relating to the query.
"""

import warnings
from urllib.parse import parse_qs, urlparse
from langchain.tools import tool

# Suppress harmless package rename notice from duckduckgo_search library
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*", category=RuntimeWarning)
from duckduckgo_search import DDGS
from lxml.html import document_fromstring


def _perform_duckduckgo_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """
    Executes a search against DuckDuckGo using the DDGS client and extracts top results.

    DuckDuckGo provides HTML search endpoints that return search results containing
    title, source URL, and descriptive snippet.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        ddgs = DDGS()

        # Query DuckDuckGo's HTML search endpoint using the DDGS HTTP client session
        response = ddgs._get_url(
            "GET",
            "https://html.duckduckgo.com/html/",
            params={"q": query}
        )

        tree = document_fromstring(response.content, ddgs.parser)
        result_elements = tree.xpath("//div[contains(@class, 'result__body')]")

        results: list[dict[str, str]] = []
        for elem in result_elements:
            # Extract title and raw redirect href
            title_nodes = elem.xpath(".//a[contains(@class, 'result__a')]")
            title = title_nodes[0].text_content().strip() if title_nodes else ""
            raw_href = title_nodes[0].get("href", "") if title_nodes else ""

            # DuckDuckGo wraps outbound links in a redirect URL (//duckduckgo.com/l/?uddg=<url>)
            # We unwrap the 'uddg' query parameter to provide the actual destination URL to the LLM.
            if "uddg=" in raw_href:
                url = parse_qs(urlparse(raw_href).query).get("uddg", [""])[0]
            else:
                url = raw_href

            # Extract snippet text
            snippet_nodes = elem.xpath(".//a[contains(@class, 'result__snippet')]")
            snippet = snippet_nodes[0].text_content().strip() if snippet_nodes else ""

            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })

            if len(results) >= max_results:
                break

        return results


@tool
def search_tool(query: str) -> str:
    """Search the web using DuckDuckGo for a given query string.
    Returns the top search results including title, snippet, and source URL.
    Use this tool whenever you need up-to-date facts, news, or external information.
    """
    try:
        results = _perform_duckduckgo_search(query, max_results=5)
    except Exception as e:
        return f"Search temporary notice: unable to fetch live results for '{query}' due to: {e}. Please utilize findings already gathered."

    if not results:
        return f"No results found for query: '{query}'"

    # Format the results into a clean, human-and-LLM-readable text block.
    # LLMs reason best when each search result is clearly demarcated with its metadata.
    formatted_chunks = []
    for i, res in enumerate(results, start=1):
        chunk = (
            f"[{i}] {res['title']}\n"
            f"URL: {res['url']}\n"
            f"Snippet: {res['snippet']}"
        )
        formatted_chunks.append(chunk)

    return "\n\n".join(formatted_chunks)
