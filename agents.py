"""
Agents Definition for the Multi-Agent Research Assistant Crew.

This module defines the specialized agents that collaborate to conduct research,
analyze findings, and draft comprehensive reports:
1. Researcher: Gathers real-world data and sources using web search.
2. Analyst: Synthesizes raw findings into key patterns, metrics, and tradeoffs.
3. Writer: Formats and polishes findings into an executive-ready report.
"""

import io
import os
import sys

# Disable telemetry and tracing to prevent DNS resolution stalls on Windows
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Task
from crewai.tools.base_tool import Tool
from tools.search_tool import search_tool

# Ensure Windows terminal outputs Unicode/UTF-8 symbols cleanly
if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if isinstance(sys.stderr, io.TextIOWrapper) and sys.stderr.encoding != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ------------------------------------------------------------------------------
# ENVIRONMENT CONFIGURATION
# ------------------------------------------------------------------------------
# WHY: API keys must never be hardcoded in source code.
# Storing credentials in a .env file and reading them via python-dotenv / os.environ
# ensures security, prevents accidental secret leaks, and adheres to 12-Factor App principles.
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "env", ".env"))


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# 1. LLM CONFIGURATION (Groq)
# ------------------------------------------------------------------------------
# Uses the Groq API key (MY_API_KEY) configured in your .env file.
api_key = os.getenv("MY_API_KEY") or os.getenv("GROQ_API_KEY")

def _resolve_crewai_model(raw_name: str) -> str:
    """
    Resolves the model string for CrewAI's OpenAI-compatible provider.
    
    CrewAI splits the model string on the first '/' to detect the provider (e.g. 'openai').
    Models on Groq whose names start with 'openai/' (like 'openai/gpt-oss-120b') need to be
    passed as 'openai/openai/gpt-oss-120b' so CrewAI routes to its OpenAI client while
    forwarding the exact model identifier 'openai/gpt-oss-120b' to Groq.
    """
    raw = raw_name.strip()
    if raw.startswith("openai/"):
        return f"openai/{raw}"
    elif "/" not in raw:
        return f"openai/{raw}"
    return f"openai/{raw}"


if api_key:
    configured_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    llm = LLM(
        model=_resolve_crewai_model(configured_model),
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key.strip(),
        max_tokens=int(os.getenv("MAX_TOKENS", "5000")),
        timeout=120,
    )
else:
    llm = None


# ------------------------------------------------------------------------------
# 2. TOOL ADAPTATION (Bridging LangChain @tool to CrewAI)
# ------------------------------------------------------------------------------
# WHY IS Tool.from_langchain NEEDED?
# In Milestone 1, we built search_tool as a LangChain @tool (StructuredTool) to leverage
# LangChain's clean schema generation and duckduckgo-search integration.
# CrewAI's Agent class strictly validates input tools against `crewai.tools.base_tool.BaseTool`.
# Passing a LangChain StructuredTool directly causes a Pydantic validation error.
# CrewAI provides `Tool.from_langchain(tool)` as an official bridge that wraps the
# LangChain tool into a native CrewAI Tool while preserving its name, docstring schema,
# and callable execution logic.
search_crew_tool = Tool.from_langchain(search_tool)


# ------------------------------------------------------------------------------
# 3. RESEARCHER AGENT DEFINITION
# ------------------------------------------------------------------------------
# WHAT DO ROLE, GOAL, AND BACKSTORY ACTUALLY DO FOR THE AGENT'S BEHAVIOR?
#
# Under the hood, CrewAI synthesizes these three core attributes into the agent's
# system prompt and ReAct (Reasoning + Action) execution loop:
#
# 1. ROLE (Persona & Perspective Framing):
#    - What it does: Defines the agent's job title and area of expertise.
#    - Effect on behavior: Primes the LLM to speak and think from a specific professional
#      standpoint. By setting role="Senior Research Analyst", the LLM adopts a serious,
#      methodical, and evidence-driven mindset rather than answering like a generic chatbot.
#
# 2. GOAL (Objective & Success Criteria):
#    - What it does: Defines the explicit target the agent must achieve.
#    - Effect on behavior: Serves as the agent's compass during its reasoning loop.
#      When deciding whether to call another search query or conclude its work, the agent
#      evaluates whether the accumulated information satisfies this goal.
#
# 3. BACKSTORY (Behavioral Guardrails & Motivation):
#    - What it does: Sets narrative context, operational standards, and negative constraints.
#    - Effect on behavior: Dictates *how* the agent pursues its goal. Here we explicitly
#      instruct the agent to never speculate from memory, always invoke its search tool for
#      real-world facts, gather statistical data, and preserve exact source URLs.
#
# 4. VERBOSE=TRUE:
#    - Prints the agent's internal thought process, tool calls with arguments, and tool
#      outputs directly to stdout, allowing us to inspect and verify tool invocation.
#
researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments, real-world data, and detailed insights on {topic}",
    backstory=(
        "You are an elite, highly methodical research analyst with a reputation for precision. "
        "You never rely on unverified assumptions or out-of-date knowledge; instead, you actively "
        "use your search tool to gather real-world facts, recent developments, and reliable sources. "
        "You extract specific data points, statistics, case studies, and concrete examples, "
        "always documenting the source URLs for every finding."
    ),
    llm=llm,
    tools=[search_crew_tool],
    verbose=True,
    memory=False,
    max_iter=3,
)


# ------------------------------------------------------------------------------
# 4. ANALYST AGENT DEFINITION
# ------------------------------------------------------------------------------
# WHY DOES THE ANALYST NOT NEED THE SEARCH TOOL?
#
# 1. Separation of Concerns (Single Responsibility Principle):
#    In multi-agent systems, agents are most reliable when restricted to a single cognitive mode.
#    The Researcher handles information retrieval from the external web.
#    The Analyst handles internal synthesis: filtering noise, identifying patterns, comparing
#    trade-offs, and grouping data into clear thematic insights.
#
# 2. Scope Containment & Avoiding Query Drift:
#    If the Analyst had web search access, it might second-guess the Researcher's findings,
#    trigger redundant search queries, burn unnecessary API tokens, and drift away from the
#    specific corpus assembled by the Researcher.
#
# 3. Grounded Deduction:
#    Working strictly on the text handed to it forces the Analyst to base all conclusions,
#    statistical summaries, and SWOT evaluations directly on factual evidence gathered upstream.
analyst = Agent(
    role="Senior Insights & Data Analyst",
    goal="Critically analyze and synthesize raw research findings on {topic} into key trends, metrics, and actionable conclusions",
    backstory=(
        "You are a sharp, analytical data strategist with a talent for finding order in chaos. "
        "You take raw, unstructured research notes and filter out the noise to isolate genuine signal. "
        "You identify overarching trends, synthesize comparative metrics, assess practical trade-offs, "
        "and produce structured, high-signal briefings that serve as the foundation for executive reports. "
        "You never speculate beyond the verified evidence provided to you."
    ),
    llm=llm,
    tools=[],  # No external search tool needed: operates solely on handed-down research text
    verbose=True,
    memory=False,
    max_iter=3,
)


# ------------------------------------------------------------------------------
# 5. WRITER AGENT DEFINITION
# ------------------------------------------------------------------------------
# WHY DOES THE WRITER NOT NEED THE SEARCH TOOL?
#
# 1. Specialized Editorial Focus:
#    The Writer's sole mission is linguistic precision, narrative clarity, structural flow,
#    and professional polish. Its expertise is editorial synthesis, not web scraping or data gathering.
#
# 2. Prevention of Hallucination and Conflicting Data:
#    If the Writer had access to search tools, it could pull in new, unvetted snippets that
#    contradict the Researcher's and Analyst's findings. By constraining its input to the vetted
#    analysis, the Writer guarantees complete fidelity to the upstream evidence.
#
# 3. Deterministic Pipeline:
#    A linear data flow (Search -> Analysis -> Writing) guarantees a clean, predictable pipeline
#    where each agent refines and elevates the work of the previous agent without cyclic loops.
writer = Agent(
    role="Principal Technical Report Writer",
    goal="Craft a compelling, comprehensive, and beautifully formatted executive report on {topic} based on vetted research and analysis",
    backstory=(
        "You are an acclaimed technical writer and editorial strategist known for transforming "
        "dense technical data and analytical points into publication-grade executive briefs. "
        "You structure documents logically with executive summaries, clear thematic sections, "
        "impactful bullet points, and actionable takeaways, while ensuring that all source URLs "
        "and statistics from the research are cleanly cited and preserved."
    ),
    llm=llm,
    tools=[],  # No external search tool needed: operates solely on analyzed text
    verbose=True,
    memory=False,
    max_iter=3,
)


# ------------------------------------------------------------------------------
# STANDALONE TEST RUNNER (Milestone 2 Verification)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    test_topic = "growth of vlsi industry"
    print("\n" + "=" * 80)
    print("RUNNING RESEARCHER AGENT STANDALONE TEST")
    print(f"Topic: {test_topic}")
    print("=" * 80 + "\n")

    # Guard check: Ensure an API key is configured
    if not api_key:
        print("ERROR: No API key found.")
        print("Please set MY_API_KEY in your env/.env file.")
        exit(1)

    # Define the isolated research task for this agent
    research_task = Task(
        description=(
            f"Conduct thorough web research on: '{test_topic}'.\n"
            "Use the search tool (1-2 queries) to find real-world statistics, key benefits, common challenges, "
            "and notable company case studies.\n"
            "Synthesize your findings into a comprehensive research report and include cited source URLs."
        ),
        expected_output=(
            "A structured research brief containing key findings, statistics, practical examples, "
            "and cited source URLs."
        ),
        agent=researcher,
    )

    # Execute the agent alone using a single-agent crew runner
    test_crew = Crew(
        agents=[researcher],
        tasks=[research_task],
        verbose=True,
    )

    result = test_crew.kickoff(inputs={"topic": test_topic})

    print("\n" + "=" * 80)
    print("ACTUAL OUTPUT FROM RESEARCHER AGENT:")
    print("=" * 80)
    print(result)
