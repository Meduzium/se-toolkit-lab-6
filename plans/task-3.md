# Implementation Plan - Task 3: The System Agent

This plan details the upgrade of the Documentation Agent to a **System Agent** capable of querying live backend data and diagnosing system-level issues using the `query_api` tool.

## 1. Technical Strategy

### Environment & Authentication
The agent will be updated to read from two distinct secret sources:
* **LLM Config**: `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` from `.env.agent.secret`.
* **System Config**: `LMS_API_KEY` and `AGENT_API_BASE_URL` (defaulting to `http://localhost:42002`) from `.env.docker.secret`.
* **Implementation**: Use `os.environ.get()` to ensure the autochecker can inject its own values during evaluation.

### Tool Definition: `query_api`
* **Functionality**: A wrapper around the `httpx` or `requests` library.
* **Schema**:
    * `method`: HTTP verb (GET, POST, etc.).
    * `path`: Endpoint relative to `AGENT_API_BASE_URL`.
    * `body`: Optional JSON string for POST/PUT requests.
* **Security**: Authentication will be handled by passing `LMS_API_KEY` in the request headers (e.g., `Authorization: Bearer <KEY>` or `X-API-Key`).

### System Prompt Evolution
The prompt will be updated to establish a hierarchy of truth:
1.  **Live State**: Use `query_api` for counts, status codes, and dynamic errors.
2.  **Logic/Structure**: Use `read_file` on source code to understand how endpoints work.
3.  **Policy/Manuals**: Use `read_file` on `wiki/` for human-written procedures.

---

## 2. Key Implementation Steps

### Phase 1: Tool Integration
1.  Define the `query_api` Python function.
2.  Update the `tools` list in `agent.py` to include the `query_api` schema.
3.  Refactor the environment loading logic to support multiple sources.

### Phase 2: The Agentic Loop Refinement
1.  Ensure the loop correctly handles `null` content from the LLM when tool calls are present.
2.  Maintain the 10-iteration cap and 60-second timeout.
3.  Make the `source` field in the final JSON output optional.

### Phase 3: Benchmarking & Iteration
1.  Run `uv run run_eval.py` to get a baseline score.
2.  Analyze failures (e.g., the LLM trying to read a file instead of querying the API).
3.  Tweak tool descriptions in the schema to provide clearer hints to the LLM.

---

## 3. Benchmark Diagnosis (Initial Run)

* **Initial Score**: 0/10 (Pre-implementation).
* **First Failures**:
    * *Question 4 (Item Count)*: Expected to fail because the agent currently lacks the `query_api` tool.
    * *Question 6 (Bug Diagnosis)*: Expected to fail because the agent cannot yet correlate live 500 errors with source code lines.
* **Iteration Strategy**:
    1.  Implement `query_api` first to solve data-dependent questions.
    2.  Update the system prompt specifically for "chain-of-thought" reasoning: "If an API returns an error, read the corresponding module in `backend/routers/` to find the bug."

---

## 4. Technical Considerations
* **Path Traversal**: Ensure `list_files` and `read_file` maintain their security boundaries.
* **JSON Robustness**: The agent must ensure that the `query_api` result (which is already JSON) is properly stringified so it doesn't break the agent's own output format.