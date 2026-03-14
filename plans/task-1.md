# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider Selection

**Provider:** Qwen Code API (OpenAI-compatible)
**Model:** `qwen3-coder-plus`

**Rationale:**
- 1000 free requests per day (sufficient for development and testing)
- Works from Russia without restrictions
- No credit card required
- Strong tool calling support (needed for future tasks)
- OpenAI-compatible API (easy integration)


## Implementation Steps

1. **Environment Setup**
   - Copy `.env.agent.example` to `.env.agent.secret`
   - Fill in `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Use `python-dotenv` to load variables

2. **Agent Core (`agent.py`)**
   - Parse command-line argument (question)
   - Load environment variables from `.env.agent.secret`
   - Build OpenAI-compatible API request
   - Send HTTP POST to `/v1/chat/completions`
   - Parse response and extract answer
   - Output JSON to stdout, debug to stderr

3. **System Prompt**
   - Minimal prompt instructing direct answers
   - Will be expanded in Task 2-3 with tools

4. **Error Handling**
   - Timeout: 60 seconds max
   - API errors: log to stderr, exit non-zero
   - Invalid JSON: exit non-zero

5. **Testing**
   - 1 regression test using subprocess
   - Verify JSON structure (`answer`, `tool_calls`)
   - Test with sample question

## Dependencies

- `python-dotenv` - Load environment variables
- `requests` or `httpx` - HTTP client for API calls
- Standard library: `json`, `sys`, `argparse`

## Output Format

```json
{"answer": "Representational State Transfer.", "tool_calls": []}

