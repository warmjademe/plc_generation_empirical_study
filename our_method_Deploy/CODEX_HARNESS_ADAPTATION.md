# Codex harness mechanisms applicable to PLC generation

This note records the implementation evidence reviewed in the local open-source
Codex checkout and the bounded adaptations used by this service.  It is an
engineering trace, not a claim that the PLC service embeds or reproduces Codex.

## Source mechanisms reviewed

1. `codex-rs/core/src/stream_events_utils.rs` records a completed model item
   before dispatching its tool call.  This keeps the durable history and the
   executed action aligned even when a turn is cancelled later.
2. `codex-rs/thread-store/README.md`, `live_thread.rs`, and the local store use
   canonical append-only history plus separately queryable metadata.  The raw
   history remains the source of truth, while SQLite is a projection for fast
   lookup and resume.
3. `codex-rs/core/src/tasks/mod.rs` gives long-running tasks an explicit
   lifecycle, cancellation token, completion event, and final persistence
   flush.
4. `codex-rs/core/src/compact.rs` replaces oversized conversational history
   with a bounded summary while preserving the current user objective and the
   context needed by the active turn.
5. The repository-level `AGENTS.md` requires model-visible context to grow
   incrementally and imposes hard size limits on injected fragments.

## Adaptation in the PLC service

- Validator execution is treated as a structured tool loop.  Each candidate,
  validator result, diagnostic certificate, and requirement support set is
  written to its attempt directory before the next model request is built.
- The next request uses a bounded state packet rather than unbounded raw logs.
  It retains the frozen contract, the non-regression Anchor, current failures,
  requirements already supported, and a compact failure history.  Raw compiler
  or simulator logs are not copied without a hard character bound.
- SQLite stores the queryable job lifecycle; append-only JSONL and immutable
  attempt artifacts retain contract and validation evidence.  Browser refresh
  resumes polling the same server-side job instead of submitting a duplicate.
- Browser submission persists the exact request together with its idempotency
  key until the server returns a job ID.  A force-refresh in that response-loss
  window replays the same request and resolves to the committed job without
  dispatching a second background contract task.  Once a job ID is known, only
  that identifier is retained for polling recovery.
- Model transport failures, deterministic program failures, and validator
  infrastructure failures use different terminal states.  A failed tool cannot
  be silently converted into a functional pass.
- Candidate generation is narrower than a general coding agent: the model may
  propose ST or Ladder IR, but it cannot change the frozen requirement IDs,
  validators, tests, tool configuration, or success rule.

## Additional delivery hardening

The contract audit now produces a requirement traceability matrix.  Every
requirement must map to semantic evidence, a feedback runtime test, and a
confirmation runtime test; every safety-critical requirement must map to a
formal property.  This closes an important coverage gap, but it does not prove
that an LLM paraphrase is semantically identical to arbitrary natural language.
The deterministic completeness gate and human contract review remain the
controls for that boundary.

An additional deterministic priority audit checks explicitly ordered input
events.  Every input pair in adjacent priority levels must be exercised in both
feedback and sealed tests.  When the pair is active together, governed state is
compared with a counterfactual scan in which the lower event is suppressed.  A
difference means the lower event overrode the declared priority, so the contract
is rejected before candidate generation.

The next useful Codex-inspired improvement is resumable server-side execution
from the last fully persisted candidate.  HTTP job submission is now
idempotent, but individual provider calls and Windows validation requests still
need their own durable execution keys before an interrupted worker can safely
resume inside an existing job.
