# tool-call-guard — Claude Code plugin (v0.1.0, log-only)

A log-only audit trail for Claude Code tool calls. Every proposed
tool call is recorded to the project's audit log, in the format
`guard.py` scores. Nothing is blocked in this version.

## Install

```text
/plugin marketplace add szzxli/claude-plugins
/plugin install tool-call-guard@tool-call-guard-marketplace
```

Requires Python 3.8+ on your machine, no other dependencies.
Both hooks are short, standard-library-only Python — read them:
`hooks/log-prompt.py` and `hooks/log-call.py`.

## What it does

Two hooks work together:

- `UserPromptSubmit` (`log-prompt.py`) saves each submitted
  prompt, verbatim, to a per-session state file in your OS temp
  directory. Without the prompt, the guard cannot tell which hosts
  you named.
- `PreToolUse` (`log-call.py`) fires before every proposed tool
  call and appends one record to the audit log:

```text
<project>/.claude/tool-call-guard/calls.jsonl
```

Each record carries the prompt as `user_request`, the hosts that
prompt actually named as `named_hosts`, the tool name and the full
`tool_input` as `arguments`, plus `source: claude-code-hook`.
`declared_tools` stays empty: a prompt never offers tools by
name, and guessing would fabricate evidence.

Both hooks print nothing and always exit 0. A hook that fails
fails open — it must never block your agent or stall your prompt.

## Scoring the log

```text
python3 ${CLAUDE_PLUGIN_ROOT}/guard.py <project>/.claude/tool-call-guard/calls.jsonl
```

`guard.py` is the same checker as the
[agent-tool-call-guard skill](https://github.com/szzxli/soc-home-lab/tree/add-agent-tool-call-guard/05-soc-skills/skills/agent-tool-call-guard)
(sha256 `d2d15421…`), frozen for independent validation. It scores
each proposed call `allow` / `suspicious` / `block` — log-only,
it never runs a call.

## Environment variables

- `TOOL_CALL_GUARD_LOG` — write the log somewhere else instead
  of the project default.
- `TOOL_CALL_GUARD_OFF=1` — stop logging without uninstalling.

## Privacy

The log stays on your machine, in your project. Nothing is sent
anywhere. If you share a log for an audit, scrub it first (the
skill's `scrub.py` does this) and read every line before it
leaves your boundary.

## What v0.1.0 does NOT do

- **No enforcement.** Nothing is blocked. The guard's
  false-positive rate on real traffic is not yet measured —
  in the first real run it blocked 4/4 benign GitHub API reads,
  because no user names `api.github.com`. Blocking mode waits
  for a workflow-host mechanism and a measured false-positive
  rate.
- **No independent validation.** The guard's 100/100 is a
  self-test on synthetic calls. The second-author blind set
  has not been run. Do not quote any number from this plugin
  as production performance.
- **Claude Code only.** Other agents need their own collectors.
- **One agent, one session.** The log is what one agent
  proposed in one project. It is evidence, not a benchmark.
- **Known open gaps (checker frozen, fix after the blind set).**
  The guard's call-side host extraction misses a host written
  without a scheme (`curl api.github.com/...`), so that call
  would not even reach the unseen-host check. The hook's
  bare-domain extraction from prompts is an approximation:
  it excludes file paths and common file extensions, but a
  filename that looks exactly like a domain would count as a
  named host.
