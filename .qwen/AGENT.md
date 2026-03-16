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