# C06_M01_configurable_batch_counter: Configurable batch counter

## Objective

Implement `C06_M01_configurable_batch_counter` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Only a rising Item edge while Enable and below Target shall increment Count.
- **R2** **[safety-critical]**: Count shall remain between zero and Target.
- **R3**: BatchDone shall be TRUE when Count reaches Target.
- **R4**: Reset shall clear Count, BatchDone, and Accepted.

## Assumptions

- Target remains constant during a test and is between 1 and 100.
- Item pulses are separated by at least one low scan.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
