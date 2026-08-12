# Construction and review protocol

## Sampling frame

The benchmark crosses ten PLC control-behavior categories with five prespecified
complexity patterns.  This coverage frame was fixed before evaluating any model.
The benchmark does not estimate how frequently the categories occur in industrial
projects.

For every category the five cases are:

1. one easy, single-mechanism task;
2. one medium task combining normal behaviors;
3. one medium task emphasizing a temporal or boundary condition;
4. one hard task adding fault handling and recovery;
5. one hard task combining components or competing priorities.

No two formal tasks may differ only in names, constants, or application narrative.

## Authoring order

1. Freeze IEC-ST Core and the task matrix.
2. Write requirements, assumptions, and the fixed interface.
3. Review the requirement without seeing generated code.
4. Write a reference implementation.
5. Derive properties and tests independently from requirement identifiers.
6. Add one optional seeded semantic fault as a negative control.
7. Run structural, compiler, dynamic, formal, and optional negative-control checks.
8. Freeze task hashes before model evaluation.

## Review requirements

- One author constructs a task and a second PLC-knowledgeable reviewer independently
  checks every requirement, priority, initialization rule, and expected trace.
- Difficulty and category labels are assigned independently; raw agreement and
  weighted Cohen's kappa are reported.
- A third reviewer audits at least 20% of tasks selected with a fixed random seed.
- Disagreements and every post-review correction are retained in a review ledger.

## Oracle qualification

- The reference program must pass all mandatory gates.
- Every requirement maps to at least one dynamic assertion.
- Safety and key temporal requirements map to formal properties when expressible.
- One seeded fault per task is retained as an optional negative control.  It targets
  a published requirement and should be rejected by at least one oracle before
  release.  It incurs no LLM calls and is not part of model scoring.
- OpenPLC and the formal execution model replay common traces; disagreements are
  investigated before using the task for scoring.

## Leakage controls

- The 50 primary tasks are newly authored and are not copied from public benchmarks.
- Public Agents4PLC tasks are used only for harness development and external
  replication.
- Reference programs and hidden tests are excluded from prompts and retrieval stores.
- Text, AST, control-flow, and requirement-level near-duplicate checks are performed.
- Dataset hashes, prompts, tool versions, and stopping rules are frozen before the
  first scored model run.

## Statistical scope

The task is the unit of analysis.  With 50 paired tasks, the primary study is powered
for practically large method differences rather than small ranking differences.  The
primary contrast is the full verification-guided loop against one prespecified
strongest baseline.  Exact paired tests, effect sizes, and confidence intervals are
reported; repeated model samples reduce stochastic uncertainty but do not increase
the number of independent tasks.
