FUNCTION_BLOCK C05_B18_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_OilPressure : BOOL;
    A_MotorFeedback : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Overload : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_LubePump : BOOL;
    A_MotorCommand : BOOL;
    A_Cooldown : BOOL;
    A_Fault : BOOL;
    A_State : INT;
    B_Main : BOOL;
    B_Star : BOOL;
    B_Delta : BOOL;
    B_Fault : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_PreLube : TON;
    A_FeedbackWait : TON;
    A_CoolTimer : TON;
    B_StarTimer : TON;
    B_GapTimer : TON;
END_VAR

A_PreLube(IN := (A_State = 1) AND A_OilPressure, PT := T#300ms);
A_FeedbackWait(IN := (A_State = 2) AND (NOT A_MotorFeedback), PT := T#400ms);
A_CoolTimer(IN := (A_State = 4), PT := T#300ms);
IF (A_State <> 0) AND (A_State <> 4) AND (A_Stop OR (NOT A_Permit)) THEN
    A_State := 4;
ELSIF (A_State = 3) AND (NOT A_OilPressure) THEN
    A_Fault := TRUE;
    A_State := 4;
ELSIF (A_State = 2) AND A_FeedbackWait.Q THEN
    A_Fault := TRUE;
    A_State := 4;
ELSIF (A_State = 0) AND A_Start AND A_Permit AND (NOT A_Stop) AND (NOT A_Fault) THEN
    A_State := 1;
ELSIF (A_State = 1) AND A_PreLube.Q THEN
    A_State := 2;
ELSIF (A_State = 2) AND A_MotorFeedback THEN
    IF A_OilPressure THEN
        A_State := 3;
    ELSE
        A_Fault := TRUE;
        A_State := 4;
    END_IF;
ELSIF (A_State = 4) AND A_CoolTimer.Q THEN
    A_State := 0;
END_IF;
IF A_Reset AND (A_State = 0) AND (NOT A_Start) THEN A_Fault := FALSE; END_IF;
A_LubePump := ((A_State = 1) OR (A_State = 2) OR (A_State = 3) OR (A_State = 4));
A_MotorCommand := ((A_State = 2) OR (A_State = 3)) AND (NOT A_Fault);
A_Cooldown := (A_State = 4);

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_LubePump THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_StarTimer(IN := B_Main AND B_Star, PT := T#500ms);
    B_GapTimer(IN := B_Main AND (NOT B_Star) AND (NOT B_Delta), PT := T#200ms);

    IF B_Overload THEN
        B_Fault := TRUE;
    END_IF;
    IF B_Reset AND (NOT B_Start) AND (NOT B_Overload) THEN
        B_Fault := FALSE;
    END_IF;

    IF B_Stop OR B_Overload OR B_Fault THEN
        B_Main := FALSE;
        B_Star := FALSE;
        B_Delta := FALSE;
    ELSIF B_Start AND (NOT B_Main) THEN
        B_Main := TRUE;
        B_Star := TRUE;
        B_Delta := FALSE;
    ELSIF B_StarTimer.Q THEN
        B_Star := FALSE;
    ELSIF B_GapTimer.Q AND B_Main THEN
        B_Delta := TRUE;
    END_IF;
ELSE
    B_Main := FALSE;
    B_Star := FALSE;
    B_Delta := FALSE;
    B_Fault := FALSE;
END_IF;

END_FUNCTION_BLOCK
