# RQ1 exploratory failure-30 pilot

This folder evaluates `baseline1_llm4plc.py` on the 30 semantic failures from the
first frozen 68-task Kimi K3 Direct@1 screening batch. The purpose is to estimate
how often the LLM4PLC-adapted planning and tool-feedback loop can recover a task
that one direct Kimi candidate did not solve.

This is not the final RQ1 sample. The selection is intentionally conditioned on
Direct@1 failure and is not category-balanced: C01 contributes 11 tasks, C02 10,
C03 6, and C05 3. It must be reported as an exploratory pilot. The formal RQ1
comparison will use the final balanced 50-task dataset and paired runs of all
external baselines, internal controls, and the proposed method.

The frozen subset stores the source Kimi result and qualification record for every
selected task. Baseline1 receives only `requirement.md` and `interface.st`; reference
programs, properties, selection evidence, and OpenPLC tests are not placed in its
prompt.

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
experiment repository.
