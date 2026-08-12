# C09_B04_composite: Composed supervisory control: First-out fault recorder with deterministic priority -> Delayed warning, immediate trip, shelving, acknowledgement, and reset

## Objective

Implement `C09_B04_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_AnyFault shall equal the disjunction of all three fault inputs.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: The first observed fault shall latch A_LockedOut and its code in A_FirstFault.
- **R3**: Subsystem A shall satisfy: Simultaneous first faults shall use priority A, then B, then C.
- **R4**: Subsystem A shall satisfy: Later faults shall not overwrite A_FirstFault while A_LockedOut is TRUE.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_LockedOut and A_FirstFault only when all fault inputs are FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: An enabled B_WarningCondition shall become B_Warning after 300 ms unless B_Shelved or a B_Trip is active.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Shelve may suppress only warnings; B_TripCondition shall latch B_Trip and B_LockedOut immediately regardless of B_Shelve.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Every newly displayed B_Warning or B_Trip shall set B_Unacked; B_Acknowledge clears B_Unacked without clearing active alarms.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Shelved follows B_Shelve only while no B_Trip is active; a B_Trip cancels B_Shelved.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Enable FALSE shall suppress B_Warning but shall not clear B_Trip or B_LockedOut.
- **R11** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears B_Trip and B_LockedOut only when disabled and both conditions are FALSE.
- **R12** **[safety-critical]**: A TRUE A_AnyFault shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- The runtime scan period is 100 ms.
- Acknowledge may be held for more than one scan.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
