# External PLC-generation baselines

These entry points are external-method comparisons and are distinct from the
`ablation*.py` internal controls.

| Entry point | Method identity | Reproduction status | Candidate process |
|---|---|---|---|
| `baseline1_llm4plc.py` | LLM4PLC | Official workflow and public prompts adapted to the shared task format and judges | Model-based plan; code; iterative latest-code repair from MatIEC/PLCverif feedback |
| `baseline2_agents4plc.py` | Agents4PLC | Reimplemented from the paper because the complete author workflow is not public | Deterministic public-corpus retrieval; Planning Agent; Coding Agent; Validation Agent; Debugging Agent |
| `baseline3_chatdev.py` | ChatDev 1.0 | Official role workflow adapted to emit one IEC ST artifact | Product analysis; CTO design; Programmer; Code Reviewer; Programmer revision |
| `baseline4_claude_code.py` | Claude Code with Sonnet 5 | Official Claude Code CLI in isolated non-interactive mode | Read/edit agent; iterative MatIEC/PLCverif feedback; one continuing session per task |
| `baseline5_codex.py` | Codex with GPT-5.6 Luna | Official Codex CLI in isolated non-interactive mode | Fresh coding-agent session per candidate; persistent public artifact and visible MatIEC/PLCverif feedback |

Baselines 1--5 use the same public task contract, ten-candidate upper bound, and
MatIEC -> PLCverif -> terminal sealed OpenPLC judge. Each comparison run freezes
its model configuration. They stop at the first full pass, and OpenPLC contents
are never returned to an agent.
The number of complete ST candidates is the primary opportunity budget; auxiliary
planning, reviewing, and debugging calls are recorded separately, and token, model
call, and wall-clock costs must also be reported.

The adapters intentionally do not claim bit-for-bit equivalence:

- The original LLM4PLC pipeline includes user interaction and LLM-generated SMV.
  For the automatic common-task comparison, human feedback is disabled and the
  generated ST is judged by the frozen deterministic PLCverif adapter.
- The Agents4PLC release states that its full multi-agent implementation cannot be
  released. The adapter is therefore labelled `paper-reimplemented`, pins the
  release commit, uses only a frozen public IEC corpus for retrieval, and logs every
  role call.
- The Agents4PLC experiment used the classic ChatDev software-company workflow.
  The adapter pins the `chatdev1.0` branch rather than ChatDev 2.0 and removes
  irrelevant GUI, documentation, and multi-file phases while preserving the product,
  technology, programmer, and reviewer roles.

Example after the final qualified dataset and its qualification record are frozen:

```bash
export DEEPSEEK_API_KEY='read from the private environment file'
python3 baseline2_agents4plc.py \
  --config our_method/configs/deepseek_v4_flash_external_baselines.json \
  --dataset-root /path/to/final_50_tasks \
  --qualification /path/to/qualification.json \
  --output /path/to/runs/baseline2_agents4plc_kimi_k3 \
  --workers 2
```

Every run binds its adapter and model configuration, dataset tree, and qualification
record by hash; applicable reproduced methods also bind their upstream commit and
public retrieval corpus. Reference programs, formal properties, negative controls,
and OpenPLC tests are excluded from prompts.

## Baseline 4: Claude Code with Sonnet 5

Baseline 4 is intentionally a coding-agent comparison rather than another
OpenAI-compatible chat wrapper. It calls the official `claude` CLI with the full
`claude-sonnet-5` selector and accepts no fallback model. Runtime stream events
must resolve exclusively to a Sonnet 5 identifier; an absent or different model
terminates the task as an infrastructure error.

Each task receives a fresh Claude Code session and a temporary workspace outside
the research tree containing only `requirement.md`, `interface.st`, `candidate.st`, and the latest visible
`feedback.md`. Safe mode disables local CLAUDE.md files, hooks, skills, plugins,
MCP servers, and other user customizations. Only the built-in Read, Write, and Edit
tools are enabled, and their paths are audited. MatIEC and PLCverif run outside the
agent and may supply feedback for the next candidate. OpenPLC remains a terminal
sealed judge and is never exposed to Claude Code.

Authenticate the official CLI before the experiment (`claude auth login` or the
site-approved API-key mechanism), then run:

```bash
python3 baseline4_claude_code.py \
  --config our_method/configs/claude_code_sonnet5_external_baseline.json \
  --dataset-root datasets_100 \
  --qualification datasets_100/evidence/exact_revalidation/calibration_summary.json \
  --output /path/to/runs/baseline4_claude_code_sonnet5 \
  --workers 2
```

The primary opportunity budget is ten complete `candidate.st` artifacts per task.
The summary also reports Claude Code invocations, internal agent turns, tokens,
cost, CLI version, resolved model identifiers, and protocol-audit results.

## Baseline 5: Codex with GPT-5.6 Luna

Baseline 5 calls the official `codex exec` interface and fixes the model to the
exact `gpt-5.6-luna` identifier. Each candidate uses a fresh isolated Codex home
and agent session, while the public workspace carries forward `candidate.st` and
the latest visible `feedback.md`. The adapter disables user configuration and
exec-policy rules, excludes project instruction files, and audits the resolved
model and file/command activity from Codex JSONL and rollout artifacts.

Run the dataset-100 experiment with:

```bash
RQ1/run_datasets100_codex_gpt56_luna_baseline5.sh
```

The result records the Codex CLI version and executable hash, exact runtime model,
candidate/model-call counts, completed turns and items, token usage, estimated
cost, and isolation audits. OpenPLC remains terminal and sealed.
