# PROJECT INSTRUCTIONS — AI Research Assistant Crew
(For the coding agent. Read fully before writing any code.)

## 1. What we're building
A multi-agent AI system that takes a topic and produces a researched report:
- A Researcher agent searches the web (real search, via a LangChain tool).
- An Analyst agent extracts key points from the research.
- A Writer agent drafts a final polished report.
- The whole thing is wrapped in a FastAPI REST endpoint (`POST /research`).

This is a learning project for a human who wants to understand every
concept used (REST APIs, LLM tool-calling, LangChain, CrewAI) — not just
get working code. Favor clear, well-commented code over clever/terse code.

## 2. Tech stack — DO NOT substitute or upgrade without asking
- Python 3.11+
- crewai
- langchain, langchain-community (for the search tool)
- duckduckgo-search (free, no API key required)
- fastapi, uvicorn
- anthropic (Claude API, via crewai's LLM wrapper or langchain-anthropic)
- python-dotenv

Before using ANY function, class, or import from these libraries, verify it
exists in the version actually installed in this environment (check with
`pip show <package>` or the installed `__init__.py`/docs) — do not assume
an API from memory. These libraries (especially crewai) have changed their
APIs across versions; a method that existed in an older version may not
exist now, or may have moved.

## 3. Hard rules — anti-hallucination
1. **Never invent a library API.** If you are not certain a function/class/
   parameter exists in the installed version, check the installed package
   source or official docs first. If you cannot verify it, say so instead
   of guessing.
2. **Never claim something works without actually running it.** After
   writing or changing code, execute it. Show the real output. Do not
   describe expected output as if it were actual output.
3. **Never fabricate API keys, tokens, or test results.** If a step
   requires a real API key and none is available, stop and ask — do not
   simulate a fake response and present it as real.
4. **Do not add features, files, or dependencies that were not asked for.**
   Stick to the file structure in Section 4. If you think something extra
   is genuinely needed, ask before adding it.
5. **If an instruction is ambiguous, ask a clarifying question** rather
   than picking an interpretation silently.
6. **Every file must include short comments explaining WHY, not just
   what** — this is for a person actively learning the concepts, not just
   trying to ship code. Comment on: why a tool is defined this way, what
   an agent's role/goal/backstory does, why a task has certain inputs.
7. **Work in the step order in Section 5. Do not skip ahead** (e.g. do not
   build the Crew before the search tool is tested working in isolation).
8. **After completing each step, state clearly**: what was built, how it
   was tested, and the actual result of that test — so progress can be
   verified at each checkpoint, not just at the end.
9. **Never hardcode the API key in code.** Always load it from a `.env`
   file via `python-dotenv` / `os.environ`.

## 4. File structure — build exactly this, nothing more
```
research-crew/
├── .env.example
├── requirements.txt
├── README.md
├── main.py
├── crew.py
├── agents.py
├── tools/
│   ├── __init__.py
│   └── search_tool.py
├── outputs/
│   └── .gitkeep
└── tests/
    └── test_search_tool.py
```

## 5. Build order — follow these milestones in sequence
**Milestone 1 — Search tool (isolated, no agents yet)**
- Build `tools/search_tool.py`: a LangChain `@tool` wrapping a DuckDuckGo
  search call.
- Build `tests/test_search_tool.py`: call the tool directly with a sample
  query, print and verify real results come back.
- STOP and report the actual test output before continuing.

**Milestone 2 — Researcher agent (alone)**
- Build `agents.py` with only the Researcher agent (role, goal, backstory,
  llm, tools=[search_tool]).
- Test it on one sample topic as a standalone script. Confirm it actually
  invokes the search tool (not just hallucinating an answer) — check for
  real search results in its reasoning/output.
- STOP and report the actual output before continuing.

**Milestone 3 — Full crew**
- Add Analyst and Writer agents to `agents.py`.
- Build `crew.py`: one Task per agent, chained via `context=` so each task
  receives the previous task's output. Assemble `Crew(process=Process.sequential)`.
- Run `crew.kickoff(inputs={"topic": "..."})` end-to-end on a real topic.
- STOP and report the actual final report output.

**Milestone 4 — REST API wrapper**
- Build `main.py`: FastAPI app, `POST /research` accepts `{"topic": str}`,
  runs the crew, saves the report to `outputs/`, returns it as JSON.
- Test with a real HTTP request (curl or similar) and report the actual
  response received.

**Milestone 5 — Docs**
- Write `README.md`: setup steps, architecture summary, one real example
  request/response (from actual output, not invented).

## 6. Definition of done
Each milestone is only "done" when it has been run for real and produced
verifiable output — not when the code merely looks correct.
