import os
import sys
import json
from requests import *
from openai import OpenAI
from dotenv import load_dotenv

def validate_path(path):
    """Ensures the path is within the project directory to prevent directory traversal."""
    base_dir = os.path.abspath(os.getcwd())
    requested_path = os.path.abspath(os.path.join(base_dir, path))
    if not requested_path.startswith(base_dir):
        raise PermissionError("Access denied: Path is outside the project directory.")
    return requested_path

def list_files(path):
    """Lists files and directories at a given path."""
    try:
        safe_path = validate_path(path)
        if not os.path.isdir(safe_path):
            return f"Error: {path} is not a directory."
        entries = os.listdir(safe_path)
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {str(e)}"

def read_file(path):
    """Reads the content of a file."""
    try:
        safe_path = validate_path(path)
        if not os.path.isfile(safe_path):
            return f"Error: {path} is not a file."
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

def query_api(method, path, body=None):
    """Calls the deployed backend API with authentication."""
    base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002").rstrip('/')
    api_key = os.getenv("LMS_API_KEY")
    
    url = f"{base_url}/{path.lstrip('/')}"
    headers = {"X-API-Key": api_key} if api_key else {}
    
    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json.loads(body) if body else None,
            timeout=10
        )
        return json.dumps({
            "status_code": resp.status_code,
            "body": resp.text
        })
    except Exception as e:
        return f"Error: API request failed: {str(e)}"

def main():
    # Load environment variables (order matters for local vs autochecker)
    load_dotenv(".env.agent.secret")
    load_dotenv(".env.docker.secret")

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL", "openrouter/free")

    if not api_key:
        print("Error: LLM_API_KEY missing", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: uv run agent.py <question>", file=sys.stderr)
        sys.exit(1)

    user_question = sys.argv[1]
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files in a directory to explore the project structure.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read source code or markdown files to understand logic or documentation.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Query the live backend API for real-time data or system behavior.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                        "path": {"type": "string", "description": "API endpoint path (e.g. /items/)"},
                        "body": {"type": "string", "description": "Optional JSON string body"}
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system", 
            "content": (
                "You are a System Agent. Follow these steps:\n"
                "1. For wiki/docs, use list_files('wiki') then read_file.\n"
                "2. For live data or API behavior, use query_api.\n"
                "3. For code logic or bugs, use list_files/read_file on backend/ source code.\n"
                "4. If a query fails, read the error message and the relevant source code to diagnose bugs.\n"
                "5. Provide a 'source' if the info came from a file (e.g. 'wiki/path.md#section')."
            )
        },
        {"role": "user", "content": user_question}
    ]

    captured_tool_calls = []
    for _ in range(10):
        response = client.chat.completions.create(model=model, messages=messages, tools=tools)
        resp_msg = response.choices[0].message
        messages.append(resp_msg)

        if not resp_msg.tool_calls:
            # Final answer reached
            source = None
            for call in captured_tool_calls:
                if call["tool"] == "read_file":
                    source = call["args"].get("path")
            
            print(json.dumps({
                "answer": (resp_msg.content or "").strip(),
                "source": source,
                "tool_calls": captured_tool_calls
            }))
            return

        for tool_call in resp_msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if name == "list_files": result = list_files(args.get("path"))
            elif name == "read_file": result = read_file(args.get("path"))
            elif name == "query_api": result = query_api(args.get("method"), args.get("path"), args.get("body"))
            else: result = "Error: Tool not found"

            captured_tool_calls.append({"tool": name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": result})

if __name__ == "__main__":
    main()