# DVP48ES300R-oriented PLC generation harness

This directory adapts the method in `../our_method` to Delta's
**DVP48ES300R (DVP-ES3)** target. It generates IEC 61131-3 Structured Text
(ST) or typed Ladder Diagram (LD) function blocks and evaluates them with the same
100-task dataset in `../datasets_100`. Linux performs the model orchestration
and tool-neutral checks; a serial worker on an interactive Windows desktop
performs the Delta-specific compilation, download, and simulator checks.

The implementation evaluates compatibility with the installed ISPSoft and
COMMGR simulator. Passing the experiment is not evidence that a program has
been tested on physical DVP48ES300R hardware.

## Experimental ladder-diagram output

The local implementation can also generate a typed ladder-diagram intermediate
representation by setting `experiment.output_language` to `ld`. Each accepted
model response produces three linked artifacts in its attempt directory:

- `candidate.ld.json`: the executable, schema-checked Ladder IR;
- `candidate.ld.svg`: deterministic rails, contacts, branches, coils, and
  Chinese rung comments for human review;
- `candidate.st`: deterministic IEC ST lowering used by MatIEC, PLCverif, and
  OpenPLC, and as the portable semantic counterpart of the LD artifact.

The initial Ladder IR subset supports Boolean contacts and expressions,
comparisons, normal/set/reset coils, conditional assignments, arithmetic
expressions, and saturating INT/DINT scan counters. Unknown operations, direct
Delta device names, harness identifiers, type errors, and ambiguous mixed coil
writes fail closed before a validator is invoked. The model never emits SVG or
vendor-private source units directly.

For the calibrated Boolean subset, the Delta gate now exports an ISPSoft native
`[FB,LD]` source unit, imports and compiles that FBU, and executes it through an
independent ST test harness and COMMGR. The native subset contains AND/OR
topologies, normally-open and normally-closed contacts, and normal/set/reset
coils. Comparisons, arithmetic, assignments, counters, timers, edges, and
vendor function blocks still fail closed at native export until their official
encodings are calibrated. The portable ST lowering remains available to the
three tool-neutral gates and is never presented as native LD.

Run the offline fixture without a model or Windows worker:

```bash
python3 scripts/ladder_tool.py \
  --input tests/fixtures/ladder/MotorControl.ld.json \
  --interface tests/fixtures/ladder/MotorControl.interface.st \
  --task-id MotorControl \
  --st-output /tmp/MotorControl.st \
  --svg-output /tmp/MotorControl.svg \
  --ispsoft-source-output /tmp/MotorControl.Unzipped.src
```

Development-only end-to-end configurations are
`configs/teamorouter_claude_sonnet5_dvp48es300r_ladder_v1.json` and
`configs/deepseek_v4_flash_dvp48es300r_ladder_v1.json`. The DeepSeek profile
uses the provider's lowercase `deepseek-v4-flash` identifier and explicitly
disables thinking mode; otherwise the provider can spend the complete output
budget on reasoning without returning a Ladder IR document.

## Validation protocol

Each complete model response counts as one candidate. A task may use at most
ten candidates and stops when a candidate passes all visible gates and the
terminal sealed gate. The configured order is:

1. **MatIEC:** compile the IEC ST candidate.
2. **PLCverif:** check every mandatory property supported by the qualified
   native PLCverif translation.
3. **Visible OpenPLC:** execute the feedback test vectors in pinned OpenPLC v3.
4. **Visible Delta validation:** translate the candidate into an ISPSoft source
   unit, compile it with ISPSoft 3.24, download it into the DVP-ES3 simulator,
   and drive the visible vectors through COMMGR 2.11.
5. **Sealed validation:** freeze the candidate and run the hidden OpenPLC and
   ISPSoft/COMMGR vectors once. Hidden vectors and mismatches are never returned
   to the model.

A task is a verified success only when every required gate returns `pass`.
Compiler or runtime failures at visible gates may guide another candidate;
unconfirmed tool failures are kept separate from candidate defects. A sealed
failure can trigger only the method's bounded blind restart and never reveals
the hidden trace.

## Delta-specific adapter

The adapter in `src/plc_loop/delta_dvp/` parses one complete function block and
generates an ISPSoft `MAIN` test program. For ST candidates, MAIN contains:

- the candidate's retained state and body, inlined to avoid ISPSoft importer
  cache reuse;
- deterministic M-device mappings for inputs, output comparisons, and the
  request/acknowledgement scan protocol;
- a candidate-specific 64-bit image identity written on every PLC scan.

For a Ladder IR candidate in the calibrated subset, `native_ld.py` instead
builds a native `[FB,LD]` FBU. MAIN instantiates that function block, maps the
same M-device protocol to its ports, and reads its outputs. The submitted job
hashes the canonical Ladder IR, native LD source, encrypted FBU, ST harness,
runtime suite, and image identity independently.

The parser also enforces candidate isolation: direct Delta devices such as
`M1000` or `Y0`, located IEC addresses, and the `EGBS_` harness namespace are
not available to generated code. This prevents a candidate from reading test
inputs or writing request, acknowledgement, comparison, or identity coils
outside its declared task interface.

Target compatibility is checked before a Windows job is submitted. In the
installed DVP-ES3 target, ISPSoft 3.24 reports error 200 for IEC `TON` and
`TIME` locals because these names are not exposed as local symbol types. Such a candidate
therefore receives a visible, actionable compatibility failure and must use a
saturating scan counter derived from the task's declared scan period. The
restriction is target-specific; MatIEC or OpenPLC acceptance alone does not
establish DVP-ES3 compatibility.

The same confirmed restriction is included in the target-specific generation
context, so it is available before the first candidate rather than only after a
Windows rejection. Job preparation independently rejects `TON`, `TIME`, and direct
address/namespace violations. It also records a non-blocking advisory when a
retained-`INT` self-increment is neither protected by an explicit upper-bound
guard nor dominated by a same-scan literal reset. The latter is not a semantic
proof because state transitions may bound the value. This prospective policy
was added after diagnosing the frozen 100-task run and is not used
retroactively to alter that run's score.

Before applying a test vector, COMMGR reads all 64 identity coils. A mismatch
is fail-closed as infrastructure inconclusive, preventing an old simulator
image from being scored as the current candidate. Every test case is downloaded
as a fresh image to implement the dataset's fresh-function-block-instance
assumption.

The Windows worker in `windows/Run-DvpValidationWorker.ps1` restores a clean
ISPSoft project for each job, verifies all submitted artifact hashes, imports
the native FBU when present and then `MAIN`, compiles the combined project,
downloads it, starts the simulator, and invokes
`windows/Invoke-DvpRuntimeCase.ps1`. Only one worker is allowed because the
configured COMMGR DVP simulator exposes one serial execution channel.

## Execution architecture

```text
huashuo: Sonnet + MatIEC + PLCverif + OpenPLC
                    |
                    | redirected-drive spool
                    v
Windows RDP session: ISPSoft -> DVP-ES3 Simulator -> COMMGR Oracle
                    |
                    v
huashuo: immutable result + evidence ledger + next method decision
```

`scripts/start_huashuo_dvp_bridge.sh` maintains the headless RDP session and
maps `dvp_bridge/dvp-spool` into Windows. Jobs may be prepared concurrently,
but the Windows worker claims and evaluates them serially. Two generation
workers are sufficient to keep this queue occupied without creating excessive
wait-time timeouts.

## Configuration

The formal experiment configuration is
`configs/teamorouter_claude_sonnet5_dvp48es300r_v1.json`. It requires the exact
resolved model ID `claude-sonnet-5`; provider mismatch or silent fallback causes
the task to fail closed. Credentials and the private ISPSoft source-unit
password are read only from environment variables and are not stored here.

The immutable 100-task raw run uses v1. The companion
`configs/teamorouter_claude_sonnet5_dvp48es300r_v2.json` preserves the model,
candidate budget, method settings, and verification chain while identifying the
post-run target-type preflight and compile-summary repair. V2 is used only for
an independent rerun of every task whose v1 terminal state is
`infrastructure_error`; raw and infrastructure-corrected rates are reported
separately.

Required private variables are:

```bash
TEAMOROUTER_API_KEY=...
DELTAPLC_ISPSOFT_SOURCE_PASSWORD=...
WINDOWS_RDP_PASSWORD=...
```

The Linux host must also provide `gcc`. PLCverif can fall back from nuXmv to
CBMC for an otherwise valid candidate, and CBMC invokes GCC as its C
preprocessor. The validator now fails closed when this dependency is absent.

## Install and test

```bash
cd /home/qyb/RESEARCH/PLC_Generation/PLC_Generation_Empirical_Study/source_codes/our_method_delta_DVP48ES300R
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Start the Windows bridge from huashuo after loading the private environment:

```bash
set -a
. "$HOME/.config/plc-dvp/private.env"
set +a
scripts/start_huashuo_dvp_bridge.sh
```

Run the Balanced-100 experiment:

```bash
set -a
. "$HOME/.config/plc-dvp/private.env"
set +a
export DELTAPLC_SPOOL_ROOT="$PWD/dvp_bridge/dvp-spool"
# Optional when the local DNS cache has not followed dynamic DNS:
# export DELTAPLC_RDP_TARGET="<current-address>:33389"

.venv/bin/python scripts/run_method_batch.py \
  --config configs/teamorouter_claude_sonnet5_dvp48es300r_v1.json \
  --dataset-root ../datasets_100 \
  --output runs/dvp48es300r_sonnet5_balanced100 \
  --method evidence \
  --workers 2
```

## Evidence and scoring

Each task directory records candidate source, model request/response metadata,
individual gate results, method state, and the hash-chained ledger. The batch
summary reports task count, verified-success count and rate, terminal states,
candidate use, model-identity checks, sealed-query checks, and ledger validity.
The authoritative Delta evidence remains under
`dvp_bridge/dvp-spool/results/<job-id>/` and includes the immutable manifest,
ISPSoft screenshots, compile summary, COMMGR observations, and final result.

The main reported success rate is:

```text
verified tasks / 100
```

Infrastructure-inconclusive tasks are reported separately and are not silently
converted into functional failures or successes. Candidate count, token usage,
API cost, gate latency, and Windows validation workload are retained for the
resource analysis.

After `batch_summary.json` has been written, run the independent cross-layer
audit. It rechecks every ledger and model identity, verifies the frozen source
archive, and links each Delta gate back to its hash-verified Windows spool job:

```bash
.venv/bin/python scripts/audit_dvp48es300r_batch.py \
  --config configs/teamorouter_claude_sonnet5_dvp48es300r_v1.json \
  --dataset-root ../datasets_100 \
  --run-root runs/dvp48es300r_sonnet5_balanced100 \
  --spool-root dvp_bridge/dvp-spool \
  --frozen-source runs/dvp48es300r_sonnet5_balanced100/frozen_method_source.tar.gz \
  --frozen-source-sha256 runs/dvp48es300r_sonnet5_balanced100/frozen_method_source.sha256 \
  --output runs/dvp48es300r_sonnet5_balanced100/audit_final.json
```

The final success rate is reported only when this command returns
`"audit_pass": true` for all 100 tasks.

Because the authored runtime suites are bounded, a formal success means that a
candidate passed the prespecified Oracle; it is not a proof over every possible
input history. `scripts/audit_reference_differential.py` provides a post-hoc,
non-scoring diagnostic that runs each successful candidate and the reference
side by side on additional deterministic sequences. A mismatch is reviewed as
possible Oracle undercoverage rather than silently changing the frozen score.

## Calibration evidence

The Delta layer was calibrated on 2026-08-18 before the 100-task run:

- a real Sonnet candidate for `C01_B02_composite` passed MatIEC, all native
  PLCverif cases, visible OpenPLC, visible ISPSoft/COMMGR cases OT01--OT02, and
  sealed ISPSoft/COMMGR cases OT03--OT05 on its first candidate;
- `calibration/C01_B02_known_bad_vote.st` is compile-valid but deliberately
  forces the two-out-of-three vote to `FALSE`; ISPSoft accepted it and COMMGR
  rejected OT02 with the expected R5 output mismatch;
- changing the candidate image changes the 64-bit identity. This calibration
  detected and led to correction of an automation error that had closed the
  download dialog instead of pressing `Start transfer`.
- `calibration/fresh_instance_reset` sets retained state in one case and checks
  that a subsequent redownload starts from FALSE; both COMMGR cases passed.
- `calibration/C01_B04_reference_divergence` reproduces a post-hoc Oracle gap:
  the reference passes the added three-scan vector while one formally accepted
  candidate is rejected by both OpenPLC and COMMGR on `B_RunPermit` and
  `B_Degraded`. This evidence is diagnostic and is not added retroactively to
  the prespecified success criterion.
- `calibration/timer_scan_semantics` establishes the OpenPLC boundary for a
  300 ms timer under the dataset's 100 ms end-of-scan convention, then records
  ISPSoft's deterministic rejection of the same IEC `TON` declaration for the
  DVP-ES3 target. This calibration motivates the pre-submission compatibility
  diagnostic above; it is not part of the task score.

These checks qualify the measurement path; they are not included in the
Balanced-100 success-rate numerator or denominator.
