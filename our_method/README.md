# Evidence-Guided Bounded Synthesis for IEC Structured Text

This directory contains the experimental harness for generating one complete IEC
61131-3 Structured Text (ST) function block per model opportunity.  A task receives
at most ten candidate programs and stops immediately when a candidate passes every
configured visible gate.  That candidate is frozen and evaluated once by a sealed
judge; sealed evidence is never returned to the model.

The scored validation chain is fixed as **MatIEC -> PLCverif -> OpenPLC**. MatIEC
checks IEC ST compilation, PLCverif checks every mandatory property in the
qualified native fragment, and OpenPLC executes independent functional test
vectors as the terminal judge. The older reference-derived stress and local scan
gates are retained only in archived development runs and do not determine scores
under the current configuration.

The OpenPLC adapter uses a request/acknowledgement wrapper. It installs all inputs
before enabling the function block, executes exactly one DUT scan per requested
test repetition, and acknowledges only after outputs have been copied. This avoids
an unscored all-FALSE startup scan and makes each test case's fresh-instance
semantics explicit. A failing PLCverif run stops at the first trustworthy mandatory
counterexample; a PLCverif pass still requires checking every native case.

The working method name is **Evidence-Guided Bounded Synthesis (EGBS)**.  It is a
research hypothesis, not a claim of novelty.  Compiler- or verifier-guided retry is
already present in prior PLC-generation work.  The mechanism to evaluate here is how
verification evidence is organized under the same candidate and token budget:

- an append-only, hash-chained evidence ledger;
- deterministic requirement-aligned failure certificates instead of raw log dumps;
- selection of a best non-regressing anchor rather than always repairing the latest
  candidate;
- deterministic `PATCH`, `RESTRUCTURE`, and `RESTART` decisions;
- replay/cross-oracle status that separates candidate defects from validator
  disagreement;
- strict isolation of visible feedback tests from the sealed final judge.

The falsifiable question is whether these mechanisms improve sealed
`VerifiedSuccess@10` and reduce candidate/token cost relative to raw-log repair on
the same 50 tasks, same model snapshot, and same budgets.

The current development implementation is revision
`agentic-context-v4.0-actionable-evidence`; its motivation, corrections, and
ablation controls are documented in `METHOD_V4.md`.  The earlier Kimi and
DeepSeek trajectories were used to design v4 and therefore cannot serve as its
unbiased evaluation set.  No v4 success-rate claim has been made yet.

## Current status

Implemented and locally checked now:

- exact candidate accounting, including empty or malformed responses;
- early stopping and a terminal sealed judge;
- OpenAI-compatible Kimi client with model/provider identity logging;
- complete assistant-message preservation for stateful Kimi K3 conversations;
- ST response extraction;
- fail-closed MatIEC, PLCverif/nuXmv/CBMC, and pinned OpenPLC adapters;
- independent OpenPLC functional suites derived from authored base-task oracles
  and explicit composition rules rather than composite-reference execution;
- evidence certificates, non-regression anchor scoring, hash-chained JSONL ledger;
- `evidence`, `raw_repair`, `independent`, and `direct` experiment modes.

Still required before treating the selected set as a paper benchmark:

- complete the frozen 200-task reference qualification and Kimi-K3 Direct@1
  screening;
- freeze five semantic failures per category using the declared role-balance rule;
- independently review the selected 50 task contracts and OpenPLC oracles;
- retain unsupported temporal DSL properties as explicit coverage limitations.

The 200-task screening run is dataset construction and must not be reported as an
unbiased estimate of Kimi-K3 performance on IEC ST tasks.

### Qualified C01 pilot

`configs/kimi_k3_pilot_c01.json` is a deliberately narrow end-to-end profile for
the Boolean task `C01_E01_two_input_permissive`.  It runs MatIEC from its
installation directory, translates the task's mandatory Boolean invariant to a
PLCverif pattern checked by nuXmv, and executes the sealed Boolean vectors in the
pinned OpenPLC v3 runtime.  The formal and OpenPLC adapters reject unsupported
property or interface fragments as inconclusive; they must not be generalized to
the other 49 tasks without separate qualification.

On 2026-08-10, Kimi K3 produced the correct candidate on opportunity 1.  The
original online run nevertheless exhausted ten opportunities because the first
MatIEC adapter was launched from the artifact directory and could not resolve its
relative `lib/ieclib.txt`.  The immutable failed run is retained.  After correcting
the adapter, an API-free replay of the frozen opportunity-1 candidate passed the
interface, MatIEC, visible scan, PLCverif/nuXmv, and sealed OpenPLC gates.  This is
infrastructure qualification evidence, not a paper-scale model result.

The literature, local corpus, and public-code audit found no verifier named
`PurifyPLC`.
The Agents4PLC and MPC-Coder workflows use **PLCverif**, which translates PLC code
and requirements for nuXmv or CBMC.  Consequently, this repository uses the gate
name `plcverif`; it does not relabel PLCverif or an in-house script as a nonexistent
external tool.  `configs/kimi_k3_bool_pilot.json` extends the qualified fragment to
stateless, Boolean-interface tasks whose mandatory properties are propositional
end-of-scan invariants.  Other tasks remain fail-closed as inconclusive.

The Boolean profile was qualified on five generated-dataset tasks before the clean
model runs.  For every task, all gates accepted the reference; the authored
negative control was rejected by the visible scan oracle and PLCverif; and a
separate output-inversion sentinel was rejected by PLCverif and the sealed OpenPLC
judge.  Three subsequent clean Kimi K3 runs (C01 easy, C01 medium, and C03 easy)
each reached `verified_success` on the first candidate.  Across these runs, all
three ledgers verified, each sealed judge was invoked exactly once, and total model
usage was 2,671 tokens.  These are pilot results for the qualified Boolean fragment,
not estimates for the full 50-task benchmark.

## Kimi model configuration

The supplied K3 credential was authenticated on 2026-08-10 using the Kimi Coding
model-list endpoint.  Its compatible base URL is `https://api.kimi.com/coding/v1`,
and that endpoint exposes model IDs `k3` and `k3-256k`.  The same credential returned
HTTP 401 at `https://api.moonshot.ai/v1`; the two account systems must not be treated
as interchangeable.  `configs/kimi_k3.json` therefore requires `KIMI_API_KEY`, uses
model `k3`, and fails if either the credential is absent or the provider resolves a
different model.  The Volcengine `kimi-k2.6` configuration remains a separate
development option whose results must not be labelled as K3.

No credential is stored in this directory.  Supply the selected key through the
environment named in the provider configuration.  Every run ledger records the
requested and resolved model identity.  A fallback is never silent.

## Install and run

```bash
cd /root/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes/our_method
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Run a development task with the deterministic scan engine after explicitly setting
the provider key:

```bash
export ARK_API_KEY='read-from-private-global-configuration'
plc-evidence-loop run \
  --config configs/volcano_kimi_k2_6.json \
  --task ../datasets/tasks/C01_E01_two_input_permissive \
  --output runs/dev-C01 \
  --method evidence
```

The development profile has only interface and deterministic scan-test gates.  It
cannot produce a formally verified score.  Formal study configurations must list
all mandatory visible gates and an independent sealed judge; preflight rejects
missing commands.

## Experimental comparisons

- `direct`: one candidate, no repair feedback;
- `independent`: up to ten independent candidates, no prior candidate or feedback;
- `raw_repair`: repair the latest candidate using bounded raw diagnostics;
- `evidence`: requirement-level certificates, anchor selection, and adaptive repair
  mode under the same maximum number of complete candidates.

The primary metric is task-level `VerifiedSuccess@10`.  Also report cumulative
success for opportunities 1--10, restricted mean attempts (failures truncated at
11), visible-pass/sealed-fail rate, tokens and cost per solved task, repeated-error
rate, safety-regression rate, and oracle disagreements.  Properties, test steps, and
attempts are dependent observations and do not increase the sample size beyond 50
tasks.
