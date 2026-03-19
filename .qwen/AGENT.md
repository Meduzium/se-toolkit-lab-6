# Agent Documentation: The System Agent

## Purpose
The `agent.py` script has evolved into a comprehensive **System Agent**. Beyond simply reading documentation, it is now capable of interacting with the live running backend as a source of truth. By combining static file analysis (via the wiki and source code) with dynamic API querying, the agent can answer complex questions ranging from architectural design to real-time database counts and system debugging.

## Usage

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed.
- Access to an OpenAI-compatible LLM API.
- A running instance of the project backend API.

### Environment Configuration
The agent strictly follows a "no-hardcoding" policy. It requires the following environment variables, typically loaded from `.env.agent.secret` and `.env.docker.secret`:

| Variable | Description | Requirement |
| :--- | :--- | :--- |
| `LLM_API_KEY` | Key for the LLM provider (e.g., Qwen). | Required |
| `LLM_API_BASE` | Base URL for the LLM completions endpoint. | Required |
| `LLM_MODEL` | The model identifier (e.g., `qwen3-coder-plus`). | Required |
| `LMS_API_KEY` | Authentication key for the **Backend API**. | Required |
| `AGENT_API_BASE_URL` | Base URL of the backend (default: `http://localhost:42002`). | Optional |

### Execution
```Bash
    uv run agent.py "How many items are in the database?"
```

# Architecture & Tools

The agent utilizes an agentic loop (max 10 iterations) with access to three primary tools:

1. list_files: Navigates the directory structure to find wiki pages or source code files.

2. read_file: Reads the contents of a file. Essential for finding framework details in main.py or resolving documentation queries.

3. query_api: The new system tool. It performs HTTP requests (GET, POST, etc.) to the backend. It automatically attaches the LMS_API_KEY for authentication and returns both the status code and the response body to the LLM.

# System Prompt Strategy

The LLM is instructed to evaluate the "nature" of the truth required:

1. Static Facts: If the user asks about instructions or policies, the agent prioritizes wiki/ files.

2. System Logic: If the user asks about how the code works or specific frameworks, it uses list_files and read_file on the backend/ or src/ directories.

3. Live Data: If the user asks about counts, status codes, or current system state, it triggers query_api.

# Output Schema

The output is a single JSON line. The source field is now optional, as system-direct answers may not have a corresponding markdown file.
```JSON
{
  "answer": "There are 120 items in the database.",
  "source": "Optional path or null",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
    }
  ]
}
```

# Benchmark & Lessons Learned
## Evaluation Results

The agent successfully passed the run_eval.py benchmark with a 10/10 score.
Lessons Learned

1. Authentication Separation: A critical lesson was maintaining the distinction between the LLM provider key and the Backend API key. Mixing these up results in 401 Unauthorized errors during query_api calls.

2. Error Diagnosis: By combining query_api and read_file, the agent can perform "Full-Stack Debugging." For example, it can catch a 500 Internal Server Error via the API, see the traceback, and then immediately read the corresponding Python file to identify the specific line causing a ZeroDivisionError or TypeError.

3. Handling null Responses: Some LLMs return a null content field when initiating a tool call. The agent logic was updated to handle (msg.get("content") or "") to prevent AttributeError crashes.

4. Path Precision: The agent performs best when the system prompt encourages it to list_files first rather than guessing file paths, which reduces "File Not Found" errors in the loop.