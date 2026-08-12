# C07_B15_composite: Composed supervisory control: Temperature control with hysteresis -> Clamped analog scaling with range status

## Objective

Implement `C07_B15_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_ConfigError shall be TRUE when A_LowThreshold is not less than A_HighThreshold.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Disable or A_ConfigError shall turn A_Heater off.
- **R3**: Subsystem A shall satisfy: While enabled with valid thresholds, A_Temperature below or equal to A_LowThreshold shall turn A_Heater on.
- **R4**: Subsystem A shall satisfy: A_Temperature above or equal to A_HighThreshold shall turn A_Heater off.
- **R5**: Subsystem A shall satisfy: Between thresholds, A_Heater shall retain its previous state.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Raw below zero shall set B_UnderRange, clear B_OverRange, and clamp B_Engineering to 0.0.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Raw above 4095 shall set B_OverRange, clear B_UnderRange, and clamp B_Engineering to 10.0.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: In-range B_Raw shall clear both flags and scale linearly to 0.0 through 10.0.
- **R9** **[safety-critical]**: A TRUE A_Heater shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
