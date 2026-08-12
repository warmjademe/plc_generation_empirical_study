# C07_H01_redundant_sensor_selection: Redundant analog sensor selection

## Objective

Implement `C07_H01_redundant_sensor_selection` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: When both sensors are valid and agree within MaxDifference, Selected shall be their average.
- **R2** **[safety-critical]**: When both sensors are valid but disagree beyond MaxDifference, Disagree shall be TRUE and Selected shall retain its previous value.
- **R3**: When exactly one sensor is valid, Selected shall use that sensor and Degraded shall be TRUE.
- **R4** **[safety-critical]**: When neither sensor is valid, NoValidSensor shall be TRUE and Selected shall retain its previous value.
- **R5**: Degraded, Disagree, and NoValidSensor shall be mutually exclusive.

## Assumptions

- MaxDifference is non-negative and constant during a test.
- Selected initializes to 0.0 in a fresh instance.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
