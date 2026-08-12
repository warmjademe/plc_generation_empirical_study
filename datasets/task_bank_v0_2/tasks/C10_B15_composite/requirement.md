# C10_B15_composite: Composed supervisory control: Lead-lag pump demand control -> Alternating two-pump starts

## Objective

Implement `C10_B15_composite` as an IEC-ST Core v1 function block in the Multi-device coordination category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Subsystem A shall satisfy: With A_LowDemand only, the available selected lead pump shall run and the lag pump shall remain off.
- **R2**: Subsystem A shall satisfy: With A_HighDemand, every available pump shall run.
- **R3**: Subsystem A shall satisfy: If the selected lead is unavailable under A_LowDemand, the available lag pump shall run.
- **R4**: Subsystem A shall satisfy: No pump shall run when neither demand input is TRUE.
- **R5**: Subsystem A shall satisfy: A_CapacityShortfall shall indicate zero available pumps for A_LowDemand or fewer than two for A_HighDemand.
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

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.
- Subsystem A executes before the supervisory latch and subsystem B within each scan.
- Requirements inherited from subsystem B apply only while SubsystemBEnable and CrossReady are TRUE.
- When subsystem B is isolated, its externally visible outputs take their type-safe defaults.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
