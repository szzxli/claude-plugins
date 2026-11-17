# claude-plugins

Marketplace for Claude Code plugins that audit AI coding agents.
One plugin so far.

## Plugins

- **tool-call-guard** (`plugins/tool-call-guard/`) — log-only
  audit trail for Claude Code tool calls: a `PreToolUse` hook
  records every proposed call and `guard.py` scores it. See the
  plugin's README for install, privacy, and limits.

## Install

These are Claude Code slash commands — run them inside a Claude Code
session, not in your terminal. In your terminal, type `claude` first
and wait for the Claude Code prompt, then run:

```text
/plugin marketplace add szzxli/claude-plugins
/plugin install tool-call-guard@tool-call-guard-marketplace
```

## Status

v0.1.0, log-only. The plugin was built and tested locally
(simulated hook input, real `guard.py` scoring); the marketplace
install path itself is verified after this repo is created, by
running the two install commands in Claude Code. Enforcement
mode is not shipped: the guard's false-positive rate on real
traffic is unmeasured.
