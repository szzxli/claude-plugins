# tool-call-guard — Claude Code plugin (v0.1.0, log-only)

**This plugin records. It does not protect.** It writes a log of
proposed tool calls so a human can audit them later. Do not present
it as a guard, a blocker, or a safety control — the checker behind
it failed its blind test (see "What v0.1.0 does NOT do" below).

A log-only audit trail for Claude Code tool calls. Every proposed
tool call is recorded to the project's audit log, in the format
`guard.py` scores. Nothing is blocked in this version.

## Install

These are Claude Code slash commands — run them inside a Claude Code
session, not in your terminal. In your terminal, type `claude` first
and wait for the Claude Code prompt, then run:

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
(sha256 `7e94ff0df06911d010b53680d6d4b28a5debdb770f35fa8adbc18b77a1cd93a0` — re-frozen 2026-11-18 after the failed blind set; see the skill's EVAL.md).
It scores each proposed call `allow` / `suspicious` / `block` —
log-only, it never runs a call.

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
- **No validation — the blind set failed.** The guard's 100/100
  is same-author dev-set calibration only (100 synthetic calls,
  checker and eval calls written by the same author). The
  second-author blind set (same team, 40 calls, run 2026-11-18)
  scored **20/40 exact match (50%)**, below the 80% bar:
  TP=13, FN=13, FP=4, TN=10. Misses (13) outnumber false
  positives (4) — a missed call can execute; a false positive
  is visible and hand-clearable. Until the guard is fixed,
  re-frozen, and re-tested blind above the bar, there is no
  validation number to quote, **no paid audit may rest on the
  guard, and no distribution push may promote it as protection.**
  A false-negative gate is proposed (not yet decided — see the
  validation plan): a future blind set must also keep misses at
  or below the proposed bar.
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

## Maintenance

This plugin is maintained on a best-effort basis. No SLA is
promised: issues are triaged weekly, but there is no guaranteed
response or fix time.
