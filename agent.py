
## 2. Agent Code (`agent.py`)


#!/usr/bin/env python3
"""
Agent CLI - Connects to an LLM and answers questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON line to stdout: {"answer": "...", "tool_calls": []}
"""

import argparse
import json
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables from .env.agent.secret
load_dotenv(".env.agent.secret")

# Configuration from environment
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-coder-plus")

# Timeout in seconds
TIMEOUT = 60


def log_debug(message: str) -> None:
    """Log debug messages to stderr."""
    print(f"[DEBUG] {message}", file=sys.stderr, flush=True)


def call_llm(question: str) -> dict:
    """
    Call the LLM API and get a response.
    
    Args:
        question: The user's question
        
    Returns:
        dict with 'answer' and 'tool_calls' keys
        
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
    
    # System prompt - minimal for now, will expand in later tasks
    system_prompt = (
        "You are a helpful AI assistant. Answer questions directly and concisely. "
        "Do not use any tools yet - just provide the answer based on your knowledge."
    )
    
    # Build the request payload (OpenAI-compatible format)
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    
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
    
    # Extract the answer from the response
    try:
        answer = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected API response format: {e}")
    
    # For Task 1, tool_calls is always empty
    # Will be populated in Task 2 when we add tool support
    tool_calls = []
    
    return {
        "answer": answer.strip(),
        "tool_calls": tool_calls
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent CLI - Ask questions to an LLM"
    )
    parser.add_argument(
        "question",
        type=str,
        help="The question to ask the LLM"
    )
    
    args = parser.parse_args()
    
    log_debug(f"Received question: {args.question}")
    
    try:
        result = call_llm(args.question)
        
        # Output valid JSON to stdout (single line)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        
        return 0
        
    except Exception as e:
        log_debug(f"Error: {e}")
        # Output error as JSON to maintain format consistency
        error_result = {
            "answer": f"Error: {str(e)}",
            "tool_calls": []
        }
        print(json.dumps(error_result, ensure_ascii=False), file=sys.stdout, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())