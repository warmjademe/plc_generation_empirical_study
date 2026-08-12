# C07_B03_composite: Composed supervisory control: Redundant analog sensor selection -> Temperature control with hysteresis

## Objective

Implement `C07_B03_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: When both sensors are valid and agree within A_MaxDifference, A_Selected shall be their average.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: When both sensors are valid but A_Disagree beyond A_MaxDifference, A_Disagree shall be TRUE and A_Selected shall retain its previous value.
- **R3**: Subsystem A shall satisfy: When exactly one sensor is valid, A_Selected shall use that sensor and A_Degraded shall be TRUE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: When neither sensor is valid, A_NoValidSensor shall be TRUE and A_Selected shall retain its previous value.
- **R5**: Subsystem A shall satisfy: A_Degraded, A_Disagree, and A_NoValidSensor shall be mutually exclusive.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ConfigError shall be TRUE when B_LowThreshold is not less than B_HighThreshold.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disable or B_ConfigError shall turn B_Heater off.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: While enabled with valid thresholds, B_Temperature below or equal to B_LowThreshold shall turn B_Heater on.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Temperature above or equal to B_HighThreshold shall turn B_Heater off.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Between thresholds, B_Heater shall retain its previous state.
- **R11** **[safety-critical]**: A TRUE A_Degraded shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- MaxDifference is non-negative and constant during a test.
- Selected initializes to 0.0 in a fresh instance.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
