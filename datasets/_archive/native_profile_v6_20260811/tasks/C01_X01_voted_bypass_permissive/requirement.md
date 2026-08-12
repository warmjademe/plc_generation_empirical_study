# C01_X01_voted_bypass_permissive: Voted permissive with qualified bypass and diagnostics

## Objective

Implement `C01_X01_voted_bypass_permissive` as an IEC-ST Core v1 function block in the Boolean and conditional logic category. Preserve the supplied interface exactly.

## Requirements

- **R1**: The selected request shall be AutoRequest in automatic mode and ManualRequest otherwise.
- **R2** **[safety-critical]**: Without bypass, RunPermit requires SafetyOK and at least two TRUE channels.
- **R3** **[safety-critical]**: Bypass may latch only in manual mode when BypassRequest, BypassPermit, SafetyOK, and at least one channel are TRUE.
- **R4**: Reset may clear BypassActive only when neither automatic nor manual request is active.
- **R5**: Degraded shall identify a permitted run with channel disagreement or active bypass; Blocked shall identify a selected request without RunPermit.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
