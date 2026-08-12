# C04_H02_dual_event_priority_lockout: Dual-event priority capture with lockout

## Objective

Implement `C04_H02_dual_event_priority_lockout` as an IEC-ST Core v1 function block in the Edge and event handling category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Reset shall clear Captured, Code, and Pulse.
- **R2**: While armed and not captured, a rising EventA shall capture Code 1.
- **R3**: A simultaneous rising edge shall select EventA over EventB.
- **R4**: A rising EventB without EventA shall capture Code 2.
- **R5** **[safety-critical]**: After capture, later events shall not change Code until Reset.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
