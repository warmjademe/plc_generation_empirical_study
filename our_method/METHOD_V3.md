# Agent-style context and verification mechanisms

The frozen DeepSeek experiment uses revision
`agentic-context-v3.3-deterministic-wrapper-extraction`. This revision makes the declaration
skeleton semantics explicit: every candidate must contain the supplied
`VAR_INPUT` and `VAR_OUTPUT` blocks. It also returns the earliest MatIEC
diagnostics because later messages are commonly parser cascades, and explicitly
disallows `//` comments unsupported by the frozen MatIEC profile. These changes
alter only generation constraints and feedback quality, not the MatIEC, PLCverif,
or OpenPLC acceptance criteria.

The response parser also accepts a missing `</st_program>` tag only when the text
after `<st_program>` consists of exactly one complete function block ending at
`END_FUNCTION_BLOCK`. It records this extraction mode and never edits the ST body;
the extracted candidate still traverses the full frozen verification chain.

The v3 profile remains a bounded PLC synthesis experiment rather than an
unrestricted coding session. It borrows observable coding-agent mechanisms:
context gathering, tool-mediated action, verification, bounded memory, and
checkpoint selection. OpenAI documents project guidance, on-demand skills,
external tools, and focused subagents as complementary customization layers;
Anthropic describes the coding-agent loop as gathering context, taking action,
and verifying results. The PLC harness instantiates only mechanisms that can be
frozen and ablated under an equal ten-candidate budget.

Official design references:

- https://learn.chatgpt.com/docs/customization/overview
- https://code.claude.com/docs/en/how-claude-code-works

## Full v3 mechanism

1. A deterministic task-state builder records requirement support, regressions,
   current failure signatures, scan semantics, and the selected anchor.
2. A bounded retriever selects at most four generic IEC ST pattern cards using
   only the public requirement and interface text. The library contains no
   benchmark reference program, formal property, or sealed test.
3. Each model opportunity emits one complete candidate. MatIEC compiles it,
   PLCverif evaluates every qualified property, and OpenPLC executes only the
   prespecified feedback-role functional cases.
4. Failures become a deduplicated requirement-level certificate containing the
   newest trace per signature, repetition count, attempt hypotheses, and
   supported-requirement deltas.
5. The strongest non-regressing candidate is the checkpoint for the next repair.
   Repeated candidates or repeated evidence trigger a structural restart.
6. The first visible pass is frozen. A separate OpenPLC run executes only sealed
   cases; its evidence is terminal and is never returned to the model.

The formal and runtime tools remain deterministic actors. The model cannot edit
test partitions, properties, validator commands, budgets, or success criteria.

## Prespecified ablations

| ID | Removed mechanism | Configuration change |
|---|---|---|
| A1 | IEC pattern retrieval | `domain_context.enabled=false` |
| A2 | Compressed agent state | `context_strategy=full_history` and retrieval disabled |
| A3 | Structured evidence v2 | `certificate_version=v1` |
| A4 | Non-regression checkpoint | `anchor_policy=latest` |
| A5 | Adaptive repair policy | `repair_policy=patch` |
| A6 | Visible OpenPLC feedback | remove `openplc_feedback` from validators and required gates |
| A7 | Full method | `configs/kimi_k3_agentic_context_v3.json` |

All variants use the same public task contract, Kimi snapshot, candidate limit,
maximum output tokens, and sealed OpenPLC cases. Since A6 changes what evidence
is visible but not the final judge, it measures the contribution of executable
functional feedback. Candidate-level observations are dependent; the primary
comparison remains paired task-level `VerifiedSuccess@10`.

## Validity boundary

The 48 completed v1 trajectories were inspected to design v3, so they are
development evidence rather than an unbiased confirmation set. A paper claim
requires freezing v3 and evaluating it, its strongest baselines, and the primary
ablations on tasks not used to choose these mechanisms. The current 50-task run
can quantify engineering improvement on the development benchmark, but not by
itself establish generalization.
