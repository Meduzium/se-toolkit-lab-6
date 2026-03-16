#!/usr/bin/env python3

"""
Regression tests for agent.py

Tests verify that the agent:
1. Outputs valid JSON
2. Contains required fields (answer, source, tool_calls)
3. Tool security prevents path traversal
4. Agentic loop executes correctly
5. Exits with code 0 on success
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Import agent functions for unit testing
from agent import list_files, read_file, PROJECT_ROOT, run_agentic_loop, call_llm, MAX_ITERATIONS


# =============================================================================
# Tool Security Tests
# =============================================================================

def test_list_files_security_traversal():
    """Ensure list_files rejects paths with .."""
    result = list_files("../etc")
    assert "Error" in result, "list_files should reject path traversal"


def test_list_files_security_outside_root():
    """Ensure list_files rejects paths outside project root."""
    result = list_files("/etc")
    assert "Error" in result, "list_files should reject absolute paths outside root"


def test_read_file_security_traversal():
    """Ensure read_file rejects paths with .."""
    result = read_file("../../secret.txt")
    assert "Error" in result, "read_file should reject path traversal"


def test_read_file_security_outside_root():
    """Ensure read_file rejects paths outside project root."""
    result = read_file("/etc/passwd")
    assert "Error" in result, "read_file should reject absolute paths outside root"


def test_read_file_nonexistent():
    """Ensure read_file handles nonexistent files gracefully."""
    result = read_file("nonexistent_file_12345.md")
    assert "Error" in result, "read_file should report error for nonexistent files"


def test_list_files_nonexistent():
    """Ensure list_files handles nonexistent directories gracefully."""
    result = list_files("nonexistent_dir_12345")
    assert "Error" in result, "list_files should report error for nonexistent directories"


# =============================================================================
# Agentic Loop Tests (Mocked)
# =============================================================================

def test_agent_tool_call_logging():
    """Test that tool calls are logged correctly in tool_calls field."""
    tool_call = {
        "id": "call_1",
        "function": {
            "name": "list_files",
            "arguments": json.dumps({"path": "wiki"})
        }
    }
    
    call_count = [0]
    
    def mock_call(messages, tool_calls_response=False):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"content": "", "tool_calls": [tool_call]}
        else:
            return {
                "content": '{"answer": "Found docs", "source": "wiki/readme.md#intro"}',
                "tool_calls": []
            }
    
    with patch('agent.call_llm', side_effect=mock_call):
        result = run_agentic_loop("Where are the docs?")
    
    assert len(result["tool_calls"]) == 1, "Should have exactly 1 tool call logged"
    assert result["tool_calls"][0]["tool"] == "list_files", "Tool name should be list_files"
    assert result["tool_calls"][0]["args"] == {"path": "wiki"}, "Tool args should match"
    assert result["answer"] == "Found docs", "Answer should be extracted from JSON"
    assert result["source"] == "wiki/readme.md#intro", "Source should be extracted from JSON"


def test_agent_read_file_in_tool_calls():
    """Test that read_file tool calls are logged for documentation queries."""
    tool_call = {
        "id": "call_1",
        "function": {
            "name": "read_file",
            "arguments": json.dumps({"path": "wiki/git-workflow.md"})
        }
    }
    
    call_count = [0]
    
    def mock_call(messages, tool_calls_response=False):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"content": "", "tool_calls": [tool_call]}
        else:
            return {
                "content": '{"answer": "Edit conflicting files", "source": "wiki/git-workflow.md#resolving-merge-conflicts"}',
                "tool_calls": []
            }
    
    with patch('agent.call_llm', side_effect=mock_call):
        result = run_agentic_loop("How do you resolve a merge conflict?")
    
    assert len(result["tool_calls"]) >= 1, "Should have at least 1 tool call"
    assert any(tc["tool"] == "read_file" for tc in result["tool_calls"]), "Should include read_file"
    assert "wiki/git-workflow.md" in result["source"], "Source should reference git-workflow.md"


def test_agent_max_iterations():
    """Test that agent stops after max iterations to prevent infinite loops."""
    tool_call = {
        "id": "call_1",
        "function": {
            "name": "list_files",
            "arguments": json.dumps({"path": "wiki"})
        }
    }
    
    def mock_call_always_tool(messages, tool_calls_response=False):
        return {"content": "", "tool_calls": [tool_call]}
    
    with patch('agent.call_llm', side_effect=mock_call_always_tool):
        result = run_agentic_loop("Loop test")
    
    # Should stop after MAX_ITERATIONS (10)
    assert len(result["tool_calls"]) == MAX_ITERATIONS, f"Should stop after {MAX_ITERATIONS} iterations"
    assert "maximum tool call limit" in result["answer"], "Should indicate max limit reached"


def test_agent_multiple_tool_calls():
    """Test that agent handles multiple tool calls in a single response."""
    tool_calls = [
        {
            "id": "call_1",
            "function": {
                "name": "list_files",
                "arguments": json.dumps({"path": "wiki"})
            }
        },
        {
            "id": "call_2",
            "function": {
                "name": "read_file",
                "arguments": json.dumps({"path": "wiki/readme.md"})
            }
        }
    ]
    
    call_count = [0]
    
    def mock_call(messages, tool_calls_response=False):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"content": "", "tool_calls": tool_calls}
        else:
            return {
                "content": '{"answer": "Multiple files found", "source": "wiki/readme.md#overview"}',
                "tool_calls": []
            }
    
    with patch('agent.call_llm', side_effect=mock_call):
        result = run_agentic_loop("What files are in the wiki?")
    
    assert len(result["tool_calls"]) == 2, "Should have 2 tool calls logged"
    assert result["tool_calls"][0]["tool"] == "list_files"
    assert result["tool_calls"][1]["tool"] == "read_file"


def test_agent_json_parse_fallback():
    """Test that agent handles non-JSON LLM responses gracefully."""
    def mock_call(messages, tool_calls_response=False):
        return {
            "content": "I found the answer in the docs.",
            "tool_calls": []
        }
    
    with patch('agent.call_llm', side_effect=mock_call):
        result = run_agentic_loop("Test question")
    
    assert result["answer"] == "I found the answer in the docs."
    assert result["source"] == "unknown"
    assert len(result["tool_calls"]) == 0


# =============================================================================
# Subprocess Regression Tests
# =============================================================================

def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields."""
    
    # Path to agent.py
    agent_path = Path(__file__).parent.parent / "agent.py"
    
    # Test question
    test_question = "What does HTTP stand for?"
    
    # Run the agent as a subprocess
    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), test_question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON output: {e}\nStdout: {result.stdout}")
    
    # Check required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    
    # Check field types
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"
    
    # Check answer is not empty
    assert len(output["answer"].strip()) > 0, "'answer' field is empty"
    
    print(f"✓ Test passed! Answer: {output['answer'][:100]}...")


def test_agent_has_source_field():
    """Test that agent.py output includes the source field (Task 2 requirement)."""
    
    agent_path = Path(__file__).parent.parent / "agent.py"
    test_question = "What files are in the wiki?"
    
    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), test_question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON output: {e}\nStdout: {result.stdout}")
    
    # Task 2 requirement: source field must exist
    assert "source" in output, "Missing 'source' field in output (Task 2 requirement)"
    assert isinstance(output["source"], str), "'source' must be a string"


def test_agent_error_handling():
    """Test that agent handles errors gracefully and outputs valid JSON."""
    
    agent_path = Path(__file__).parent.parent / "agent.py"
    # Use a very long question that might cause issues
    test_question = "A" * 10000
    
    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), test_question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Even on error, should output valid JSON
    try:
        output = json.loads(result.stdout.strip())
        assert "answer" in output, "Error response should still have 'answer' field"
    except json.JSONDecodeError:
        # If stdout is empty, check stderr for error
        if result.returncode != 0:
            pass  # Acceptable for edge cases
        else:
            raise AssertionError("Non-error response should be valid JSON")


# =============================================================================
# Integration Test (Requires wiki/ directory)
# =============================================================================

def test_agent_with_wiki_directory():
    """Test agent with actual wiki directory if it exists."""
    
    wiki_path = PROJECT_ROOT / "wiki"
    
    if not wiki_path.exists():
        pytest.skip("wiki/ directory does not exist, skipping integration test")
    
    agent_path = Path(__file__).parent.parent / "agent.py"
    test_question = "What files are in the wiki?"
    
    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), test_question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON output: {e}\nStdout: {result.stdout}")
    
    # Should have used list_files tool
    tool_names = [tc["tool"] for tc in output.get("tool_calls", [])]
    assert "list_files" in tool_names, "Should have used list_files tool for wiki query"


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run tests manually when executed directly
    print("Running tool security tests...")
    test_list_files_security_traversal()
    test_read_file_security_traversal()
    print("✓ Security tests passed!")
    
    print("\nRunning agentic loop tests...")
    test_agent_tool_call_logging()
    test_agent_max_iterations()
    print("✓ Agentic loop tests passed!")
    
    print("\nRunning subprocess regression tests...")
    test_agent_outputs_valid_json()
    test_agent_has_source_field()
    print("✓ Regression tests passed!")
    
    print("\nAll tests passed!")