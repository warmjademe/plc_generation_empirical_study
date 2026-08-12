# C10_M01_alternating_pump_starts: Alternating two-pump starts

## Objective

Implement `C10_M01_alternating_pump_starts` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Each rising Demand shall start at most one available pump.
- **R2**: When both pumps are available, successive demand episodes shall alternate the selected pump.
- **R3**: If the preferred pump is unavailable, the other available pump shall run.
- **R4**: Unavailable shall be TRUE exactly when Demand is TRUE and neither pump is available.
- **R5**: Reset without Demand shall set NextPump to 1 and stop both pumps.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
