# C01_B11_composite: Composed supervisory control: Two-out-of-three sensor voter -> Mode-dependent command selection

## Objective

Implement `C01_B11_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Vote shall be TRUE when at least two of A_S1, A_S2, and A_S3 are TRUE.
- **R2**: Subsystem A shall satisfy: A_Unanimous shall be TRUE only when all three channels have the same value.
- **R3** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Command shall follow B_AutoDemand in automatic mode and B_ManualDemand in manual mode, but only when B_SafetyOK is TRUE and B_Inhibit is FALSE.
- **R4**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Blocked shall be TRUE when the selected request is TRUE but safety is not OK or B_Inhibit is TRUE.
- **R5** **[safety-critical]**: A TRUE A_Vote shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R6** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R7**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R8** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The function block is called exactly once per PLC scan.
- Subsystem A: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
