#!/usr/bin/env python3

"""
Agent CLI - Connects to an LLM with tool support for documentation queries.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON line to stdout: {"answer": "...", "source": "...", "tool_calls": []}
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env.agent.secret
load_dotenv(".env.agent.secret")

# Configuration from environment - LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")

# Configuration from environment - Backend API
LMS_API_KEY = os.getenv("LMS_API_KEY")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

# Timeout in seconds
TIMEOUT = 60
MAX_ITERATIONS = 10
PROJECT_ROOT = Path.cwd().resolve()


def log_debug(message: str) -> None:
    """Log debug messages to stderr."""
    print(f"[DEBUG] {message}", file=sys.stderr, flush=True)


# --- Tools ---

def safe_path(path_str: str) -> Path:
    """Resolve and validate a path to ensure it stays within the project root."""
    if ".." in path_str:
        raise ValueError("Path traversal not allowed")
    
    target = (PROJECT_ROOT / path_str).resolve()
    
    try:
        # Check if target is within project root
        target.relative_to(PROJECT_ROOT)
    except ValueError:
        raise ValueError(f"Access denied: {path_str} is outside project directory")
    
    return target


def list_files(path: str) -> str:
    """List files and directories at a given path."""
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: {path} does not exist"
        if not safe.is_dir():
            return f"Error: {path} is not a directory"
        
        entries = [str(p.name) for p in safe.iterdir()]
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {str(e)}"


def read_file(path: str) -> str:
    """Read a file from the project repository."""
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: {path} does not exist"
        if not safe.is_file():
            return f"Error: {path} is not a file"
        
        return safe.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error: {str(e)}"


def query_api(method: str, path: str, body: Optional[str] = None) -> str:
    """
    Query the deployed backend API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API endpoint path (e.g., '/items/', '/analytics/completion-rate')
        body: Optional JSON request body as a string
        
    Returns:
        JSON string with 'status_code' and 'body' keys
    """
    import httpx
    
    if not LMS_API_KEY:
        return json.dumps({"status_code": 500, "body": "Error: LMS_API_KEY not configured"})
    
    headers = {
        "Authorization": f"Bearer {LMS_API_KEY}",
        "Content-Type": "application/json",
    }
    
    url = f"{AGENT_API_BASE_URL.rstrip('/')}{path}"
    
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = client.post(url, headers=headers, content=body or "{}")
            elif method.upper() == "PUT":
                response = client.put(url, headers=headers, content=body or "{}")
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return json.dumps({"status_code": 400, "body": f"Error: Unsupported method {method}"})
        
        # Return structured response
        return json.dumps({
            "status_code": response.status_code,
            "body": response.text
        })
        
    except httpx.RequestError as e:
        return json.dumps({"status_code": 0, "body": f"Connection error: {str(e)}"})
    except Exception as e:
        return json.dumps({"status_code": 500, "body": f"Error: {str(e)}"})


# --- Tool Definitions for LLM ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a specific path. Use this to discover wiki files or source code structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki' or 'backend/app')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a specific file. Use this to find answers in documentation, wiki, or source code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md' or 'backend/app/main.py')"
                    }
                },
                "required": ["path"]
            }
        }
    },
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
]

TOOL_MAP = {
    "list_files": list_files,
    "read_file": read_file,
    "query_api": query_api
}

# --- System Prompt ---

SYSTEM_PROMPT = """
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
1. The source field should include file path and section anchor for wiki/code answers (e.g., wiki/git-workflow.md#resolving-merge-conflicts)
2. For system/API questions where there's no file source, use "source": "system" or "source": "api"
3. If you cannot find the answer after reasonable searching, state that clearly in the JSON answer
4. Always be precise - quote exact values from code or API responses when possible
"""


def call_llm(messages: list, tool_calls_response: bool = False) -> dict:
    """
    Call the LLM API and get a response.
    
    Args:
        messages: List of message dicts for the conversation
        tool_calls_response: Whether to expect tool calls in response
        
    Returns:
        dict with 'content' and 'tool_calls' keys
        
    Raises:
        Exception: If API call fails
    """
    import httpx
    
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY not set in .env.agent.secret")
    if not LLM_API_BASE:
        raise ValueError("LLM_API_BASE not set in .env.agent.secret")
    
    # Build the API endpoint URL
    api_url = f"{LLM_API_BASE.rstrip('/')}/v1/chat/completions"
    
    log_debug(f"Calling LLM at {api_url}")
    log_debug(f"Model: {LLM_MODEL}")
    
    # Build the request payload (OpenAI-compatible format)
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    
    # Add tools if we want tool calls
    if tool_calls_response:
        payload["tools"] = TOOLS
        payload["tool_choice"] = "auto"
    
    # Headers for API authentication
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    start_time = time.time()
    
    # Make the API request
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(api_url, json=payload, headers=headers)
    
    elapsed = time.time() - start_time
    log_debug(f"API response time: {elapsed:.2f}s")
    
    # Check for errors
    response.raise_for_status()
    
    # Parse the response
    response_data = response.json()
    log_debug(f"Response: {json.dumps(response_data, indent=2)[:500]}...")
    
    # Extract the response from the API
    try:
        choice = response_data["choices"][0]
        message = choice["message"]
        # Handle None content safely (LLM may return null when making tool calls)
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected API response format: {e}")
    
    return {
        "content": content,
        "tool_calls": tool_calls
    }


def run_agentic_loop(question: str) -> dict:
    """
    Run the agentic loop for a given question.
    
    Args:
        question: The user's question
        
    Returns:
        dict with 'answer', 'source', and 'tool_calls' keys
    """
    # Initialize message history
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    iterations = 0
    
    while iterations < MAX_ITERATIONS:
        iterations += 1
        log_debug(f"Iteration {iterations}/{MAX_ITERATIONS}")
        
        # Call LLM with tool support
        response = call_llm(messages, tool_calls_response=True)
        
        # Check for tool calls
        if response["tool_calls"]:
            log_debug(f"LLM requested {len(response['tool_calls'])} tool call(s)")
            
            for tool_call in response["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = json.loads(tool_call["function"]["arguments"])
                tool_call_id = tool_call.get("id", f"call_{len(tool_calls_log)}")
                
                log_debug(f"Executing tool: {func_name} with args: {func_args}")
                
                # Execute tool
                try:
                    if func_name in TOOL_MAP:
                        result = TOOL_MAP[func_name](**func_args)
                    else:
                        result = f"Error: Unknown tool {func_name}"
                except Exception as e:
                    result = f"Error: {str(e)}"
                
                # Log tool call
                tool_calls_log.append({
                    "tool": func_name,
                    "args": func_args,
                    "result": result
                })
                
                # Append tool response to message history
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": func_name,
                    "content": result
                })
            
            # Continue loop to get LLM reaction to tool output
            continue
        
        else:
            # No tool calls, assume final answer
            log_debug("LLM returned final answer")
            content = response["content"]
            
            # Attempt to parse JSON from content
            try:
                # Clean up markdown if present
                clean_content = content.replace("```json", "").replace("```", "").strip()
                final_data = json.loads(clean_content)
                return {
                    "answer": final_data.get("answer", content),
                    "source": final_data.get("source", "unknown"),
                    "tool_calls": tool_calls_log
                }
            except json.JSONDecodeError:
                # Fallback if LLM didn't return strict JSON
                log_debug("LLM did not return valid JSON, using content as answer")
                return {
                    "answer": content,
                    "source": "unknown",
                    "tool_calls": tool_calls_log
                }
    
    # Max iterations reached
    log_debug("Maximum iterations reached")
    return {
        "answer": "Stopped due to maximum tool call limit.",
        "source": "unknown",
        "tool_calls": tool_calls_log
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent CLI - Ask questions to an LLM with tool support"
    )
    parser.add_argument(
        "question",
        type=str,
        help="The question to ask the LLM"
    )
    
    args = parser.parse_args()
    
    log_debug(f"Received question: {args.question}")
    
    try:
        result = run_agentic_loop(args.question)
        
        # Output valid JSON to stdout (single line)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        
        return 0
        
    except Exception as e:
        log_debug(f"Error: {e}")
        # Output error as JSON to maintain format consistency
        error_result = {
            "answer": f"Error: {str(e)}",
            "source": "unknown",
            "tool_calls": []
        }
        print(json.dumps(error_result, ensure_ascii=False), file=sys.stdout, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())