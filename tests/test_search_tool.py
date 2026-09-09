"""
Test Suite: Milestone 1 — Isolated Search Tool Test.

WHY TEST THE TOOL IN ISOLATION?
------------------------------
In agentic AI development, a common debugging mistake is to connect tools to an agent
immediately. When the agent fails or produces low-quality answers, it is hard to tell
whether the LLM hallucinated, the tool failed silently, the network was blocked, or the
prompt was ambiguous.

Testing the search tool directly:
1. Validates external network connectivity and DuckDuckGo response parsing.
2. Confirms the LangChain @tool interface behaves as expected.
3. Does NOT consume any LLM API credits or require an API key.
4. Provides a known, verifiable baseline before building the agent layer.
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'tools' module can be imported cleanly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.search_tool import search_tool


def test_search_tool():
    query = "growth of vlsi industry"
    print("=" * 70)
    print(f"RUNNING TEST: Calling search_tool directly with query: '{query}'")
    print("=" * 70)

    # Calling the tool directly via LangChain's standard .invoke() interface
    raw_result = search_tool.invoke({"query": query})

    print("\n--- ACTUAL TOOL OUTPUT RECEIVED ---")
    print(raw_result)
    print("-" * 70)

    # Assertions to verify the tool actually returned real search results
    assert raw_result, "Tool returned empty output!"
    assert "No results found" not in raw_result, f"Search failed to find results: {raw_result}"
    assert "URL: http" in raw_result, "Output should contain at least one HTTP/HTTPS URL"
    assert "Snippet:" in raw_result, "Output should contain snippet information"

    print("\n[SUCCESS] Milestone 1 verification passed: search tool returned valid real-world results.")


if __name__ == "__main__":
    test_search_tool()
