# C05_E01_on_delay_enable: On-delay enable

## Objective

Implement `C05_E01_on_delay_enable` as an IEC-ST Core v1 function block in the Timers and timeouts category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Delayed shall remain FALSE until Enable has remained TRUE continuously for 300 ms.
- **R2** **[safety-critical]**: Reset or Enable FALSE shall make Delayed FALSE without an additional delay.

## Assumptions

- The runtime scan period is 100 ms.
- Timer tests check exact boundaries with a declared one-scan infrastructure tolerance and stable states without tolerance.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
