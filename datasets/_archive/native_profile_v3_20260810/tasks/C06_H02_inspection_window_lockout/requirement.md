# C06_H02_inspection_window_lockout: Inspection-window reject lockout

## Objective

Implement `C06_H02_inspection_window_lockout` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Each rising Inspected edge shall add one to WindowCount and, when Rejected is TRUE, one to RejectCount.
- **R2**: Completing WindowSize items shall pulse WindowComplete for one scan and then start a new zeroed window.
- **R3** **[safety-critical]**: If rejects in the completed window exceed RejectLimit, LockedOut shall latch TRUE.
- **R4** **[safety-critical]**: No new items shall be counted while LockedOut.
- **R5**: Reset shall clear counts, WindowComplete, and LockedOut.

## Assumptions

- WindowSize is at least 1 and RejectLimit is non-negative.
- Rejected is sampled only on a rising Inspected edge.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
