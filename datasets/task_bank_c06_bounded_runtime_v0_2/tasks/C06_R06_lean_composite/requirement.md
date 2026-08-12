# C06_R06_lean_composite: Composed supervisory control: Inspection-window reject lockout -> Four-level alarm priority encoder

## Objective

Implement `C06_R06_lean_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: Each rising A_Inspected edge shall add one to A_WindowCount and, when A_Rejected is TRUE, one to A_RejectCount.
- **R2**: Subsystem A shall satisfy: Completing A_WindowSize items shall pulse A_WindowComplete for one scan and then start a new zeroed window.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: If rejects in the completed window exceed A_RejectLimit, A_LockedOut shall latch TRUE.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: No new items shall be counted while A_LockedOut.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear counts, A_WindowComplete, and A_LockedOut.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Emergency shall always produce B_Level 4 and B_Active TRUE, even when B_Suppress is TRUE.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When not suppressed, the highest B_Active condition shall determine B_Level.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Suppress shall force B_Level 0 and B_Active FALSE when B_Emergency is FALSE.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Level 0 shall be equivalent to B_Active FALSE.
- **R10** **[safety-critical]**: A TRUE A_LockedOut shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

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
