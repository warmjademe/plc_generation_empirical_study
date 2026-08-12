# C06_R09_lean_composite: Composed supervisory control: Inspection-window reject lockout -> Mode-dependent command selection

## Objective

Implement `C06_R09_lean_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: Each rising A_Inspected edge shall add one to A_WindowCount and, when A_Rejected is TRUE, one to A_RejectCount.
- **R2**: Subsystem A shall satisfy: Completing A_WindowSize items shall pulse A_WindowComplete for one scan and then start a new zeroed window.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: If rejects in the completed window exceed A_RejectLimit, A_LockedOut shall latch TRUE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: No new items shall be counted while A_LockedOut.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear counts, A_WindowComplete, and A_LockedOut.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Command shall follow B_AutoDemand in automatic mode and B_ManualDemand in manual mode, but only when B_SafetyOK is TRUE and B_Inhibit is FALSE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Blocked shall be TRUE when the selected request is TRUE but safety is not OK or B_Inhibit is TRUE.
- **R8** **[safety-critical]**: A TRUE A_LockedOut shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R9** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R10**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R11** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_WindowSize is at least 1 and A_RejectLimit is non-negative.
- Subsystem A: A_Rejected is sampled only on a rising A_Inspected edge.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- A_WindowSize remains within the closed interval [-4, 4] during a test.
- A_RejectLimit remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
