# C09_B18_composite: Composed supervisory control: Delayed warning, immediate trip, shelving, acknowledgement, and reset -> Delayed warning with trip lockout and acknowledgement

## Objective

Implement `C09_B18_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: An enabled A_WarningCondition shall become A_Warning after 300 ms unless A_Shelved or a A_Trip is active.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Shelve may suppress only warnings; A_TripCondition shall latch A_Trip and A_LockedOut immediately regardless of A_Shelve.
- **R3**: Subsystem A shall satisfy: Every newly displayed A_Warning or A_Trip shall set A_Unacked; A_Acknowledge clears A_Unacked without clearing active alarms.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Shelved follows A_Shelve only while no A_Trip is active; a A_Trip cancels A_Shelved.
- **R5**: Subsystem A shall satisfy: A_Enable FALSE shall suppress A_Warning but shall not clear A_Trip or A_LockedOut.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: A_Reset clears A_Trip and A_LockedOut only when disabled and both conditions are FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_WarningCondition shall assert B_Warning only after it remains enabled for 300 ms.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_TripCondition while enabled shall immediately latch B_Trip and B_LockedOut.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A newly asserted B_Warning or B_Trip shall set B_Unacked.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Acknowledge shall clear B_Unacked without clearing active B_Warning or latched B_Trip.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Trip and B_LockedOut only while both conditions and B_Enable are FALSE.
- **R12** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Disabling the system shall clear the non-latched B_Warning but not an existing B_Trip.
- **R13** **[safety-critical]**: A TRUE A_Warning shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R14** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R15**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R16** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Acknowledge may be held for more than one scan.
- Each test starts from a fresh function-block instance.
- Acknowledge has priority over a new Unacked indication within the same scan.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
