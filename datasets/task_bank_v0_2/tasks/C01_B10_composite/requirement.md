# C01_B10_composite: Composed supervisory control: Two-out-of-three sensor voter -> Redundant-channel safety gate

## Objective

Implement `C01_B10_composite` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A_Vote shall be TRUE when at least two of A_S1, A_S2, and A_S3 are TRUE.
- **R2**: Subsystem A shall satisfy: A_Unanimous shall be TRUE only when all three channels have the same value.
- **R3** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Disagree shall be TRUE exactly when B_ChA and B_ChB differ.
- **R4** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Normal B_SafeEnable requires B_ProcessRequest and both channels TRUE.
- **R5** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Test mode may bypass B_ChB only when B_TestPermit and B_ChA are TRUE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_TestActive shall indicate B_TestMode and B_TestPermit together.
- **R7** **[safety-critical]**: A TRUE A_Vote shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R8** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R9**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R10** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
