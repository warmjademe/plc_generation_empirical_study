# C09_B20_composite: Composed supervisory control: Delayed warning, immediate trip, shelving, acknowledgement, and reset -> Time-qualified sensor disagreement alarm

## Objective

Implement `C09_B20_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: An enabled A_WarningCondition shall become A_Warning after 300 ms unless A_Shelved or a A_Trip is active.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Shelve may suppress only warnings; A_TripCondition shall latch A_Trip and A_LockedOut immediately regardless of A_Shelve.
- **R3**: Subsystem A shall satisfy: Every newly displayed A_Warning or A_Trip shall set A_Unacked; A_Acknowledge clears A_Unacked without clearing active alarms.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Shelved follows A_Shelve only while no A_Trip is active; a A_Trip cancels A_Shelved.
- **R5**: Subsystem A shall satisfy: A_Enable FALSE shall suppress A_Warning but shall not clear A_Trip or A_LockedOut.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: A_Reset clears A_Trip and A_LockedOut only when disabled and both conditions are FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds B_MaxDifference.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A disagreement lasting 300 ms shall latch B_Alarm.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A shorter disagreement shall not latch B_Alarm.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Alarm only while no disagreement is present.
- **R11** **[safety-critical]**: A TRUE A_Warning shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_Acknowledge may be held for more than one scan.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_MaxDifference is non-negative.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
