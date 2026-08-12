# C06_M02_bounded_up_down_counter: Bounded up/down inventory counter

## Objective

Implement `C06_M02_bounded_up_down_counter` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: A lone rising AddItem edge increments Count when below Capacity.
- **R2**: A lone rising RemoveItem edge decrements Count when above zero.
- **R3**: Simultaneous rising edges shall leave Count unchanged and set Conflict for one scan.
- **R4** **[safety-critical]**: Count shall remain within zero and Capacity; Empty and Full reflect the boundaries.
- **R5**: Reset shall clear Count and Conflict.

## Assumptions

- Capacity remains constant during a test and is positive.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
