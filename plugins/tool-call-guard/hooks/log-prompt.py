#!/usr/bin/env python3
"""UserPromptSubmit hook for the tool-call-guard plugin.

Saves the submitted prompt (verbatim) to a per-session state file
so the PreToolUse hook can attach it to each tool call as the
user_request. That is the whole job: without the prompt, the guard
cannot tell which hosts the user named, and every external call
reads as an unseen host.

Prints nothing (stdout on UserPromptSubmit becomes context Claude
can see). Always exits 0. A failure here must never block the
prompt, so every step is guarded and every error is swallowed.
"""

import json
import re
import sys
import tempfile
from pathlib import Path


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "default")[:64]
    return Path(tempfile.gettempdir()) / f"tool-call-guard-{safe}.json"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        if not isinstance(data, dict):
            return 0
        state_path(data.get("session_id") or "default").write_text(
            json.dumps(
                {"prompt": data.get("prompt") or "", "cwd": data.get("cwd") or ""},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
