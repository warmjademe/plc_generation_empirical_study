FUNCTION_BLOCK C08_M02_fill_mix_drain
VAR_INPUT
    Start : BOOL;
    HighLevel : BOOL;
    MixDone : BOOL;
    LowLevel : BOOL;
    Abort : BOOL;
END_VAR
VAR_OUTPUT
    FillValve : BOOL;
    Mixer : BOOL;
    DrainValve : BOOL;
    Complete : BOOL;
    State : INT;
END_VAR
END_FUNCTION_BLOCK
