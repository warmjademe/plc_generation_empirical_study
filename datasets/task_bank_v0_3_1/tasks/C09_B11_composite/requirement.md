# C09_B11_composite: Composed supervisory control: High and high-high alarm priority -> Time-qualified sensor disagreement alarm

## Objective

Implement `C09_B11_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Value at or above A_HighLimit shall latch A_HighAlarm.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Value at or above A_HighHighLimit shall latch both alarms and A_Shutdown.
- **R3**: Subsystem A shall satisfy: A high alarm below A_HighHighLimit shall not by itself assert A_Shutdown.
- **R4**: Subsystem A shall satisfy: A_Reset shall clear all latched outputs only below A_HighLimit.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds B_MaxDifference.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A disagreement lasting 300 ms shall latch B_Alarm.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A shorter disagreement shall not latch B_Alarm.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Alarm only while no disagreement is present.
- **R9** **[safety-critical]**: A TRUE A_HighAlarm shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_HighHighLimit is greater than A_HighLimit.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_MaxDifference is non-negative.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
