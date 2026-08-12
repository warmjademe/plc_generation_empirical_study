# C07_M02_temperature_hysteresis: Temperature control with hysteresis

## Objective

Implement `C07_M02_temperature_hysteresis` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: ConfigError shall be TRUE when LowThreshold is not less than HighThreshold.
- **R2** **[safety-critical]**: Disable or ConfigError shall turn Heater off.
- **R3**: While enabled with valid thresholds, Temperature below or equal to LowThreshold shall turn Heater on.
- **R4**: Temperature above or equal to HighThreshold shall turn Heater off.
- **R5**: Between thresholds, Heater shall retain its previous state.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
