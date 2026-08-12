FUNCTION_BLOCK C08_X01_paused_three_stage_timeout
VAR_INPUT
    Start : BOOL;
    Stage1Done : BOOL;
    Stage2Done : BOOL;
    Stage3Done : BOOL;
    Pause : BOOL;
    Abort : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Actuator1 : BOOL;
    Actuator2 : BOOL;
    Actuator3 : BOOL;
    Paused : BOOL;
    Complete : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
VAR
    StageTimer : TON;
END_VAR

Complete := FALSE;
StageTimer(IN := (State > 0) AND (NOT Pause), PT := T#500ms);
IF Abort THEN
    State := 0;
    Fault := TRUE;
ELSIF StageTimer.Q THEN
    State := 0;
    Fault := TRUE;
ELSIF (State = 0) AND Reset AND (NOT Start) AND (NOT Abort) AND (NOT Stage1Done) AND (NOT Stage2Done) AND (NOT Stage3Done) THEN
    Fault := FALSE;
ELSIF NOT Fault THEN
    IF (State = 0) AND Start THEN
        State := 1;
    ELSIF NOT Pause THEN
        CASE State OF
            1: IF Stage1Done THEN State := 2; END_IF;
            2: IF Stage2Done THEN State := 3; END_IF;
            3: IF Stage3Done THEN State := 0; Complete := TRUE; END_IF;
            ELSE State := 0;
        END_CASE;
    END_IF;
END_IF;
Paused := (State > 0) AND Pause AND (NOT Fault);
Actuator1 := (State = 1) AND (NOT Pause) AND (NOT Fault);
Actuator2 := (State = 2) AND (NOT Pause) AND (NOT Fault);
Actuator3 := (State = 3) AND (NOT Pause) AND (NOT Fault);

END_FUNCTION_BLOCK
