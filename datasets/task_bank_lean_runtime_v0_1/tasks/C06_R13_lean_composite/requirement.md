# C06_R13_lean_composite: Composed supervisory control: Configurable batch counter -> Two-out-of-three sensor voter

## Objective

Implement `C06_R13_lean_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: Only a rising A_Item edge while A_Enable and below A_Target shall increment A_Count.
- **R2** **[safety-critical]**: Subsystem A shall satisfy: A_Count shall remain between zero and A_Target.
- **R3**: Subsystem A shall satisfy: A_BatchDone shall be TRUE when A_Count reaches A_Target.
- **R4**: Subsystem A shall satisfy: A_Reset shall clear A_Count, A_BatchDone, and A_Accepted.
- **R5**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Vote shall be TRUE when at least two of B_S1, B_S2, and B_S3 are TRUE.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Unanimous shall be TRUE only when all three channels have the same value.
- **R7** **[safety-critical]**: A TRUE A_BatchDone shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R8** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R9**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R10** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_Target remains constant during a test and is between 1 and 100.
- Subsystem A: A_Item pulses are separated by at least one low scan.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
