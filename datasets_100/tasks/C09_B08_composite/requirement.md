# C09_B08_composite: Composed supervisory control: Delayed warning with trip lockout and acknowledgement -> Delayed warning, immediate trip, shelving, acknowledgement, and reset

## Objective

Implement `C09_B08_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_WarningCondition shall assert A_Warning only after it remains enabled for 300 ms.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_TripCondition while enabled shall immediately latch A_Trip and A_LockedOut.
- **R3**: Subsystem A shall satisfy: A newly asserted A_Warning or A_Trip shall set A_Unacked.
- **R4**: Subsystem A shall satisfy: A_Acknowledge shall clear A_Unacked without clearing active A_Warning or latched A_Trip.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_Trip and A_LockedOut only while both conditions and A_Enable are FALSE.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: Disabling the system shall clear the non-latched A_Warning but not an existing A_Trip.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: An enabled B_WarningCondition shall become B_Warning after 300 ms unless B_Shelved or a B_Trip is active.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Shelve may suppress only warnings; B_TripCondition shall latch B_Trip and B_LockedOut immediately regardless of B_Shelve.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Every newly displayed B_Warning or B_Trip shall set B_Unacked; B_Acknowledge clears B_Unacked without clearing active alarms.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Shelved follows B_Shelve only while no B_Trip is active; a B_Trip cancels B_Shelved.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Enable FALSE shall suppress B_Warning but shall not clear B_Trip or B_LockedOut.
- **R12** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Trip and B_LockedOut only when disabled and both conditions are FALSE.
- **R13** **[safety-critical]**: A TRUE A_Warning shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R14** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R15**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R16** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: A_Acknowledge has priority over a new A_Unacked indication within the same scan.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The runtime scan period is 100 ms.
- Subsystem B: B_Acknowledge may be held for more than one scan.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
