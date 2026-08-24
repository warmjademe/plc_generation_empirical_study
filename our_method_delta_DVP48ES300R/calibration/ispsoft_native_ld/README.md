# ISPSoft native LD exporter calibration

This directory records the controlled calibration of the deterministic
`Ladder IR -> ISPSoft [FB,LD]` exporter.  The observations were made with
ISPSoft 3.24 in a DVP48ES300R/DVP-ES3 project on 2026-08-22.  Each sample was
drawn in ISPSoft, exported by ISPSoft, decrypted only in the private validation
environment, and compared at the `Unzipped.src` level.  No package password or
vendor credential is stored here.

## Confirmed source-unit fields

- Program LD: `ContentType=0`, `[PRG,LD]`, `P_type=0`, `P_Lang=1`.
- Function-block LD: `ContentType=1`, `[FB,LD]`, `P_type=1`, `P_Lang=1`.
- Native LD networks contain `ROOTLINK` and `OUTLINK`; they do not contain an
  `IL_ST_CODE` section.

## Confirmed node mapping

| Construct | ISPSoft node |
| --- | --- |
| Normally-open contact | `TYPE=1`, `DEV_NAME=<symbol>` |
| Normally-closed contact | `TYPE=2`, `DEV_NAME=<symbol>` |
| Empty cell used to align unequal parallel branches | `TYPE=5` |
| Parallel group | `TYPE=6`, `LNK_C=<branch count>`, `LNK_L=<maximum branch width>` |
| Normal coil | `TYPE=13`, `DEV_NAME=<symbol>` |
| Set coil | `TYPE=15`, `DEV_NAME=<symbol>` |
| Reset coil | `TYPE=16`, `DEV_NAME=<symbol>` |

`LD_TOPOLOGY` encodes `(X0 AND X1) OR (NOT X2)`: the two branches are padded
to width two, followed by `TYPE=6`, `LNK_C=2`, and `LNK_L=2`.  `LD_OR2`
encodes `X0 OR (NOT X2)` and has no padding node, followed by `LNK_C=2` and
`LNK_L=1`.  These two observations establish the branch dimensions used by
the exporter rather than merely testing one diagram.

## Fail-closed boundary

The calibrated native subset currently contains Boolean contacts combined by
AND/OR, NOT applied directly to a Boolean variable, and normal/set/reset
coils.  Rungs with multiple coils are emitted as separate equivalent networks.
Comparisons, arithmetic, move instructions, counters, timers, edge contacts,
and vendor function blocks are rejected by the native exporter until a
controlled official sample and an ISPSoft compile/runtime calibration exist.
The same Ladder IR can still be lowered to ST for MatIEC, PLCverif, and OpenPLC;
that portable path is not mislabelled as native LD.

## Acceptance checks

The generated `FB_GEN_TEST.FBU` was produced by this exporter, imported back
into ISPSoft, opened in the native ladder editor with its four local symbols
and three networks intact, and included in a project compile reporting zero
errors and zero warnings.  Runtime calibration is performed by importing the
native-LD FBU together with the independently generated ST test harness and
driving the resulting image through COMMGR; this path is separate from the ST
portability gates.

The positive runtime control passed ISPSoft compilation (0 errors, 0 warnings)
and all four COMMGR observations covering normal output, set, retained state,
and reset.  A negative control replaced the first contact with the undeclared
symbol `MissingContact`; ISPSoft rejected it with error 240 before COMMGR ran.
The two compact machine-readable records are stored beside this document.
