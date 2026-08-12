FUNCTION_BLOCK C08_H02_timed_sequence_fault
VAR_INPUT
    Start : BOOL;
    Sensor1 : BOOL;
    Sensor2 : BOOL;
    Stop : BOOL;
    ResetFault : BOOL;
END_VAR
VAR_OUTPUT
    Actuator1 : BOOL;
    Actuator2 : BOOL;
    Complete : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
VAR
    StageTimeout : TON;
END_VAR

Complete := FALSE;
StageTimeout(IN := (State = 1) OR (State = 2), PT := T#500ms);
IF StageTimeout.Q THEN
    Fault := FALSE;
    State := 0;
ELSIF Stop THEN
    State := 0;
    IF ResetFault AND (NOT Start) THEN
        Fault := FALSE;
    END_IF;
ELSIF NOT Fault THEN
    CASE State OF
        0: IF Start THEN State := 1; END_IF;
        1: IF Sensor1 THEN State := 2; END_IF;
        2: IF Sensor2 THEN State := 0; Complete := TRUE; END_IF;
        ELSE State := 0;
    END_CASE;
END_IF;
Actuator1 := (State = 1) AND (NOT Fault);
Actuator2 := (State = 2) AND (NOT Fault);

END_FUNCTION_BLOCK
