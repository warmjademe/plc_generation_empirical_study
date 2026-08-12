# C09_B03_composite: Composed supervisory control: First-out fault recorder with deterministic priority -> Time-qualified sensor disagreement alarm

## Objective

Implement `C09_B03_composite` as an IEC-ST Core v1 function block in the Alarms and fault recovery category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_AnyFault shall equal the disjunction of all three fault inputs.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: The first observed fault shall latch A_LockedOut and its code in A_FirstFault.
- **R3**: Subsystem A shall satisfy: Simultaneous first faults shall use priority A, then B, then C.
- **R4**: Subsystem A shall satisfy: Later faults shall not overwrite A_FirstFault while A_LockedOut is TRUE.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_LockedOut and A_FirstFault only when all fault inputs are FALSE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Disagreeing shall be TRUE exactly when monitoring is enabled and the absolute difference exceeds B_MaxDifference.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A disagreement lasting 300 ms shall latch B_Alarm.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: A shorter disagreement shall not latch B_Alarm.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Alarm only while no disagreement is present.
- **R10** **[safety-critical]**: A TRUE A_AnyFault shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- The runtime scan period is 100 ms.
- MaxDifference is non-negative.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
