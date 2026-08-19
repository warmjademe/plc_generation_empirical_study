# Agentic Context v5.2: bounded-state recovery

`agentic-context-v5.2-bounded-formal-state-recovery` is a development revision
of v5.1. It preserves the MatIEC, PLCverif, visible OpenPLC, and sealed OpenPLC
judges. It changes only the recovery action after a mandatory formal check is
inconclusive because of resource exhaustion.

PLCverif receives one bounded invocation per candidate. Repeating exactly the
same candidate after a backend timeout cannot add semantic evidence and can
consume another 15 minutes, so v5.2 disables that outer same-candidate retry.
The validator's own fixed backend sequence remains unchanged.

If PLCverif remains inconclusive, the harness may use at most one remaining
candidate slot for a blind public-contract resynthesis. The next request omits
the timed-out program and every verifier diagnostic. It supplies a fixed
`verification_bounded_state` profile that requires threshold-saturating elapsed
counters, forbids an ever-growing global scan clock, and minimizes retained
state. This is resource-oriented generation guidance, not a claim that the
previous candidate violated a functional property.

All v5.1 mechanisms remain enabled: public contract-risk obligations, bounded
sealed-blind restart epochs, duplicate-candidate detection, corrected IEC edge
patterns, and visible OpenPLC failure prefixes. The configuration remains
`development_only`; results on the current 50 tasks cannot serve as an unbiased
final estimate because these tasks informed harness development.

Use `configs/deepseek_v4_flash_agentic_context_v5_2.json`. A publication study
should separately ablate the bounded-state recovery and evaluate the frozen
method on a new task-level holdout.
