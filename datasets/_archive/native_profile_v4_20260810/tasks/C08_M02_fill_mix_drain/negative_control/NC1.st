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

Complete := FALSE;
IF Abort THEN
    State := 0;
ELSE
    CASE State OF
        0: IF Start THEN State := 1; END_IF;
        1: IF HighLevel THEN State := 2; END_IF;
        2: IF MixDone THEN State := 3; END_IF;
        3: IF LowLevel THEN State := 0; Complete := FALSE; END_IF;
        ELSE State := 0;
    END_CASE;
END_IF;
FillValve := State = 1;
Mixer := State = 2;
DrainValve := State = 3;

END_FUNCTION_BLOCK
