FUNCTION_BLOCK C08_E01_two_step_cycle
VAR_INPUT
    Start : BOOL;
    Step1Done : BOOL;
    Step2Done : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Step1 : BOOL;
    Step2 : BOOL;
    Complete : BOOL;
    State : INT;
END_VAR

IF Reset THEN
    State := 0;
ELSE
    CASE State OF
        0: IF Start THEN State := 2; END_IF;
        1: IF Step1Done THEN State := 2; END_IF;
        2: IF Step2Done THEN State := 3; END_IF;
        3: State := 3;
        ELSE State := 0;
    END_CASE;
END_IF;
Step1 := State = 1;
Step2 := State = 2;
Complete := State = 3;

END_FUNCTION_BLOCK
