# C10_B02_composite: Composed supervisory control: Duty-standby pump feedback failover -> Alternating two-pump starts

## Objective

Implement `C10_B02_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: A new A_Demand shall command the available duty pump, or the standby if the duty pump is unavailable.
- **R2**: Subsystem A shall satisfy: If the commanded pump lacks feedback for 300 ms, control shall transfer to an available standby pump.
- **R3** **[safety-critical]**: Subsystem A shall satisfy: Both run commands shall never be TRUE simultaneously.
- **R4** **[safety-critical]**: Subsystem A shall satisfy: A_Failure shall latch if A_Demand cannot be served by an available pump with feedback after failover.
- **R5**: Subsystem A shall satisfy: A_Demand FALSE shall stop both pumps; A_Reset may clear A_Failure only with A_Demand FALSE.
- **R6** **[safety-critical]**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: Each rising B_Demand shall start at most one available pump.
- **R7**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: When both pumps are available, successive B_Demand episodes shall alternate the selected pump.
- **R8**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: If the preferred pump is B_Unavailable, the other available pump shall run.
- **R9**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Unavailable shall be TRUE exactly when B_Demand is TRUE and neither pump is available.
- **R10**: While SubsystemBEnable and CrossReady are TRUE, subsystem B shall satisfy: B_Reset without B_Demand shall set B_NextPump to 1 and stop both pumps.
- **R11** **[safety-critical]**: A TRUE A_Pump1Run shall latch CrossReady unless CrossReset is TRUE in the same scan.
- **R12** **[safety-critical]**: CrossReset shall have priority, clear CrossReady, and isolate every subsystem-B output to its type-safe default.
- **R13**: Once set, CrossReady shall remain TRUE after the subsystem-A signal falls, until a later CrossReset scan.
- **R14** **[safety-critical]**: Subsystem B may execute only while SubsystemBEnable and CrossReady are TRUE; CrossBlocked is TRUE exactly when SubsystemBEnable is requested without CrossReady.

## Assumptions

- Subsystem A: The runtime scan period is 100 ms.
- Subsystem A: Pump feedback is sampled at scan start.
- Subsystem A: Each test starts from a fresh function-block instance.
- Subsystem B: The function block is called exactly once per PLC scan.
- Subsystem B: Inputs are sampled at scan start and outputs are checked at scan end.
- Subsystem B: Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
