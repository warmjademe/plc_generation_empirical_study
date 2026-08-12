# RQ1: comparison with PLC-generation agents

RQ1 evaluates the proposed method and external agent workflows on the same frozen
Balanced-100 task set. The task—not an individual candidate, requirement, or test
observation—is the statistical unit. Every method receives at most ten complete
ST candidates per task and uses the common MatIEC, PLCverif, and OpenPLC terminal
decision chain.

The primary external comparisons are `baseline1_llm4plc.py`,
`baseline2_agents4plc.py`, and `baseline3_chatdev.py`. Each is evaluated with
DeepSeek-V4-Flash, GPT-5.6 Luna, Gemini-3.5-Flash-Lite, and Claude Sonnet 5.
`baseline4_claude_code.py` and `baseline5_codex.py` are model-fixed general coding
agent controls. The proposed method is evaluated under the same four model
families as the primary comparisons.

Compact task-level result logs, controller logs, their hashes, and the scripts
that rebuild all RQ1 tables are under [`results/`](results/). Only completed
100-task batches are included there. Historical 30/50-task pilots and aborted
launches are excluded from the paper result set.

## Baselines 4 and 5: independent coding-agent Pass@10

`baseline4_claude_code.py` evaluates Claude Code with the exact Sonnet 5 model,
and `baseline5_codex.py` evaluates Codex with the exact GPT-5.6 Luna model. For
each task, both baselines receive at most ten independent candidate opportunities
and stop at the first candidate that passes MatIEC, PLCverif, and OpenPLC.
Every opportunity starts from the same public requirement and interface in a new
workspace and a new non-persistent session. No previous candidate, compiler or
formal-verification diagnostic, OpenPLC verdict, or attempt index is exposed to
the next generation.

`baseline5_codex.py` evaluates the official Codex CLI as a general-purpose coding
agent with the model fixed to the exact `gpt-5.6-luna` identifier. Claude Code is
likewise fixed to `claude-sonnet-5`; runtime model records are audited so aliases
or fallback models cannot silently enter the comparison.

Codex runs with a fresh temporary `CODEX_HOME`; plugins, remote plugin catalogs,
apps, skills, MCP, subagents, browser/computer tools, hooks, goals, and user rules
are disabled. Claude Code uses safe mode, no session persistence, an empty strict
MCP surface, and only the Read, Write, and Edit built-in tools. Both adapters audit
session uniqueness, identical prompts and initial candidate hashes, tool/file
access, model identity, candidate counts, and the absence of validator feedback.
Any model substitution, reuse of state, extra tool surface, or isolation violation
invalidates the protocol record.

The dataset-100 launcher is `run_datasets100_codex_gpt56_luna_baseline5.sh`. It
reuses existing Codex CLI authentication and does not store credentials in the
experiment repository. Both coding-agent result batches are retained for audit;
because their summaries contain infrastructure-error tasks and fail the strict
whole-batch protocol predicate, they are reported descriptively rather than used
for the primary confirmatory comparison.
