# C06_V02_lean_composite: Composed supervisory control: Four-level alarm priority encoder -> Inspection-window reject lockout

## Objective

Implement `C06_V02_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: A_Emergency shall always produce A_Level 4 and A_Active TRUE, even when A_Suppress is TRUE.
- **R2**: Subsystem A shall satisfy: When not suppressed, the highest A_Active condition shall determine A_Level.
- **R3**: Subsystem A shall satisfy: A_Suppress shall force A_Level 0 and A_Active FALSE when A_Emergency is FALSE.
- **R4**: Subsystem A shall satisfy: A_Level 0 shall be equivalent to A_Active FALSE.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each rising B_Inspected edge shall add one to B_WindowCount and, when B_Rejected is TRUE, one to B_RejectCount.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Completing B_WindowSize items shall pulse B_WindowComplete for one scan and then start a new zeroed window.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If rejects in the completed window exceed B_RejectLimit, B_LockedOut shall latch TRUE.
- **R8** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: No new items shall be counted while B_LockedOut.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear counts, B_WindowComplete, and B_LockedOut.
- **R10** **[safety-critical]**: A TRUE A_Active shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_WindowSize is at least 1 and B_RejectLimit is non-negative.
- Subsystem B: B_Rejected is sampled only on a rising B_Inspected edge.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- B_WindowSize remains within the closed interval [-4, 4] during a test.
- B_RejectLimit remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
