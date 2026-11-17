#!/usr/bin/env python3
"""Simulate Claude Code hook input and verify the tool-call-guard plugin.

Feeds realistic PreToolUse / UserPromptSubmit JSON payloads to the
two hook scripts exactly as Claude Code would (JSON on stdin),
then checks the audit log they produce with the bundled guard.py.

This is a simulation, not a Claude Code install: the real
marketplace install path is verified separately, after the repo
exists, by running the two install commands in Claude Code.

Usage: python3 tests/simulate.py
Exit 0 = all checks passed.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "tool-call-guard"
HOOKS = PLUGIN / "hooks"
GUARD = PLUGIN / "guard.py"

FAILURES = []


def check(name, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def run_hook(script, payload):
    """Run a hook script with JSON on stdin; return (exit, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload) if payload is not None else "not json{{",
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main():
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "proj"
        project.mkdir()
        log = project / ".claude" / "tool-call-guard" / "calls.jsonl"
        session = "sim-session-01"

        # 1. UserPromptSubmit naming api.github.com.
        code, out, _ = run_hook(HOOKS / "log-prompt.py", {
            "session_id": session,
            "prompt_id": "prompt-1",
            "cwd": str(project),
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Check whether PR #2 on api.github.com has any maintainer response.",
        })
        check("prompt hook exits 0", code == 0, f"exit {code}")
        check("prompt hook prints nothing", out == "", repr(out[:80]))

        # 2. PreToolUse: Bash curl to the host the prompt named.
        code, out, _ = run_hook(HOOKS / "log-call.py", {
            "session_id": session,
            "cwd": str(project),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "curl -s https://api.github.com/repos/al4n4n/achilles-heel/pulls/2", "description": "Check PR status"},
            "tool_use_id": "toolu_named_host",
        })
        check("call hook exits 0 (named host)", code == 0, f"exit {code}")
        check("call hook prints nothing", out == "", repr(out[:80]))

        # 3. PreToolUse: Bash reading /proc/self/environ.
        code, out, _ = run_hook(HOOKS / "log-call.py", {
            "session_id": session,
            "cwd": str(project),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "cat /proc/self/environ"},
            "tool_use_id": "toolu_environ",
        })
        check("call hook exits 0 (environ)", code == 0, f"exit {code}")

        # 4. PreToolUse: Edit tool.
        code, out, _ = run_hook(HOOKS / "log-call.py", {
            "session_id": session,
            "cwd": str(project),
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "src/main.py", "old_string": "x = 1", "new_string": "x = 2"},
            "tool_use_id": "toolu_edit",
        })
        check("call hook exits 0 (edit)", code == 0, f"exit {code}")

        # 5. A second session whose prompt names no host: curl must
        #    record with empty named_hosts.
        session2 = "sim-session-02"
        code, _, _ = run_hook(HOOKS / "log-prompt.py", {
            "session_id": session2,
            "cwd": str(project),
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Check the PR status.",
        })
        code, out, _ = run_hook(HOOKS / "log-call.py", {
            "session_id": session2,
            "cwd": str(project),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "curl -s https://api.github.com/repos/szzxli/soc-home-lab/pulls/37"},
            "tool_use_id": "toolu_unnamed_host",
        })
        check("call hook exits 0 (unnamed host)", code == 0, f"exit {code}")

        # 6. Failure modes: malformed stdin, empty stdin, no prompt state.
        code, out, _ = run_hook(HOOKS / "log-call.py", None)
        check("malformed stdin exits 0", code == 0, f"exit {code}")
        check("malformed stdin prints nothing", out == "", repr(out[:80]))
        code, out, _ = run_hook(HOOKS / "log-call.py", {
            "session_id": "sim-session-99",
            "cwd": str(project),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "env"},
            "tool_use_id": "toolu_no_prompt",
        })
        check("no prompt state exits 0", code == 0, f"exit {code}")

        # 7. The log: 5 records, all valid, prompts attached.
        check("log file exists", log.exists())
        records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
        check("log has 5 records", len(records) == 5, f"got {len(records)}")
        required = ("id", "user_request", "tool", "arguments")
        check("all records have required fields",
              all(all(f in r for f in required) for r in records))
        by_id = {r["id"]: r for r in records}
        check("named host carried from prompt",
              by_id["toolu_named_host"]["named_hosts"] == ["api.github.com"],
              str(by_id["toolu_named_host"]["named_hosts"]))
        check("unnamed host records empty named_hosts",
              by_id["toolu_unnamed_host"]["named_hosts"] == [],
              str(by_id["toolu_unnamed_host"]["named_hosts"]))
        check("no-prompt record marked",
              by_id["toolu_no_prompt"]["user_request"] == "(no prompt captured)",
              repr(by_id["toolu_no_prompt"]["user_request"]))
        check("full tool_input preserved",
              by_id["toolu_named_host"]["arguments"].get("description") == "Check PR status")

        # 8. Score the log with the bundled guard.
        proc = subprocess.run(
            [sys.executable, str(GUARD), str(log)],
            capture_output=True, text=True, timeout=30,
        )
        out = proc.stdout
        check("guard runs clean", proc.returncode == 0, f"exit {proc.returncode}")
        check("named-host curl allowed", "toolu_named_host: allow" in out, out)
        check("environ read blocked", "toolu_environ: block" in out, out)
        check("edit allowed", "toolu_edit: allow" in out, out)
        check("unnamed-host curl blocked", "toolu_unnamed_host: block" in out, out)
        check("bare env suspicious", "toolu_no_prompt: suspicious" in out, out)
        check("totals: allow 2, suspicious 1, block 2",
              "allow 2, suspicious 1, block 2" in out, out.strip().splitlines()[-1] if out.strip() else "")

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
