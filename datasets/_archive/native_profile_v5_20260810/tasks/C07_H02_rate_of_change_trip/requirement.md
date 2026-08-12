# C07_H02_rate_of_change_trip: Rate-of-change monitoring with latched trip

## Objective

Implement `C07_H02_rate_of_change_trip` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: The first enabled sample shall initialize history, set Ready, and shall not trip.
- **R2**: For subsequent enabled samples, Delta shall equal Value minus the previous enabled Value.
- **R3** **[safety-critical]**: A Delta above MaxRise or below negative MaxFall shall latch Trip.
- **R4** **[safety-critical]**: Trip shall remain set until Reset occurs while Enable is FALSE.
- **R5**: Disabling monitoring shall clear Ready but shall not by itself clear Trip.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- MaxRise and MaxFall are non-negative and remain constant during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
