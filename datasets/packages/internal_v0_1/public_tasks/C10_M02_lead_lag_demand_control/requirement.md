# C10_M02_lead_lag_demand_control: Lead-lag pump demand control

## Objective

Implement `C10_M02_lead_lag_demand_control` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: With LowDemand only, the available selected lead pump shall run and the lag pump shall remain off.
- **R2**: With HighDemand, every available pump shall run.
- **R3**: If the selected lead is unavailable under LowDemand, the available lag pump shall run.
- **R4**: No pump shall run when neither demand input is TRUE.
- **R5**: CapacityShortfall shall indicate zero available pumps for LowDemand or fewer than two for HighDemand.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
