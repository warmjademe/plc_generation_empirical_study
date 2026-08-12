# C06_H01_quality_batch_statistics: Good/reject batch statistics with reject lockout

## Objective

Implement `C06_H01_quality_batch_statistics` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: A good-part rising edge increments only GoodCount; a reject-part rising edge increments only RejectCount.
- **R2**: Simultaneous good and reject edges shall count one reject and no good part.
- **R3**: BatchDone shall be TRUE when GoodCount plus RejectCount reaches BatchTarget.
- **R4** **[safety-critical]**: QualityFault shall latch when RejectCount reaches RejectLimit and remain set until Reset.
- **R5**: Reset shall clear both counts, BatchDone, and QualityFault.

## Assumptions

- BatchTarget and RejectLimit remain positive and constant during a test.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
