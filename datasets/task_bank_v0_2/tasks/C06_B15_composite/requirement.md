# C06_B15_composite: Composed supervisory control: Bounded up/down inventory counter -> Configurable batch counter

## Objective

Implement `C06_B15_composite` as an IEC-ST Core v1 function block in the Counters and batch logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A lone rising A_AddItem edge increments A_Count when below A_Capacity.
- **R2**: Subsystem A shall satisfy: A lone rising A_RemoveItem edge decrements A_Count when above zero.
- **R3**: Subsystem A shall satisfy: Simultaneous rising edges shall leave A_Count unchanged and set A_Conflict for one scan.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Count shall remain within zero and A_Capacity; A_Empty and A_Full reflect the boundaries.
- **R5**: Subsystem A shall satisfy: A_Reset shall clear A_Count and A_Conflict.
- **R6**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Only a rising B_Item edge while B_Enable and below B_Target shall increment B_Count.
- **R7** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Count shall remain between zero and B_Target.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_BatchDone shall be TRUE when B_Count reaches B_Target.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_Count, B_BatchDone, and B_Accepted.
- **R10** **[safety-critical]**: A TRUE A_Empty shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R11** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R12**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R13** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Capacity remains constant during a test and is positive.
- Each test starts from a fresh function-block instance.
- Target remains constant during a test and is between 1 and 100.
- Item pulses are separated by at least one low scan.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
