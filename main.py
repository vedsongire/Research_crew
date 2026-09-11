"""
FastAPI REST API Service for the AI Research Assistant Crew.

This module exposes the multi-agent research pipeline via standard HTTP REST endpoints:
- POST /research: Accepts a research topic, triggers the CrewAI workflow, persists
  the generated report as a timestamped Markdown file in `outputs/`, and returns
  the report and metadata as JSON.
- GET /health: Simple healthcheck endpoint for server status and uptime monitoring.

WHY REST / FASTAPI?
1. Separation of Concerns: Decouples the client (UI, CLI, external services) from the
   heavy multi-agent orchestration backend.
2. Pydantic Validation: Automatically parses and validates request payloads, returning
   standard 4xx client errors on malformed or missing fields before any LLM tokens are spent.
3. Asynchronous Non-blocking Architecture: Standard in modern Python web development,
   FastAPI easily handles I/O while running compute/LLM workloads.
4. Auto-Generated OpenAPI Docs: Provides interactive Swagger UI at `/docs` out of the box.
"""

import os
import re
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from crew import run_research


# ------------------------------------------------------------------------------
# 1. FASTAPI APPLICATION INITIALIZATION
# ------------------------------------------------------------------------------
app = FastAPI(
    title="AI Research Assistant Crew API",
    description=(
        "REST API wrapper for the CrewAI Multi-Agent Research Assistant. "
        "Coordinates Researcher, Analyst, and Writer agents to produce comprehensive reports."
    ),
    version="1.0.0",
)

# Base directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


# ------------------------------------------------------------------------------
# 2. REQUEST & RESPONSE SCHEMAS (Pydantic Models)
# ------------------------------------------------------------------------------
# WHY PYDANTIC MODELS?
# Pydantic enforces strict contract schemas at the HTTP boundary:
# - If a client sends bad JSON or omits 'topic', FastAPI immediately rejects the request
#   with an HTTP 422 Unprocessable Entity, preventing internal attribute errors.
# - Documentation: Types and field descriptions automatically populate `/docs`.

class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        description="The subject or research question to investigate.",
        examples=["Quantum Computing Applications in Healthcare"],
    )


class ResearchResponse(BaseModel):
    status: str = Field(..., description="Execution status ('success' or 'error').")
    topic: str = Field(..., description="The validated research topic investigated.")
    filename: str = Field(..., description="Name of the timestamped markdown report saved.")
    saved_path: str = Field(..., description="Relative workspace path where the report is stored.")
    report: str = Field(..., description="The complete final Markdown report produced by the Writer agent.")


# ------------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def save_report_to_disk(topic: str, content: str) -> tuple[str, str]:
    """
    Saves the generated report to outputs/ with a timestamped and sanitized filename.

    WHY TIMESTAMPED FILENAMES?
    - Prevents accidental overwriting when researching identical or similar topics.
    - Creates an immutable historical log of all research runs for auditing.
    - Cleans non-alphanumeric characters to ensure filesystem compatibility across Windows/Linux.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize topic: replace special characters with underscores and limit length
    safe_topic = re.sub(r"[^a-zA-Z0-9_\-]", "_", topic.strip())[:40].strip("_")
    filename = f"report_{timestamp}_{safe_topic}.md" if safe_topic else f"report_{timestamp}.md"
    filepath = os.path.join(OUTPUTS_DIR, filename)

    # Save as UTF-8 to correctly preserve markdown symbols, emojis, and formatting
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    rel_path = os.path.relpath(filepath, BASE_DIR)
    return filename, rel_path


# ------------------------------------------------------------------------------
# 4. REST ENDPOINTS
# ------------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """
    Healthcheck endpoint to verify that the service is alive.
    """
    return {"status": "ok", "service": "AI Research Assistant Crew API"}


@app.post(
    "/research",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    tags=["Research"],
    summary="Trigger Multi-Agent Research Pipeline",
)
def create_research_report(payload: ResearchRequest) -> ResearchResponse:
    """
    Initiate the full research crew workflow for a given topic:
    1. Validates the input topic (returns HTTP 400 if empty or whitespace).
    2. Kicks off the sequential crew (Researcher -> Analyst -> Writer).
    3. Saves the final report to disk in the `outputs/` folder.
    4. Returns the report content and file location as JSON.
    """
    # --------------------------------------------------------------------------
    # INPUT VALIDATION (Error Handling for empty/whitespace topics)
    # --------------------------------------------------------------------------
    clean_topic = payload.topic.strip()
    if not clean_topic:
        # WHY 400 BAD REQUEST?
        # A 400 error cleanly tells the client that their request was understood by the
        # server, but the provided payload is semantically invalid for processing.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid input: 'topic' cannot be empty or contain only whitespace. "
                "Please provide a meaningful research topic."
            ),
        )

    # --------------------------------------------------------------------------
    # PIPELINE EXECUTION
    # --------------------------------------------------------------------------
    try:
        report_content = run_research(clean_topic)
    except Exception as e:
        # Catch unexpected pipeline failures (e.g. LLM API quota errors, networking issues)
        # and surface a clear 500 error instead of silently crashing the process.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research crew pipeline failed during execution: {str(e)}",
        )

    # --------------------------------------------------------------------------
    # PERSISTENCE & RESPONSE
    # --------------------------------------------------------------------------
    filename, saved_path = save_report_to_disk(clean_topic, report_content)

    return ResearchResponse(
        status="success",
        topic=clean_topic,
        filename=filename,
        saved_path=saved_path,
        report=report_content,
    )


# ------------------------------------------------------------------------------
# 5. SERVER ENTRYPOINT (For direct python execution if invoked as script)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # Run uvicorn on port 8000 by default
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
