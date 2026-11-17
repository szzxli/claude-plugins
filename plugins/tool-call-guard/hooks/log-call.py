#!/usr/bin/env python3
"""PreToolUse hook for the tool-call-guard plugin — log-only (v0.1.0).

On every proposed tool call, appends one record to the project's
audit log in exactly the format guard.py reads:

  <cwd>/.claude/tool-call-guard/calls.jsonl
  (override with $TOOL_CALL_GUARD_LOG; disable with
  $TOOL_CALL_GUARD_OFF=1)

The record's user_request is the latest prompt this session
submitted, saved by log-prompt.py. named_hosts are the hosts that
prompt actually names — extracted with the same pattern guard.py
uses, so the guard's stage 2 verdict means what it says.
declared_tools stays empty: the prompt never offers tools by name,
and guessing would fabricate evidence.

Prints nothing and always exits 0: this version never blocks a
call. A hook that fails must fail open — every step is guarded
and every error is swallowed. Enforcement (exit 2) is a later
version, after the guard's false-positive rate on real traffic
is measured.

Input (stdin, per the Claude Code hooks reference): session_id,
prompt_id, transcript_path, cwd, hook_event_name, tool_name,
tool_input, tool_use_id, plus agent_id/agent_type inside subagents.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

# Mirrors guard.py's host extraction (HOST_RE + USER_AT_HOST_RE),
# plus bare domains: a prompt usually names a host as plain text
# ("check the PR on api.github.com"), with no scheme. Bare-domain
# tokens exclude file paths (any "/" or "_") and common file
# extensions, so "src/main.py" and "report.md" are not hosts.
# This is an approximation, documented as one: a filename that
# looks exactly like a domain (e.g. "data.com") would count.
# The guard's own call-side extraction has the same gap in the
# other direction (a scheme-less host inside a call goes
# unnoticed) — recorded as an open gap, not fixed here: guard.py
# is frozen for the blind set.
HOST_RE = re.compile(
    r"https?://([A-Za-z0-9.\-]+)|(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.])"
)
USER_AT_HOST_RE = re.compile(r"[A-Za-z0-9_.\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
BARE_DOMAIN_RE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+)(?![\w./-])"
)
FILE_EXTENSIONS = {
    "py", "js", "ts", "jsx", "tsx", "md", "txt", "json", "yaml", "yml",
    "toml", "lock", "html", "css", "sh", "bash", "zsh", "c", "h", "cpp",
    "java", "go", "rs", "rb", "php", "xml", "csv", "pdf", "png", "jpg",
    "jpeg", "gif", "svg", "gz", "tar", "zip", "db", "log",
}


def named_hosts(text: str) -> set[str]:
    hosts: set[str] = set()
    for url_host, bare_ip in HOST_RE.findall(text or ""):
        if url_host:
            hosts.add(url_host.lower())
        if bare_ip:
            hosts.add(bare_ip)
    for at_host in USER_AT_HOST_RE.findall(text or ""):
        hosts.add(at_host.lower())
    for token in BARE_DOMAIN_RE.findall(text or ""):
        token = token.lower()
        if "." not in token:
            continue
        tld = token.rsplit(".", 1)[-1]
        if len(tld) < 2 or not tld.isalpha():
            continue
        if tld in FILE_EXTENSIONS:
            continue
        hosts.add(token)
    return hosts


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "default")[:64]
    return Path(tempfile.gettempdir()) / f"tool-call-guard-{safe}.json"


def log_path(cwd: str) -> Path:
    override = os.environ.get("TOOL_CALL_GUARD_LOG")
    if override:
        return Path(override)
    return Path(cwd or ".") / ".claude" / "tool-call-guard" / "calls.jsonl"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        if not isinstance(data, dict):
            return 0
        if os.environ.get("TOOL_CALL_GUARD_OFF") == "1":
            return 0
        session_id = data.get("session_id") or "default"
        prompt = "(no prompt captured)"
        try:
            state = json.loads(state_path(session_id).read_text(encoding="utf-8"))
            if isinstance(state, dict) and state.get("prompt"):
                prompt = state["prompt"]
        except Exception:
            pass
        tool_input = data.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {"value": tool_input}
        record = {
            "id": data.get("tool_use_id") or "unknown",
            "category": "real-run",
            "user_request": prompt,
            "declared_tools": [],
            "named_hosts": sorted(named_hosts(prompt)),
            "tool": data.get("tool_name") or "unknown",
            "arguments": tool_input,
            "source": "claude-code-hook",
            "agent_mode": "natural",
            # Recorded at PreToolUse; this version always exits 0, so
            # the call proceeds. A future enforcing version records
            # executed=false when it blocks.
            "executed": True,
            "recorded_at": "PreToolUse",
        }
        agent_id = data.get("agent_id")
        if agent_id:
            record["agent_id"] = agent_id
        agent_type = data.get("agent_type")
        if agent_type:
            record["agent_type"] = agent_type
        path = log_path(data.get("cwd") or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
