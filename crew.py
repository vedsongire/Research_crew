"""
Crew Definition and Pipeline Orchestration for the Multi-Agent Research Assistant.

This module sets up the end-to-end multi-agent workflow:
1. Defines one specialized Task per agent (Research, Analysis, Writing).
2. Chains tasks sequentially using the `context=` parameter.
3. Assembles the Crew using `Process.sequential`.
"""

import io
import os
import sys

# Disable telemetry and tracing to prevent DNS resolution stalls on Windows
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"

from crewai import Crew, Process, Task
from agents import researcher, analyst, writer, api_key

# Ensure Windows terminal outputs Unicode/UTF-8 symbols cleanly during verbose logging
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
# 1. TASK DEFINITIONS (One Task per Agent)
# ------------------------------------------------------------------------------
# WHY ARE TASK DESCRIPTIONS AND EXPECTED OUTPUTS SO SPECIFIC?
#
# In CrewAI, each Task acts as an instruction set and boundary for an Agent's ReAct cycle:
# - `description`: Tells the agent what actions to perform, what tools to call, and what constraints
#   to honor (e.g. "perform 1-2 searches", "cite source URLs").
# - `expected_output`: Defines the completion criteria. The LLM continuously evaluates its progress
#   against this expected structure before deciding its final answer is ready.
# - `context`: A list of prerequisite tasks whose final outputs are injected into this task's prompt.
#   This ensures explicit data lineage and state propagation between pipeline steps.

# Task 1: Web Research Task
# Assigned to: researcher
# Does NOT use context because it is the initial root task that discovers raw external data.
def create_research_tasks():
    """
    Factory function that creates fresh Task instances for the Research Crew.

    WHY A FACTORY INSTEAD OF STATIC SINGLETONS?
    In a REST API environment (FastAPI), multiple requests may arrive sequentially or concurrently.
    CrewAI tasks mutate during execution (storing outputs and execution metadata). Creating fresh
    Task instances for each execution prevents state leakage and cache pollution across requests.
    """
    t1 = Task(
        description=(
            "Conduct thorough web research on the topic: '{topic}'.\n"
            "Use the search tool to find:\n"
            "1. Current industry trends and key market statistics.\n"
            "2. Concrete benefits and real-world advantages.\n"
            "3. Core challenges, limitations, or adoption barriers.\n"
            "4. Real-world company case studies or practical implementations.\n"
            "CRITICAL REQUIREMENT: For every major finding, retain the exact source URL from the search results."
        ),
        expected_output=(
            "A structured raw research brief containing detailed findings, specific statistics, "
            "case study examples, and an explicit list of cited source URLs."
        ),
        agent=researcher,
    )

    t2 = Task(
        description=(
            "Carefully analyze the raw research notes provided on '{topic}'.\n"
            "Your objectives:\n"
            "1. Filter out redundant noise and identify the most significant underlying patterns.\n"
            "2. Break down findings into categorized thematic pillars (e.g., operational impact, economic ROI, tech hurdles).\n"
            "3. Evaluate the trade-offs: compare the promised benefits against practical implementation challenges.\n"
            "4. Preserve all relevant statistics, case study details, and source URLs provided by the researcher."
        ),
        expected_output=(
            "A structured analytical briefing featuring categorized thematic insights, a balanced "
            "pros/cons evaluation, distilled key metrics, and preserved source URLs."
        ),
        agent=analyst,
        context=[t1],
    )

    t3 = Task(
        description=(
            "Review the structured analysis and research on '{topic}'.\n"
            "Draft a polished, comprehensive, publication-ready executive report formatted in clean Markdown.\n"
            "The report MUST include:\n"
            "- Title and Executive Summary (high-level synthesis of findings).\n"
            "- Market Overview & Current Trends (with specific statistics).\n"
            "- Key Benefits & Strategic Advantages.\n"
            "- Implementation Challenges & Risk Factors.\n"
            "- Real-World Case Studies / Industry Examples.\n"
            "- Future Outlook & Strategic Recommendations.\n"
            "- References / Sources Section listing all cited URLs."
        ),
        expected_output=(
            "A comprehensive, beautifully formatted Markdown executive research report with clear headings, "
            "bullet points, numerical data, strategic takeaways, and a complete cited sources section."
        ),
        agent=writer,
        context=[t2],
    )

    return t1, t2, t3


# Default singleton tasks for module-level access and backwards compatibility
research_task, analysis_task, writing_task = create_research_tasks()


# ------------------------------------------------------------------------------
# 2. CREW ASSEMBLY
# ------------------------------------------------------------------------------
# WHAT DOES Process.sequential MEAN VS OTHER OPTIONS?
#
# 1. Process.sequential (Used Here):
#    - How it works: Tasks execute one after another in the exact order listed in `tasks=[...]`.
#    - Data flow: Output from Task N flows into Task N+1 via the `context=` parameter.
#    - When to use: Ideal for deterministic, step-by-step pipelines (e.g., ETL, Research -> Analyze -> Write),
#      where each stage depends strictly on the output of the preceding stage.
#    - Benefits: Predictable, cost-effective, low token overhead, zero manager-LLM latency.
#
# 2. Process.hierarchical:
#    - How it works: A manager LLM (specified via `manager_llm=...`) oversees the crew.
#      The manager evaluates tasks dynamically, decides which agent should work on what sub-task,
#      reviews intermediate answers, and requests revisions if criteria are not met.
#    - When to use: Useful for complex, open-ended problem solving where task ordering cannot be
#      predetermined, or where tasks require dynamic delegation and iterative review.
#    - Trade-offs: Higher token consumption, slower execution, and requires a capable manager model.

def create_research_crew() -> Crew:
    """
    Factory function to assemble and return a fresh Research Crew instance.
    Generates new tasks per run to avoid cross-request state contamination.
    """
    tasks = list(create_research_tasks())
    return Crew(
        agents=[researcher, analyst, writer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )


def run_research(topic: str) -> str:
    """
    Convenience function to kickoff the crew for a given topic and return the report text.
    """
    crew = create_research_crew()
    result = crew.kickoff(inputs={"topic": topic})
    return str(result)


# ------------------------------------------------------------------------------
# 3. STANDALONE EXECUTION RUNNER (Milestone 3 Verification)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    test_topic = "Growth of VLSI Industry"
    print("\n" + "=" * 80)
    print("STARTING FULL CREW RUN (Milestone 3 End-to-End)")
    print(f"Topic: {test_topic}")
    print("Process: Process.sequential (Researcher -> Analyst -> Writer)")
    print("=" * 80 + "\n")

    # Guard check: Ensure API key is present
    if not api_key:
        print("ERROR: No API key found. Please set MY_API_KEY in your env/.env file.")
        exit(1)

    # Initialize crew and kickoff
    crew = create_research_crew()
    result = crew.kickoff(inputs={"topic": test_topic})

    print("\n" + "=" * 80)
    print("FINAL REPORT OUTPUT FROM FULL CREW:")
    print("=" * 80 + "\n")
    print(result)
