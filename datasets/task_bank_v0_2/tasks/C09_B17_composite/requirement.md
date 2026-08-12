# C09_B17_composite: Composed supervisory control: Delayed warning, immediate trip, shelving, acknowledgement, and reset -> First-out fault recorder with deterministic priority

## Objective

Implement `C09_B17_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: An enabled A_WarningCondition shall become A_Warning after 300 ms unless A_Shelved or a A_Trip is active.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Shelve may suppress only warnings; A_TripCondition shall latch A_Trip and A_LockedOut immediately regardless of A_Shelve.
- **R3**: Subsystem A shall satisfy: Every newly displayed A_Warning or A_Trip shall set A_Unacked; A_Acknowledge clears A_Unacked without clearing active alarms.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Shelved follows A_Shelve only while no A_Trip is active; a A_Trip cancels A_Shelved.
- **R5**: Subsystem A shall satisfy: A_Enable FALSE shall suppress A_Warning but shall not clear A_Trip or A_LockedOut.
- **R6** **[safety-critical]**: Subsystem A shall satisfy: A_Reset clears A_Trip and A_LockedOut only when disabled and both conditions are FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_AnyFault shall equal the disjunction of all three fault inputs.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: The first observed fault shall latch B_LockedOut and its code in B_FirstFault.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Simultaneous first faults shall use priority A, then B, then C.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Later faults shall not overwrite B_FirstFault while B_LockedOut is TRUE.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut and B_FirstFault only when all fault inputs are FALSE.
- **R12** **[safety-critical]**: A TRUE A_Warning shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The runtime scan period is 100 ms.
- Acknowledge may be held for more than one scan.
- Each test starts from a fresh function-block instance.
- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
