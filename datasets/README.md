# IEC-ST-VerifyBench

IEC-ST-VerifyBench is the evaluation dataset for the PLC code-generation empirical
study.  It contains 50 semantically distinct Structured Text (ST) generation tasks
organized as ten control-behavior categories with five tasks per category.

The benchmark evaluates whether a method can produce, within at most ten complete
candidate programs, an implementation that satisfies a fixed interface, executable
scan-cycle tests, and formal requirements.  It does not target a particular PLC
vendor and does not claim support for the whole of IEC 61131-3.  Its language target
is the explicitly documented `IEC-ST Core v1` profile in `IEC_ST_CORE.md`.

## Dataset design

Each category contains one easy, two medium, and two hard tasks.  The benchmark
therefore contains 10 easy, 20 medium, and 20 hard tasks.  Medium and hard tasks are
intentionally oversampled because the study concerns bounded iterative repair and
because simple syntax-only tasks provide little evidence about functional
correctness.

The ten primary categories are:

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

This is a coverage benchmark, not a random sample from an estimated population of
industrial PLC projects.  Claims based on it must be limited to the documented task,
language, complexity, and execution profiles.

## Layout

```
datasets/
  README.md
  IEC_ST_CORE.md
  SCHEMA.md
  CONSTRUCTION_PROTOCOL.md
  manifest.jsonl
  dataset_summary.json
  tasks/
    C01_E01_two_input_permissive/
      metadata.json
      requirement.md
      interface.st
      reference.st
      properties.json
      tests_feedback.json
      tests_hidden.json
      negative_control/
      validation_report.json
  tools/
    build_dataset.py
    validate_dataset.py
```

Each task is the statistical unit.  Individual properties, test steps, and repeated
samples must not be reported as independent tasks.  Each task also contains one
optional automatically seeded negative-control program.  It checks whether the
oracles can reject an intentionally faulty implementation; it is never sent to an
LLM, is not an additional task, and is excluded from model cost and success rates.

## Model-visible task versus private answer material

The model receives only `requirement.md` and `interface.st`.  The model must generate
the complete candidate ST program.  `reference.st` is not part of the question or
the prompt: dataset authors use it only to demonstrate that the contract is
satisfiable and to qualify the test oracle.  Feedback tests, formal properties,
hidden tests, reference code, and negative controls remain outside the model's file
view.

For scored experiments, create physically separated trees rather than relying only
on prompt construction:

```bash
python3 tools/export_evaluation_packages.py --output packages/internal_v0_1
```

Only `public_tasks/` may be mounted in the model worker.  The feedback harness gets
`visible_oracles/`; the terminal judge alone gets `sealed_oracles/`; and
`qualification_only/`, which contains `reference.st`, is never mounted during model
evaluation.

## Verification contract

A generated candidate is counted as a verified pass only when it:

1. preserves the declared function-block interface and stays within IEC-ST Core v1;
2. passes the configured ST compiler checks;
3. passes every feedback test used by the generation loop;
4. satisfies every mandatory formal property;
5. passes the sealed OpenPLC tests that are not returned to the generator.

Tool errors, unsupported constructs, and timeouts are `INCONCLUSIVE`, not passes.

The current dataset build includes complete task artifacts and structural validation.
Compiler, model-checker, and OpenPLC results are recorded separately in each
`validation_report.json`; they must not be marked as passing until the pinned tools
have actually been run.

## Ten-opportunity protocol

An opportunity is one complete candidate ST program.  Empty, truncated, unparsable,
or interface-changing outputs consume an opportunity.  Deterministic validator calls
do not consume a generation opportunity, but their count, duration, and result are
logged.  Any auxiliary LLM call must be included in the method's call and token
budget.

The primary metric is `VerifiedSuccess@10`, the proportion of tasks for which the
method submits a candidate passing the sealed judge within ten candidates.  Adaptive
repair attempts are dependent samples, so the standard independent-sampling
`pass@k` estimator is not used for the primary comparison.

## Rebuilding and checking

Run:

```bash
python3 tools/build_dataset.py
python3 tools/validate_dataset.py
```

`build_dataset.py` is the canonical source for task content.  Generated task files
must not be edited without updating the builder, otherwise the next build will
overwrite the change.

## Release status

The dataset is currently an internal research artifact.  A redistribution license
has not yet been selected.  Before public release, pin all tool versions, complete
two-person task review, validate all reference programs and optional negative
controls, remove sealed
test answers from the public pre-evaluation package, and select an explicit license.
