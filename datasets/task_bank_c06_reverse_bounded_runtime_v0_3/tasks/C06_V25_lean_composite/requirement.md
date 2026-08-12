# C06_V25_lean_composite: Composed supervisory control: Voted permissive with qualified bypass and diagnostics -> Edge-counted batch with consecutive-reject lockout

## Objective

Implement `C06_V25_lean_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: The selected request shall be A_AutoRequest in automatic mode and A_ManualRequest otherwise.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: Without bypass, A_RunPermit requires A_SafetyOK and at least two TRUE channels.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Bypass may latch only in manual mode when A_BypassRequest, A_BypassPermit, A_SafetyOK, and at least one channel are TRUE.
- **R4**: Subsystem A shall satisfy: A_Reset may clear A_BypassActive only when neither automatic nor manual request is active.
- **R5**: Subsystem A shall satisfy: A_Degraded shall identify a permitted run with channel disagreement or active bypass; A_Blocked shall identify a selected request without A_RunPermit.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_ItemPulse while not stopped, B_Complete, or locked shall count one item.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: An accepted item increments B_AcceptedCount and clears B_ConsecutiveRejects; a B_Rejected item increments both reject counters.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Complete shall latch when B_AcceptedCount reaches positive B_Target and no later item may change counts.
- **R9** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Except for a qualified B_Reset scan, B_RejectLimit less than or equal to zero, or reaching B_RejectLimit consecutive rejects, shall latch B_LockedOut.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Stop has priority over B_ItemPulse and prevents every count change.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset clears all state only while B_Stop is TRUE and B_ItemPulse is FALSE.
- **R12** **[safety-critical]**: A TRUE A_RunPermit shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem B: B_Target and B_RejectLimit remain constant during a test.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.
- B_Target remains within the closed interval [-4, 4] during a test.
- B_RejectLimit remains within the closed interval [-4, 4] during a test.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
