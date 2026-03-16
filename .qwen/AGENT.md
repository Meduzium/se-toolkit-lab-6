# Agent Documentation

## Overview

This is a CLI-based AI agent that connects to an LLM and answers questions. It serves as the foundation for the agentic system that will be built in subsequent tasks.

## Architecture


### Components

1. **CLI Interface** (`agent.py`)
   - Parses command-line arguments
   - Handles input/output formatting

2. **LLM Client**
   - Connects to OpenAI-compatible API
   - Sends questions and receives responses

3. **Environment Configuration**
   - `.env.agent.secret` stores API credentials
   - Loaded via `python-dotenv`

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

## Configuration

### Environment File

Create `.env.agent.secret` in the project root:

```bash
cp .env.agent.example .env.agent.secret


# Documentation Agent

This agent answers questions about the project by navigating the local wiki using tools.

## Agentic Loop
The agent operates in a loop:
1. **Receive Query**: User asks a question via CLI.
2. **LLM Decision**: The LLM decides whether to call a tool or answer.
3. **Tool Execution**: If tools are requested (`list_files`, `read_file`), Python executes them securely.
4. **Observation**: Tool results are fed back to the LLM.
5. **Termination**: When the LLM has enough info, it returns a JSON answer.

## Tools

### `list_files`
- **Purpose**: Discover available documentation files.
- **Input**: `path` (string) - Relative directory path.
- **Output**: Newline-separated list of files/folders.

### `read_file`
- **Purpose**: Read content of a specific documentation file.
- **Input**: `path` (string) - Relative file path.
- **Output**: File content string.

## Security
- **Path Traversal**: All paths are resolved using `pathlib`.
- **Root Check**: Tools verify that the resolved absolute path starts with the project root directory.
- **Restriction**: Paths containing `..` are rejected immediately.

## System Prompt Strategy
The system prompt instructs the LLM to:
1. Act as a documentation assistant.
2. Use tools to verify facts (no hallucination).
3. Return the final answer in a specific JSON schema (`answer`, `source`).
4. Include section anchors in the source field (e.g., `#setup`).

## Output Format
```json
{
  "answer": "String",
  "source": "wiki/file.md#anchor",
  "tool_calls": [
    {"tool": "name", "args": {}, "result": "..."}
  ]
}