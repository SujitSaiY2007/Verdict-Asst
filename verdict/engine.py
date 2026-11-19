"""Verdict's compact local-first inference engine."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()

DB = Path(os.getenv("VERDICT_DB", Path.home() / ".verdict" / "cache.db"))


def providers():
    """Return local providers first, then explicitly configured cloud providers."""
    items = [
        ("ollama", os.getenv("VERDICT_OLLAMA_MODEL", "llama3.2"),
         os.getenv("VERDICT_OLLAMA_URL", "http://localhost:11434/v1"), "ollama"),
        ("lmstudio", os.getenv("VERDICT_LMSTUDIO_MODEL", "local-model"),
         os.getenv("VERDICT_LMSTUDIO_URL", "http://localhost:1234/v1"), "lmstudio"),
    ]
    if os.getenv("VERDICT_CLOUD_FALLBACK", "false").lower() == "true":
        cloud = {
            "gemini": (os.getenv("GEMINI_API_KEY"), os.getenv("VERDICT_GEMINI_MODEL"),
                       "https://generativelanguage.googleapis.com/v1beta/openai/"),
            "groq": (os.getenv("GROQ_API_KEY"), os.getenv("VERDICT_GROQ_MODEL"),
                     "https://api.groq.com/openai/v1"),
            "openrouter": (os.getenv("OPENROUTER_API_KEY"), os.getenv("VERDICT_OPENROUTER_MODEL"),
                           "https://openrouter.ai/api/v1"),
        }
        order = os.getenv("VERDICT_CLOUD_ORDER", "gemini,groq,openrouter").split(",")
        for name in order:
            name = name.strip().lower()
            if name in cloud:
                key, model, url = cloud[name]
                if key and model:
                    items.append((name, model, url, key))
    return items


def _db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=5)
    conn.execute("CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, answer TEXT, expires REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS cooldowns (provider TEXT PRIMARY KEY, until REAL)")
    return conn


def _cache_key(mode: str, prompt: str, allow_cloud: bool = False) -> str:
    config = "|".join(os.getenv(k, "") for k in (
        "VERDICT_OLLAMA_MODEL", "VERDICT_LMSTUDIO_MODEL", "VERDICT_GEMINI_MODEL",
        "VERDICT_GROQ_MODEL", "VERDICT_OPENROUTER_MODEL",
    ))
    return hashlib.sha256(f"v1|{mode}|{allow_cloud}|{config}|{prompt}".encode()).hexdigest()


def _cached(key: str):
    with _db() as db:
        row = db.execute("SELECT answer, expires FROM answers WHERE key=?", (key,)).fetchone()
        if row and row[1] > time.time():
            return row[0]
        db.execute("DELETE FROM answers WHERE key=?", (key,))
    return None


def _store(key: str, answer: str):
    ttl = int(os.getenv("VERDICT_CACHE_TTL", "86400"))
    with _db() as db:
        db.execute("INSERT OR REPLACE INTO answers VALUES (?, ?, ?)", (key, answer, time.time() + ttl))
        db.execute("DELETE FROM answers WHERE expires < ?", (time.time(),))
        db.execute("DELETE FROM answers WHERE rowid NOT IN (SELECT rowid FROM answers ORDER BY expires DESC LIMIT 500)")


def _cooling(name: str) -> bool:
    with _db() as db:
        row = db.execute("SELECT until FROM cooldowns WHERE provider=?", (name,)).fetchone()
        return bool(row and row[0] > time.time())


def _cooldown(name: str):
    seconds = int(os.getenv("VERDICT_COOLDOWN", "60"))
    with _db() as db:
        db.execute("INSERT OR REPLACE INTO cooldowns VALUES (?, ?)", (name, time.time() + seconds))


def _make_agent(name: str, model: str, url: str, credential: str) -> Agent:
    provider = OpenAIProvider(
        base_url=url,
        api_key=credential or "ollama",
    )
    return Agent(OpenAIChatModel(model, provider=provider), instructions=(
        "You are Verdict, a careful developer assistant. Be concise, technically precise, "
        "state uncertainty, distinguish evidence from assumptions, and never claim to have "
        "run code or inspected files that were not supplied. Do not invent project context."
    ))


def _run_one(name: str, model: str, url: str, credential: str, prompt: str) -> str:
    timeout = float(os.getenv("VERDICT_TIMEOUT", "20"))
    agent = _make_agent(name, model, url, credential)
    result = agent.run_sync(prompt, model_settings={"timeout": timeout})
    return str(result.output)


def answer(prompt: str, mode: str = "ask", allow_cloud: bool = False) -> str:
    """Run one task; cloud fallback is permitted only by explicit opt-in."""
    if not prompt.strip():
        raise ValueError("Please provide a question or code context.")
    key = _cache_key(mode, prompt, allow_cloud)
    if os.getenv("VERDICT_CACHE", "true").lower() == "true":
        hit = _cached(key)
        if hit:
            return f"{hit}\n\n[Verdict: cached result]"

    configured = providers()
    if not allow_cloud:
        configured = [p for p in configured if p[0] in ("ollama", "lmstudio")]

    errors = []
    for name, model, url, credential in configured:
        if name not in ("ollama", "lmstudio") and _cooling(name):
            continue
        try:
            output = _run_one(name, model, url, credential, f"Task: {mode}\n\n{prompt}")
            if os.getenv("VERDICT_CACHE", "true").lower() == "true":
                _store(key, output)
            return f"{output}\n\n[Verdict: {name}/{model}]"
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            message = str(exc).lower()
            if status == 429 or "429" in message or "rate limit" in message or "quota" in message:
                _cooldown(name)
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    detail = "\n".join(errors) if errors else "No local model is configured and cloud fallback was not authorized."
    return ("Verdict could not reach an available AI model.\n"
            "Your application was not modified. Check that Ollama/LM Studio is running, "
            "or explicitly authorize configured cloud providers.\n\n"
            f"Diagnostics:\n{detail}")


def debate(question: str, allow_cloud: bool = False) -> str:
    """A compact three-stage debate using the same authorized routing policy."""
    optimistic = answer(f"Give three strong arguments in favour of this decision: {question}", "optimist", allow_cloud)
    skeptical = answer(f"Challenge this proposal and identify risks:\n{question}\n\n{optimistic}", "critic", allow_cloud)
    return answer(f"Judge this debate. Give PROCEED, REJECT, MODIFY, or NEEDS_MORE_INFORMATION; explain key strengths, risks and next step.\nQuestion: {question}\nOptimist: {optimistic}\nCritic: {skeptical}", "judge", allow_cloud)
