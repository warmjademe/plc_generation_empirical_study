FUNCTION_BLOCK C05_B08_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Overload : BOOL;
    A_Reset : BOOL;
    B_Start : BOOL;
    B_Stop : BOOL;
    B_Permit : BOOL;
    B_OilPressure : BOOL;
    B_MotorFeedback : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Main : BOOL;
    A_Star : BOOL;
    A_Delta : BOOL;
    A_Fault : BOOL;
    B_LubePump : BOOL;
    B_MotorCommand : BOOL;
    B_Cooldown : BOOL;
    B_Fault : BOOL;
    B_State : INT;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_StarTimer : TON;
    A_GapTimer : TON;
    B_PreLube : TON;
    B_FeedbackWait : TON;
    B_CoolTimer : TON;
END_VAR

A_StarTimer(IN := A_Main AND A_Star, PT := T#500ms);
A_GapTimer(IN := A_Main AND (NOT A_Star) AND (NOT A_Delta), PT := T#200ms);

IF A_Overload THEN
    A_Fault := TRUE;
END_IF;
IF A_Reset AND (NOT A_Start) AND (NOT A_Overload) THEN
    A_Fault := FALSE;
END_IF;

IF A_Stop OR A_Overload OR A_Fault THEN
    A_Main := FALSE;
    A_Star := FALSE;
    A_Delta := FALSE;
ELSIF A_Start AND (NOT A_Main) THEN
    A_Main := TRUE;
    A_Star := TRUE;
    A_Delta := FALSE;
ELSIF A_StarTimer.Q THEN
    A_Star := FALSE;
ELSIF A_GapTimer.Q AND A_Main THEN
    A_Delta := TRUE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Main THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_PreLube(IN := (B_State = 1) AND B_OilPressure, PT := T#300ms);
    B_FeedbackWait(IN := (B_State = 2) AND (NOT B_MotorFeedback), PT := T#400ms);
    B_CoolTimer(IN := (B_State = 4), PT := T#300ms);
    IF (B_State <> 0) AND (B_State <> 4) AND (B_Stop OR (NOT B_Permit)) THEN
        B_State := 4;
    ELSIF (B_State = 3) AND (NOT B_OilPressure) THEN
        B_Fault := TRUE;
        B_State := 4;
    ELSIF (B_State = 2) AND B_FeedbackWait.Q THEN
        B_Fault := TRUE;
        B_State := 4;
    ELSIF (B_State = 0) AND B_Start AND B_Permit AND (NOT B_Stop) AND (NOT B_Fault) THEN
        B_State := 1;
    ELSIF (B_State = 1) AND B_PreLube.Q THEN
        B_State := 2;
    ELSIF (B_State = 2) AND B_MotorFeedback THEN
        IF B_OilPressure THEN
            B_State := 3;
        ELSE
            B_Fault := TRUE;
            B_State := 4;
        END_IF;
    ELSIF (B_State = 4) AND B_CoolTimer.Q THEN
        B_State := 0;
    END_IF;
    IF B_Reset AND (B_State = 0) AND (NOT B_Start) THEN B_Fault := FALSE; END_IF;
    B_LubePump := ((B_State = 1) OR (B_State = 2) OR (B_State = 3) OR (B_State = 4));
    B_MotorCommand := ((B_State = 2) OR (B_State = 3)) AND (NOT B_Fault);
    B_Cooldown := (B_State = 4);
ELSE
    B_LubePump := FALSE;
    B_MotorCommand := FALSE;
    B_Cooldown := FALSE;
    B_Fault := FALSE;
    B_State := 0;
END_IF;

END_FUNCTION_BLOCK
