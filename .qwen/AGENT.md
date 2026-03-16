# Agent Documentation

## Overview

This is a CLI-based AI agent that connects to an LLM and answers questions about the project. It supports three tool types: file discovery (`list_files`), file reading (`read_file`), and live API queries (`query_api`). The agent serves as a system documentation assistant that can consult both static documentation and the deployed backend.

## Architecture

### Components

1. **CLI Interface** (`agent.py`)
   - Parses command-line arguments
   - Handles input/output formatting (JSON to stdout)
   - Manages the agentic loop with iteration limits

2. **LLM Client**
   - Connects to OpenAI-compatible API
   - Supports function/tool calling schema
   - Handles conversation state and tool response injection

3. **Tool Registry**
   - `list_files`: Discover files in a directory
   - `read_file`: Read wiki, docs, or source code files
   - `query_api`: Query the live backend API for data or system behavior

4. **Environment Configuration**
   - `.env.agent.secret`: LLM credentials (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`)
   - `.env.docker.secret`: Backend API key (`LMS_API_KEY`)
   - All config loaded via `python-dotenv`; no hardcoded values

## LLM Provider

**Provider:** Qwen Code API  
**Model:** `qwen3-coder-plus`

### Why Qwen Code?
- 1000 free requests per day
- Works from Russia without restrictions
- No credit card required
- Strong tool calling support
- OpenAI-compatible API

### Alternative Providers
If Qwen Code is unavailable, you can use OpenRouter:
- `meta-llama/llama-3.3-70b-instruct:free`
- `qwen/qwen3-coder:free`

Note: OpenRouter free tier has 50 requests/day limit.

## Tools

### `list_files`
- **Purpose**: Discover available documentation or source files.
- **Input**: `path` (string) - Relative directory path from project root.
- **Output**: Newline-separated list of files/folders.
- **Use when**: You need to explore directory structure before reading files.

### `read_file`
- **Purpose**: Read content of a specific file (wiki, docs, or source code).
- **Input**: `path` (string) - Relative file path from project root.
- **Output**: File content as string.
- **Use when**: Answering questions about documentation, framework, architecture, or debugging source code.

### `query_api` ⭐ *New in Task 3*
- **Purpose**: Query the deployed backend API for live data or system behavior.
- **Input**: 
  - `method` (string): HTTP method (`GET`, `POST`, `PUT`, `DELETE`)
  - `path` (string): API endpoint (e.g., `/items/`, `/analytics/completion-rate?lab=lab-99`)
  - `body` (string, optional): JSON request body for POST/PUT
- **Output**: JSON string with `status_code` and `body` keys.
- **Authentication**: Uses `LMS_API_KEY` from environment via `Authorization: Bearer <key>` header.
- **Base URL**: Reads `AGENT_API_BASE_URL` from env (defaults to `http://localhost:42002`).
- **Use when**: 
  - Counting items, checking scores, querying analytics
  - Testing API behavior (status codes, error responses)
  - Diagnosing runtime bugs by reproducing errors

> ⚠️ **Key Distinction**: Two separate API keys!
> - `LLM_API_KEY` (`.env.agent.secret`): Authenticates with your LLM provider
> - `LMS_API_KEY` (`.env.docker.secret`): Authenticates with the backend API
> Never mix them up — the autochecker uses different values for each.

## Tool Selection Strategy

The system prompt guides the LLM to choose tools based on question type:

| Question Type | Example | Recommended Tool(s) |
|--------------|---------|-------------------|
| Wiki/documentation lookup | "What steps protect a GitHub branch?" | `read_file` |
| Source code analysis | "What framework does the backend use?" | `read_file` + `list_files` |
| Live data query | "How many items are in the database?" | `query_api` |
| API behavior test | "What status code for unauthenticated request?" | `query_api` |
| Bug diagnosis | "Why does /analytics crash for lab-99?" | `query_api` → `read_file` |
| Architecture explanation | "Trace an HTTP request journey" | `read_file` (multiple files) |

**Decision flow**:
1. Does the question ask about *live data* or *runtime behavior*? → Use `query_api`
2. Does it ask about *documentation*, *code*, or *static facts*? → Use `read_file`/`list_files`
3. Does it require *chaining* (e.g., reproduce error then read source)? → Use both in sequence

## Agentic Loop

The agent operates in an iterative loop:
1. **Receive Query**: User asks a question via CLI.
2. **LLM Decision**: The LLM decides whether to call a tool or answer directly.
3. **Tool Execution**: Python executes requested tools securely (path validation, auth headers).
4. **Observation**: Tool results are fed back to the LLM as `role: tool` messages.
5. **Termination**: When the LLM has sufficient information, it returns a JSON answer.

Maximum iterations: 10 (configurable via `MAX_ITERATIONS`).

## Security

- **Path Traversal Protection**: All file paths resolved via `pathlib`; paths with `..` rejected.
- **Root Confinement**: Tools verify resolved paths stay within `PROJECT_ROOT`.
- **Key Isolation**: LLM and backend API keys stored in separate env files; never logged or exposed in responses.
- **Error Handling**: Tool errors returned as structured JSON to LLM (not raw exceptions) to avoid leaking internals.

## Output Format

```json
{
  "answer": "String answer to the user's question",
  "source": "wiki/file.md#anchor or 'system' or 'api'",
  "tool_calls": [
    {"tool": "name", "args": {...}, "result": "..."}
  ]
}