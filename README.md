# PLC Generation Empirical Study

> Benchmark, verification harness, baselines, and reproducibility artifacts for
> empirical IEC 61131-3 Structured Text generation with MatIEC, PLCverif, and
> OpenPLC.

This repository studies whether a code-generation method can produce a functionally
correct PLC program within a bounded number of complete candidates. The target is
vendor-neutral Structured Text (ST) within the documented IEC 61131-3 subset. A
candidate is counted as successful only if it passes the fixed validation chain:

```text
natural-language requirement + fixed ST interface
                         |
                         v
                 complete ST candidate
                         |
                         v
           MatIEC -> PLCverif -> OpenPLC
             compile     formal     runtime
```

MatIEC checks compilation, PLCverif checks mandatory formal properties, and
OpenPLC executes requirement-derived scan-cycle tests. A compiler pass alone is
therefore not reported as functional correctness. Tool errors, unsupported inputs,
and timeouts are treated as inconclusive rather than successful.

## Repository status

- `datasets_100/` is the current primary benchmark: 100 tasks, with ten tasks in
  each of ten control-behavior categories.
- All 100 bundled reference programs passed the recorded current-toolchain
  revalidation. The immutable summary and validator configuration are under
  `datasets_100/evidence/exact_revalidation/`.
- The proposed harness, external baselines, and internal ablations are implemented.
- Experiment run directories and API credentials are deliberately excluded from
  version control. This repository therefore does not, by itself, state final
  comparative model success rates.

The repository is a research artifact rather than a vendor PLC compiler. Its
results apply to the stated ST subset, benchmark tasks, validators, model versions,
and candidate budgets; they do not establish compatibility with every IEC 61131-3
implementation or physical PLC.

## Benchmark

The benchmark covers ten behavior categories:

1. Boolean and conditional logic
2. Start/stop and retained state
3. Interlocks and safe outputs
4. Edge and event handling
5. Timers and timeouts
6. Counters and batch logic
7. Analog processing
8. Sequential state machines
9. Alarms and fault recovery
10. Multi-device coordination

Each task contains a natural-language requirement, a fixed interface, a reference
implementation, formal properties, OpenPLC cases, provenance, and qualification
evidence. During a scored model run, only `requirement.md` and `interface.st` are
model-visible. Reference programs, properties, negative controls, and OpenPLC
oracles must remain outside the generator's workspace.

The statistical unit is a task—not an individual property, test step, attempt, or
model call. The primary outcome is `VerifiedSuccess@10`: whether at least one of at
most ten complete candidates passes the full validation chain. Empty, malformed,
or interface-changing outputs consume a candidate opportunity.

See [`datasets_100/README.md`](datasets_100/README.md) for the selection rule,
qualification boundary, and rebuild procedure. Earlier construction artifacts are
retained in `datasets/` and `datasets_50/` for provenance; they are not the primary
100-task evaluation set.

## Methods

The proposed method is **Evidence-Guided Bounded Synthesis (EGBS)**. It organizes
compiler and verifier evidence in an append-only ledger, emits requirement-aligned
failure certificates, selects a non-regressing candidate as the next anchor, and
keeps the terminal OpenPLC judge sealed. Details and implementation status are in
[`our_method/README.md`](our_method/README.md).

External comparisons are implemented as:

| Entry point | Comparison method |
|---|---|
| `baseline1_llm4plc.py` | LLM4PLC workflow adapted to the shared task and validator contract |
| `baseline2_agents4plc.py` | Paper-guided Agents4PLC reimplementation |
| `baseline3_chatdev.py` | ChatDev role workflow adapted to emit one ST artifact |
| `baseline4_claude_code.py` | Claude Code with the exact Sonnet 5 model |
| `baseline5_codex.py` | Codex with the exact GPT-5.6 Luna model |

Baselines 4 and 5 use independent `Pass@10` candidates: every opportunity receives
the same public task in a fresh workspace and session, without prior candidates or
validator feedback. Plugins, MCP servers, subagents, browser access, and user-level
instructions are disabled and audited. Both stop early on the first full
MatIEC -> PLCverif -> OpenPLC pass.

Internal controls separate one-shot generation, independent resampling, and
latest-candidate raw-log repair from the full evidence-guided method. See
[`baseline_README.md`](baseline_README.md),
[`ablation_README.md`](ablation_README.md), and [`RQ1/README.md`](RQ1/README.md).

## Repository layout

```text
source_codes/
|-- datasets_100/       # primary balanced benchmark and qualification evidence
|-- our_method/         # EGBS package, configurations, adapters, and tests
|-- RQ1/                # controlled experiment launchers and protocol notes
|-- baseline*.py        # external comparison adapters
|-- ablation*.py        # internal controls and ablations
|-- datasets/           # original 50-task construction artifacts
`-- datasets_50/        # intermediate balanced-50 selection provenance
```

## Installation and checks

Python 3.10 or newer is required. Install the harness in an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ./our_method
python -m unittest discover -s our_method/tests -v
```

Audit the frozen 100-task package:

```bash
python datasets_100/audit_dataset.py
```

The audit checks task identities, category balance, required artifacts, manifest
hashes, interface-oracle consistency, feedback/sealed case presence, and selected
qualification evidence. It does not rerun the external validation tools.

## Running the harness

MatIEC, PLCverif with its selected backend, and the pinned OpenPLC runtime must be
installed separately and reflected in the chosen configuration. First run the
fail-closed preflight:

```bash
plc-evidence-loop preflight \
  --config our_method/configs/<study-config>.json \
  --task datasets_100/tasks/<task-id> \
  --output runs/preflight-<task-id> \
  --method evidence
```

Then run one task:

```bash
plc-evidence-loop run \
  --config our_method/configs/<study-config>.json \
  --task datasets_100/tasks/<task-id> \
  --output runs/<experiment>/<task-id> \
  --method evidence
```

Available harness modes are `direct`, `independent`, `raw_repair`, and `evidence`.
Dataset-scale launchers and machine-specific orchestration examples are under
`RQ1/`. Review their model, provider, worker-count, and output settings before use.

## Reproducibility and secret handling

For every scored experiment, freeze the dataset and validator hashes, exact model
identifier, provider, decoding settings, candidate limit, prompts, worker count,
tool versions, random seeds where applicable, and stopping rule. Retain raw
validator artifacts, token usage, cost, time, infrastructure failures, and all
unsuccessful candidates.

No API key is stored in the repository. Supply credentials through the environment
variable or private credential file named by the selected configuration. Never add
`.env` files, CLI authentication homes, run workspaces, or sealed-oracle material to
a model-visible package or Git commit.
