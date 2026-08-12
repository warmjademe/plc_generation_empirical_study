# C06_E01_three_part_counter: Three-part completion counter

## Objective

Implement `C06_E01_three_part_counter` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Each rising PartPulse shall increment Count once until Count reaches three.
- **R2** **[safety-critical]**: Count shall saturate at three.
- **R3**: Complete shall be TRUE exactly when Count equals three.
- **R4**: Reset shall clear Count and Complete.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
