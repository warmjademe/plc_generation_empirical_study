FUNCTION_BLOCK C08_H01_pause_resume_abort_sequence
VAR_INPUT
    Start : BOOL;
    Advance : BOOL;
    Pause : BOOL;
    Resume : BOOL;
    Abort : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Step1 : BOOL;
    Step2 : BOOL;
    Paused : BOOL;
    Aborted : BOOL;
    State : INT;
END_VAR

IF Abort THEN
    State := 0;
    Paused := FALSE;
    Aborted := FALSE;
ELSIF Reset AND (NOT Start) AND (NOT Advance) AND (NOT Pause) AND (NOT Resume) THEN
    Aborted := FALSE;
ELSIF NOT Aborted THEN
    IF Pause AND ((State = 1) OR (State = 2)) THEN
        Paused := TRUE;
    ELSIF Resume THEN
        Paused := FALSE;
    END_IF;
    IF NOT Paused THEN
        CASE State OF
            0: IF Start THEN State := 1; END_IF;
            1: IF Advance THEN State := 2; END_IF;
            2: IF Advance THEN State := 3; END_IF;
            3: State := 3;
            ELSE State := 0;
        END_CASE;
    END_IF;
END_IF;
Step1 := (State = 1) AND (NOT Paused) AND (NOT Aborted);
Step2 := (State = 2) AND (NOT Paused) AND (NOT Aborted);

END_FUNCTION_BLOCK
