# C08_X01_paused_three_stage_timeout: Paused three-stage sequence with abort and per-stage timeout

## Objective

Implement `C08_X01_paused_three_stage_timeout` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Start in idle shall enter stage 1; each matching Done input advances exactly one stage, and Stage3Done returns idle with a one-scan Complete pulse.
- **R2** **[safety-critical]**: Pause shall retain State while forcing every actuator FALSE; Done inputs while paused shall not advance.
- **R3** **[safety-critical]**: The active stage shall time out after 500 ms of unpaused execution and latch Fault.
- **R4** **[safety-critical]**: Abort shall immediately return idle, force safe outputs, and latch Fault.
- **R5**: Reset clears Fault only in idle while Start, Abort, and every Done input are FALSE.
- **R6** **[safety-critical]**: At most one actuator may be TRUE, and Complete shall never coincide with an actuator.

## Assumptions

- The runtime scan period is 100 ms.
- Pausing resets rather than accumulates the stage timeout.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
