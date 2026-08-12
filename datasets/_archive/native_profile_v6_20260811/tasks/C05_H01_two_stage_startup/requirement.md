# C05_H01_two_stage_startup: Two-stage timed startup with safe abort

## Objective

Implement `C05_H01_two_stage_startup` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Start with Permit shall command Stage1 immediately.
- **R2** **[safety-critical]**: Stage2 shall not start until Stage1Feedback has remained TRUE for at least 300 ms.
- **R3** **[safety-critical]**: If Stage1Feedback is absent for 600 ms after Stage1 starts, Fault shall latch and both stages shall stop.
- **R4** **[safety-critical]**: Stop or loss of Permit shall turn both stages off immediately.
- **R5**: Fault remains latched until Stop is TRUE while Start is FALSE.

## Assumptions

- The runtime scan period is 100 ms.
- Permit changes are sampled at scan start.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
