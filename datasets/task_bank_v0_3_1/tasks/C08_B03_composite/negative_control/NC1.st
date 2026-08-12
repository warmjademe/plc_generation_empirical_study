FUNCTION_BLOCK C08_B03_composite
VAR_INPUT
    A_Start : BOOL;
    A_Advance : BOOL;
    A_Pause : BOOL;
    A_Resume : BOOL;
    A_Abort : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_HighLevel : BOOL;
    B_MixDone : BOOL;
    B_LowLevel : BOOL;
    B_Abort : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Step1 : BOOL;
    A_Step2 : BOOL;
    A_Paused : BOOL;
    A_Aborted : BOOL;
    A_State : INT;
    B_FillValve : BOOL;
    B_Mixer : BOOL;
    B_DrainValve : BOOL;
    B_Complete : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR

IF A_Abort THEN
    A_State := 0;
    A_Paused := FALSE;
    A_Aborted := TRUE;
ELSIF A_Reset AND (NOT A_Start) AND (NOT A_Advance) AND (NOT A_Pause) AND (NOT A_Resume) THEN
    A_Aborted := FALSE;
ELSIF NOT A_Aborted THEN
    IF A_Pause AND ((A_State = 1) OR (A_State = 2)) THEN
        A_Paused := TRUE;
    ELSIF A_Resume THEN
        A_Paused := FALSE;
    END_IF;
    IF NOT A_Paused THEN
        CASE A_State OF
            0: IF A_Start THEN A_State := 1; END_IF;
            1: IF A_Advance THEN A_State := 2; END_IF;
            2: IF A_Advance THEN A_State := 3; END_IF;
            3: A_State := 3;
            ELSE A_State := 0;
        END_CASE;
    END_IF;
END_IF;
A_Step1 := (A_State = 1) AND (NOT A_Paused) AND (NOT A_Aborted);
A_Step2 := (A_State = 2) AND (NOT A_Paused) AND (NOT A_Aborted);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Step1 THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Complete := FALSE;
    IF B_Abort THEN
        B_State := 0;
    ELSE
        CASE B_State OF
            0: IF B_Start THEN B_State := 1; END_IF;
            1: IF B_HighLevel THEN B_State := 2; END_IF;
            2: IF B_MixDone THEN B_State := 3; END_IF;
            3: IF B_LowLevel THEN B_State := 0; B_Complete := TRUE; END_IF;
            ELSE B_State := 0;
        END_CASE;
    END_IF;
    B_FillValve := B_State = 1;
    B_Mixer := B_State = 2;
    B_DrainValve := B_State = 3;
ELSE
    B_FillValve := FALSE;
    B_Mixer := FALSE;
    B_DrainValve := FALSE;
    B_Complete := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK
