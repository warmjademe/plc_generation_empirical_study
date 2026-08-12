# C09_B16_composite: Composed supervisory control: Time-qualified sensor disagreement alarm -> Delayed warning, immediate trip, shelving, acknowledgement, and reset

## Objective

Implement `C09_B16_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds A_MaxDifference.
- **R2**: Subsystem A shall satisfy: A disagreement lasting 300 ms shall latch A_Alarm.
- **R3**: Subsystem A shall satisfy: A shorter disagreement shall not latch A_Alarm.
- **R4**: Subsystem A shall satisfy: A_Reset shall clear A_Alarm only while no disagreement is present.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: An enabled B_WarningCondition shall become B_Warning after 300 ms unless B_Shelved or a B_Trip is active.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Shelve may suppress only warnings; B_TripCondition shall latch B_Trip and B_LockedOut immediately regardless of B_Shelve.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Every newly displayed B_Warning or B_Trip shall set B_Unacked; B_Acknowledge clears B_Unacked without clearing active alarms.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Shelved follows B_Shelve only while no B_Trip is active; a B_Trip cancels B_Shelved.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Enable FALSE shall suppress B_Warning but shall not clear B_Trip or B_LockedOut.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Trip and B_LockedOut only when disabled and both conditions are FALSE.
- **R11** **[safety-critical]**: A TRUE A_Alarm shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_MaxDifference is non-negative.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Acknowledge may be held for more than one scan.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
