# C08_M02_fill_mix_drain: Fill-mix-drain sequence

## Objective

Implement `C08_M02_fill_mix_drain` as an IEC-ST Core v1 function block in the Sequential state machines category. Preserve the supplied interface exactly.

## Requirements

- **R1**: Start in idle shall enter fill and open only FillValve.
- **R2**: HighLevel shall transition fill to mix; MixDone transitions mix to drain.
- **R3**: LowLevel in drain shall return to idle and pulse Complete for one scan.
- **R4** **[safety-critical]**: FillValve, Mixer, and DrainValve shall be mutually exclusive and correspond to State.
- **R5** **[safety-critical]**: Abort shall immediately return to idle, close all actuators, and suppress Complete.

## Assumptions

- The function block is called exactly once per PLC scan.
- Inputs are sampled at scan start and outputs are checked at scan end.
- Each test starts from a fresh function-block instance.

## Output constraint

Return one complete function-block implementation without vendor-specific syntax, physical addresses, Markdown fences, or explanatory prose.
