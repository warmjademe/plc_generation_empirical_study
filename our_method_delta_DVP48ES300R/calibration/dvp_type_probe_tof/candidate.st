FUNCTION_BLOCK DVP_TYPE_PROBE_TOF
VAR_INPUT
    Enable : BOOL;
END_VAR
VAR_OUTPUT
    Active : BOOL;
END_VAR
VAR
    ProbeTimer : TOF;
END_VAR
ProbeTimer(IN := Enable, PT := T#100ms);
Active := Enable;
END_FUNCTION_BLOCK
