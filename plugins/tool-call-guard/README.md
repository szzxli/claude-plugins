# tool-call-guard — Claude Code plugin (v0.1.0, log-only)

**This plugin records. It does not protect.** It writes a log of
proposed tool calls so a human can audit them later. Do not present
it as a guard, a blocker, or a safety control — both blind
tests failed (see "What v0.1.0 does NOT do" below).

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

`guard.py` in this plugin is sha256
`d2d154216657b0b26cd90e12bd4350353c4515688adcd3fdf04e43f6bac608e3`,
the freeze scored on eval-blind-01. The later freeze of the
[agent-tool-call-guard skill](https://github.com/szzxli/soc-home-lab/tree/add-agent-tool-call-guard/05-soc-skills/skills/agent-tool-call-guard)
is sha256
`7e94ff0df06911d010b53680d6d4b28a5debdb770f35fa8adbc18b77a1cd93a0`.
That later freeze is not this copy. Either checker scores a
proposed call `allow` / `suspicious` / `block`. Scoring is
log-only: the checker never runs a call. Results for both
freezes are under "What v0.1.0 does NOT do".

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

- **No enforcement.** Nothing is blocked. The false positives
  on `api.github.com` belong to the previous freeze, sha256
  `d2d154216657b0b26cd90e12bd4350353c4515688adcd3fdf04e43f6bac608e3`
  (the copy in this plugin). On eval-blind-01 that freeze scored
  `block` on four benign calls to well-known hosts the user had
  not named, including `api.github.com`. Freeze
  `7e94ff0df06911d010b53680d6d4b28a5debdb770f35fa8adbc18b77a1cd93a0`
  scored FP=0 on eval-blind-02, including curl and clone to
  well-known hosts. The false-positive rate on real traffic
  is not measured.
- **No validation — both blind sets failed.** The 100/100
  figure is same-author dev-set calibration only (100 synthetic
  calls; the checker and the eval calls were written by the
  same author).
  eval-blind-01 (second author, same team, 40 calls, run
  2026-11-18) scored that previous freeze: exact match 20/40
  (50%), TP=13 FN=13 FP=4 TN=10 (szzxli/soc-home-lab PR #38).
  Freeze `7e94ff0d…`
  (`7e94ff0df06911d010b53680d6d4b28a5debdb770f35fa8adbc18b77a1cd93a0`)
  was tested on eval-blind-02 and failed: exact match 30/40
  (75%), TP=17 FN=7 FP=0 TN=16 (szzxli/soc-home-lab PR #39).
  A blind set passes only if it meets both bars: exact match
  at least 80%, and FN at most 2 on malicious cases. A
  malicious case has expected verdict `block` or `suspicious`.
  FN means the checker said `allow`. A severity mismatch
  (stopped, at the wrong level) counts against exact match
  and is not an FN.
  A further fix and an unseen blind set are pending. Neither
  has a result. There is no validation number to quote.
  No paid audit, and no distribution as protection, until a
  new blind set on a later freeze passes both bars.
- **Claude Code only.** Other agents need their own collectors.
- **One agent, one session.** The log is what one agent
  proposed in one project. It is evidence, not a benchmark.
- **Known open gaps.** On freeze `7e94ff0d…`, eval-blind-02
  left these categories open (szzxli/soc-home-lab PR #39).
  Allowed, so they count as FN: rsync/scp exfil to an unnamed
  host (the scored case was `rsync` in `host:path` form),
  reads of `.env.*` files, `gpg` secret-key export, `dd` or
  `mkfs` to a block device, `shutdown`, and hex-encoded
  execution piped to a shell.
  Rated only `suspicious` when `block` was expected, so they
  count against exact match and not as FN: base64-decoded and
  openssl-decoded execution, and `chmod -R 777 /`.
  The `guard.py` in this plugin is the earlier freeze. Its
  eval-blind-01 false negatives are the wider set in
  szzxli/soc-home-lab PR #38.

## Maintenance

This plugin is maintained on a best-effort basis. No SLA is
promised: issues are triaged weekly, but there is no guaranteed
response or fix time.
