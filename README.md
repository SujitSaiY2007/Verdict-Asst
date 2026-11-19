# Verdict

Verdict is a lightweight, free-first AI assistant for developers. It answers technical questions, explains code, analyzes errors, reviews snippets, and helps compare engineering decisions from the terminal or an MCP-compatible coding assistant.

## Features

- Local-first inference with Ollama or LM Studio.
- Optional cloud fallback, disabled by default and requiring per-request permission.
- Local SQLite response cache.
- CLI and MCP interfaces.
- Ask, explain, debug, review, and three-stage decision modes.

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
```

For local AI, install [Ollama](https://ollama.com/) and download a model:

```bash
ollama pull llama3.2
```

Copy `.env.example` to `.env` and adjust the model name if needed. Cloud providers are optional; configure a provider and set `VERDICT_CLOUD_FALLBACK=true` only if you want to enable them. A request must also explicitly use `--allow-cloud`.

## Use

```bash
verdict ask "What is a Python decorator?"
verdict explain "Explain this function"
verdict debug "Paste an error or log"
verdict review "Paste code to review"
verdict decide "Should I use SQLite or PostgreSQL?"
git diff | verdict review
```

## MCP

Start the local MCP server with:

```bash
verdict mcp
```

Example Codex configuration:

```toml
[mcp_servers.verdict]
command = "verdict"
args = ["mcp"]
```

## License

Apache-2.0. See `LICENSE`.
