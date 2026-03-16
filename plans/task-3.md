# Task 3: System Agent with `query_api` Tool

## Implementation Plan

### Overview
Task 3 extends the documentation agent from Task 2 by adding a `query_api` tool that allows the agent to query the live backend API. This enables answering two new question types:
1. **Static system facts**: Framework, ports, status codes
2. **Data-dependent queries**: Item counts, scores, analytics

### 1. Tool Schema Definition

#### `query_api` Function Signature
```python
def query_api(method: str, path: str, body: Optional[str] = None) -> str
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Query the deployed backend API. Use for data-dependent questions (item counts, scores, analytics) or to check system behavior (status codes, error responses). Do NOT use for wiki/documentation questions.",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "enum": ["GET", "POST", "PUT", "DELETE"],
          "description": "HTTP method to use"
        },
        "path": {
          "type": "string",
          "description": "API endpoint path, e.g., '/items/', '/analytics/completion-rate?lab=lab-99'"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body as a string (for POST/PUT)"
        }
      },
      "required": ["method", "path"]
    }
  }
}

You are a System Documentation Agent. Your goal is to answer user questions using:
1. Project wiki/documentation files (in wiki/ directory)
2. Source code files (in backend/, frontend/, etc.)
3. The live backend API (for data queries and system behavior)

Available tools:
- `list_files`: Discover files in a directory
- `read_file`: Read content of wiki, docs, or source code files
- `query_api`: Query the live backend API for data or system status

Tool selection guide:
- Use `read_file`/`list_files` for: wiki questions, documentation lookups, reading source code to understand framework/architecture/bugs
- Use `query_api` for: counting items, checking status codes, querying analytics, testing API behavior, diagnosing runtime errors

Response format:
When you have the answer, respond with a JSON object ONLY. Do not add markdown formatting.
Format: {"answer": "your answer", "source": "path/to/file.md#section-anchor"}

Rules:
1. The source field should include file path and section anchor for wiki/code answers
2. For system/API questions where there's no file source, use "source": "system" or "source": "api"
3. If you cannot find the answer after reasonable searching, state that clearly
4. Always be precise - quote exact values from code or API responses when possible