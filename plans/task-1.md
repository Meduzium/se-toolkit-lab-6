# Implementation Plan - Task 1: Call an LLM from Code

This plan outlines the approach for creating a foundational CLI agent that interfaces with an LLM via an OpenAI-compatible API.

## 1. Technical Stack & Environment
- **Runtime**: Python 3.12+ managed via `uv`.
- **LLM Provider**: Qwen Code API (Remote VM deployment).
- **Model**: `qwen3-coder-plus` (Recommended for strong tool-calling foundation).
- **Configuration**: Environment variables stored in `.env.agent.secret`.

## 2. Key Implementation Steps

### Phase 1: Environment Setup
1. Create the secret environment file: `cp .env.agent.example .env.agent.secret`.
2. Configure `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_MODEL` within the secret file.
3. Initialize the Python environment and add necessary dependencies (`openai`, `python-dotenv`).

### Phase 2: CLI Development (`agent.py`)
1. **Argument Parsing**: Use `sys.argv` to capture the user's question from the first command-line argument.
2. **Environment Loading**: Utilize `python-dotenv` to securely load API credentials.
3. **LLM Client**: Initialize an OpenAI-compatible client pointing to the Qwen API base.
4. **API Call**: Implement a chat completion request with a 60-second timeout.
5. **Output Handling**:
    - Format the response as a JSON object containing `answer` (string) and `tool_calls` (empty list).
    - Ensure the JSON is printed to `stdout`.
    - Redirect all logging, debug, or progress information to `stderr`.

### Phase 3: Validation
1. Verify the output format using `uv run agent.py "Test question"`.
2. Confirm the exit code is `0` on successful execution.

## 3. Technical Considerations
- **Error Handling**: The agent should gracefully handle API timeouts or connection errors, ensuring error messages are sent to `stderr` to avoid corrupting the JSON output on `stdout`.
- **JSON Integrity**: Strict adherence to the output schema is required for compatibility with the future autochecker/evaluator.