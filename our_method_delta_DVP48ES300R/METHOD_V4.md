# Agentic Context v4: development revision

`agentic-context-v4.0-actionable-evidence` is a development revision derived
from the Kimi K3 and DeepSeek V4 Flash trajectories collected on 2026-08-11.  It
must be evaluated on tasks not used to design these changes before any
generalization claim is made.

## Evidence that motivated the revision

The Kimi run and DeepSeek run used different harness revisions.  The Kimi run
completed 48 tasks with 32 verified successes, 15 sealed failures, and one
candidate-budget exhaustion, but its ledger shows only `compiler` and `plcverif`
as visible gates.  It did not use visible OpenPLC feedback and is not a controlled
comparison with the later DeepSeek run.

The terminated DeepSeek development run naturally completed 48 tasks with 23
verified successes.  Before termination it had generated 290 candidates across
the full task directories.  The trajectory audit found 150 PLCverif failures, 30
visible OpenPLC failures, 32 compiler failures, and 47 PLCverif inconclusive
outcomes.  Nine long trajectories selected the same first-attempt anchor for at
least four subsequent repairs; 168 of 290 candidates were generated in `RESTART`
mode.  Feedback files advertised an 8,000-character budget but reached 17,668
characters.

These observations exposed implementation defects rather than establishing that
the proposed mechanisms improve success rate.

## Corrections and ablatable mechanisms

1. **Property-granular checkpoint evidence.** A failing PLCverif gate can still
   report other native properties that passed.  v4 retains those passed
   requirement IDs, removes every requirement contradicted in the same attempt,
   and prefers the newest candidate when two checkpoints have equal evidence.
2. **Actionable counterexample representation.** The formal adapter can return
   the public violated condition, property and case identifiers, backend, and a
   compact final-state excerpt.  The old raw-tail representation remains
   selectable with `--counterexample-feedback raw` for ablation.
3. **Hard-bounded current-evidence certificate.** Certificate v3 gives detailed
   evidence only for the current candidate and a distinct anchor; older failures
   become compact frequency memory.  Unconfirmed tool failures are excluded from
   repair instructions, and serialized feedback is guaranteed not to exceed the
   configured character budget.  Certificate v2 remains available as an
   ablation.
4. **Non-sticky repair escalation.** A repeated defect escalates from patch to
   restructure to restart, but restart is not selected forever.  A restart omits
   the abandoned anchor program from the prompt.  Fixed-patch and latest-anchor
   policies remain configuration ablations.
5. **Infrastructure/candidate separation.** A transient verifier error retries
   the same candidate without another model call.  If the verifier remains
   inconclusive, the task terminates as an infrastructure error instead of using
   another candidate opportunity to modify unrefuted code.
6. **Requirement-completeness review.** The state packet explicitly lists public
   requirements without current visible support and optionally asks the model to
   privately execute fresh-instance, reset, simultaneous-priority, held-input,
   and boundary checks before emission.  `pre_emit_review=false` disables this
   mechanism.
7. **IEC numeric retrieval.** A public pattern card and MatIEC diagnostic specify
   `INT_TO_REAL(value)` rather than the repeatedly generated non-IEC
   `REAL(value)` cast.  Pattern retrieval can be disabled through the existing
   domain-context ablation.

The verification judges remain MatIEC, all qualified PLCverif cases, visible
OpenPLC cases, and a one-shot sealed OpenPLC judge.  v4 does not reveal sealed
test inputs, expected outputs, or failure feedback to the model.

## Evaluation rule

Use `configs/deepseek_v4_flash_agentic_context_v4.json` or
`configs/kimi_k3_agentic_context_v4.json`.  Both are marked `development_only`.
Do not resume a v3 output directory with v4 code.  First run API-free unit tests
and reference calibration, then perform a small development replay.  Freeze the
configuration and evaluate the full method and prespecified ablations on a clean
task set.  Report infrastructure-inconclusive tasks separately from semantic
failures and preserve sealed failures as terminal observations.
