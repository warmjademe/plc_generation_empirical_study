# C10_B10_composite: Composed supervisory control: Alternating two-pump starts -> Fair two-client resource arbiter with emergency lockout

## Objective

Implement `C10_B10_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1** **[safety-critical]**: Subsystem A shall satisfy: Each rising A_Demand shall start at most one available pump.
- **R2**: Subsystem A shall satisfy: When both pumps are available, successive A_Demand episodes shall alternate the selected pump.
- **R3**: Subsystem A shall satisfy: If the preferred pump is A_Unavailable, the other available pump shall run.
- **R4**: Subsystem A shall satisfy: A_Unavailable shall be TRUE exactly when A_Demand is TRUE and neither pump is available.
- **R5**: Subsystem A shall satisfy: A_Reset without A_Demand shall set A_NextPump to 1 and stop both pumps.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_GrantA and B_GrantB shall never be TRUE simultaneously.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When idle, a single request shall receive the resource; simultaneous requests shall follow B_Turn.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Done shall release the current grant before a new owner is selected on a later scan.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: After A completes B_Turn shall prefer B, and after B completes B_Turn shall prefer A.
- **R10** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Emergency shall immediately revoke all grants and latch B_LockedOut.
- **R11**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset shall clear B_LockedOut only while B_Emergency and both requests are FALSE.
- **R12** **[safety-critical]**: A TRUE A_Pump1Run shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R13** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R14**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R15** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
