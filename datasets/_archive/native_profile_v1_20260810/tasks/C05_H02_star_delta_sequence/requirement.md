# C05_H02_star_delta_sequence: Star-delta motor transition

## Objective

Implement `C05_H02_star_delta_sequence` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Start shall energize Main and Star when no fault, Stop, or Overload is active.
- **R2** **[safety-critical]**: After 500 ms in Star, Star shall turn off before Delta turns on after a 200 ms transition gap.
- **R3** **[safety-critical]**: Star and Delta shall never be TRUE together.
- **R4** **[safety-critical]**: Stop or Overload shall immediately turn off all contactors; Overload latches Fault.
- **R5**: Reset clears Fault only while Start is FALSE and Overload is FALSE.

## Assumptions

- The runtime scan period is 100 ms.
- Start may remain TRUE during normal operation.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
