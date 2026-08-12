# C06_B02_composite: Composed supervisory control: Good/reject batch statistics with reject lockout -> Configurable batch counter

## Objective

Implement `C06_B02_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A good-part rising edge increments only A_GoodCount; a reject-part rising edge increments only A_RejectCount.
- **R2**: Subsystem A shall satisfy: Simultaneous good and reject edges shall count one reject and no good part.
- **R3**: Subsystem A shall satisfy: A_BatchDone shall be TRUE when A_GoodCount plus A_RejectCount reaches A_BatchTarget.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_QualityFault shall latch when A_RejectCount reaches A_RejectLimit and remain set until A_Reset.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear both counts, A_BatchDone, and A_QualityFault.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_Item edge while B_Enable and below B_Target shall increment B_Count.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall remain between zero and B_Target.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_BatchDone shall be TRUE when B_Count reaches B_Target.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Count, B_BatchDone, and B_Accepted.
- **R10** **[safety-critical]**: A TRUE A_BatchDone shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: A_BatchTarget and A_RejectLimit remain positive and constant during a test.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: B_Target remains constant during a test and is between 1 and 100.
- Subsystem B: B_Item pulses are separated by at least one low scan.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
