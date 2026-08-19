# DVP-ES3 timer-type availability probes

`dvp_type_probe_tof` and `dvp_type_probe_tp` isolate the `TOF` and `TP` local
symbol types. Their observable output intentionally bypasses the timer result,
so a failed ISPSoft gate measures type availability rather than a disputed
timer-boundary convention. Run the probes only after the frozen Balanced-100
batch; calibration results are not task-score observations. Add a type to the
hard incompatibility set only when ISPSoft returns a deterministic compile
diagnostic for the corresponding single-type probe.
