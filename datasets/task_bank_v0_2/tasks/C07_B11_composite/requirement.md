# C07_B11_composite: Composed supervisory control: Clamped analog scaling with range status -> Temperature control with hysteresis

## Objective

Implement `C07_B11_composite` as an IEC-ST Core v1 function block in the Analog processing category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Raw below zero shall set A_UnderRange, clear A_OverRange, and clamp A_Engineering to 0.0.
- **R2**: Subsystem A shall satisfy: A_Raw above 4095 shall set A_OverRange, clear A_UnderRange, and clamp A_Engineering to 10.0.
- **R3**: Subsystem A shall satisfy: In-range A_Raw shall clear both flags and scale linearly to 0.0 through 10.0.
- **R4** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_ConfigError shall be TRUE when B_LowThreshold is not less than B_HighThreshold.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disable or B_ConfigError shall turn B_Heater off.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: While enabled with valid thresholds, B_Temperature below or equal to B_LowThreshold shall turn B_Heater on.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Temperature above or equal to B_HighThreshold shall turn B_Heater off.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Between thresholds, B_Heater shall retain its previous state.
- **R9** **[safety-critical]**: A TRUE A_UnderRange shall latch CrossReady unless CrossReset is TRUE in the same scan.
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
