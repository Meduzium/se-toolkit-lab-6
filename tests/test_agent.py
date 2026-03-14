
## 4. Regression Test (`tests/test_agent.py`)

#!/usr/bin/env python3
"""
Regression tests for agent.py

Tests verify that the agent:
1. Outputs valid JSON
2. Contains required fields (answer, tool_calls)
3. Exits with code 0 on success
"""

import json
import subprocess
import sys
from pathlib import Path


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


if __name__ == "__main__":
    test_agent_outputs_valid_json()
    print("All tests passed!")