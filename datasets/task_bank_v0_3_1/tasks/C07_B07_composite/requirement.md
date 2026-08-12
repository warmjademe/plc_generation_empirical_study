# C07_B07_composite: Composed supervisory control: Rate-of-change monitoring with latched trip -> Temperature control with hysteresis

## Objective

Implement `C07_B07_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: The first enabled sample shall initialize history, set A_Ready, and shall not A_Trip.
- **R2**: Subsystem A shall satisfy: For subsequent enabled samples, A_Delta shall equal A_Value minus the A_Previous enabled A_Value.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: A A_Delta above A_MaxRise or below negative A_MaxFall shall latch A_Trip.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Trip shall remain set until A_Reset occurs while A_Enable is FALSE.
- **R5**: Subsystem A shall satisfy: Disabling monitoring shall clear A_Ready but shall not by itself clear A_Trip.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ConfigError shall be TRUE when B_LowThreshold is not less than B_HighThreshold.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disable or B_ConfigError shall turn B_Heater off.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: While enabled with valid thresholds, B_Temperature below or equal to B_LowThreshold shall turn B_Heater on.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Temperature above or equal to B_HighThreshold shall turn B_Heater off.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Between thresholds, B_Heater shall retain its previous state.
- **R11** **[safety-critical]**: A TRUE A_Trip shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem A: A_MaxRise and A_MaxFall are non-negative and remain constant during a test.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
