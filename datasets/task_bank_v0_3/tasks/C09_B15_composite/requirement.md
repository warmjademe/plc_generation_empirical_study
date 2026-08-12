# C09_B15_composite: Composed supervisory control: Time-qualified sensor disagreement alarm -> High and high-high alarm priority

## Objective

Implement `C09_B15_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds A_MaxDifference.
- **R2**: Subsystem A shall satisfy: A disagreement lasting 300 ms shall latch A_Alarm.
- **R3**: Subsystem A shall satisfy: A shorter disagreement shall not latch A_Alarm.
- **R4**: Subsystem A shall satisfy: A_Reset shall clear A_Alarm only while no disagreement is present.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Value at or above B_HighLimit shall latch B_HighAlarm.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Value at or above B_HighHighLimit shall latch both alarms and B_Shutdown.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A high alarm below B_HighHighLimit shall not by itself assert B_Shutdown.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear all latched outputs only below B_HighLimit.
- **R9** **[safety-critical]**: A TRUE A_Alarm shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R10** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R11**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R12** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_MaxDifference is non-negative.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_HighHighLimit is greater than B_HighLimit.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
