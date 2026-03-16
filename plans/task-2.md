# Task 2: Documentation Agent Plan

## Overview
Transform the Task 1 CLI into an agentic system capable of navigating the project wiki using tools (`read_file`, `list_files`) to answer user questions with cited sources.

## Tool Schema Design
- **Format**: OpenAI Function Calling JSON Schema.
- **`list_files`**:
  - Args: `path` (string)
  - Description: List contents of a directory.
- **`read_file`**:
  - Args: `path` (string)
  - Description: Read contents of a specific file.
- **Security**: Both tools will resolve paths against the project root (`Path.cwd()`) to prevent directory traversal attacks (e.g., `../../etc/passwd`).

## Agentic Loop Logic
1. **Initialization**: Load system prompt, initialize message history with user query.
2. **Loop** (Max 10 iterations):
   - Call LLM with message history + tool definitions.
   - **Case A (Tool Calls)**:
     - Parse tool calls from response.
     - Execute Python functions for each tool.
     - Capture `result` (output or error).
     - Append `tool` role messages to history.
     - Log call details (`tool`, `args`, `result`) to `tool_calls` list.
     - Continue loop.
   - **Case B (Final Answer)**:
     - Parse LLM text content.
     - Extract `answer` and `source`.
     - Break loop.
3. **Output**: Construct final JSON object containing `answer`, `source`, and accumulated `tool_calls`.

## System Prompt Strategy
- Role: Documentation Assistant.
- Instructions:
  - Always use tools to verify information.
  - Do not hallucinate file paths.
  - Final output must be valid JSON with `answer` and `source` (file#anchor).
  - Stop after finding the answer.

## Security Measures
- Use `pathlib.Path.resolve()` to get absolute paths.
- Verify resolved path starts with the project root directory.
- Reject any path containing `..` before resolution.

## Testing Strategy
- **Unit Tests**: Verify path security (reject outside paths).
- **Integration Tests**: Mock the LLM client to simulate tool calls and verify the loop accumulates `tool_calls` correctly in the output.