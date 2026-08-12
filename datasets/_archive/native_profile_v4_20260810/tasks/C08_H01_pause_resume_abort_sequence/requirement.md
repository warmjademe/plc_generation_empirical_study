# C08_H01_pause_resume_abort_sequence: Pause/resume sequence with abort recovery

## Objective

Implement `C08_H01_pause_resume_abort_sequence` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Start shall begin Step 1 only when idle and not Aborted.
- **R2**: Advance shall move Step 1 to Step 2 and Step 2 to done only while not Paused.
- **R3**: Pause shall suppress active step outputs without losing State; Resume clears Paused.
- **R4** **[safety-critical]**: Abort shall return State to idle, suppress outputs, clear Paused, and latch Aborted.
- **R5**: Reset shall clear Aborted only while Start, Advance, Pause, Resume, and Abort are all FALSE.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
