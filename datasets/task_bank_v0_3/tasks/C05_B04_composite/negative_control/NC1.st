FUNCTION_BLOCK C05_B04_composite
VAR_INPUT
    A_Start : BOOL;
    A_Stop : BOOL;
    A_Permit : BOOL;
    A_Stage1Feedback : BOOL;
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
    A_Stage1 : BOOL;
    A_Stage2 : BOOL;
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
    A_FeedbackStable : TON;
    A_FeedbackTimeout : TON;
    B_PreLube : TON;
    B_FeedbackWait : TON;
    B_CoolTimer : TON;
END_VAR

A_FeedbackStable(IN := A_Stage1Feedback AND A_Stage1, PT := T#300ms);
A_FeedbackTimeout(IN := A_Stage1 AND (NOT A_Stage1Feedback), PT := T#600ms);

IF A_FeedbackTimeout.Q THEN
    A_Fault := FALSE;
END_IF;
IF A_Stop AND (NOT A_Start) THEN
    A_Fault := FALSE;
END_IF;

IF A_Stop OR (NOT A_Permit) OR A_Fault THEN
    A_Stage1 := FALSE;
    A_Stage2 := FALSE;
ELSIF A_Start THEN
    A_Stage1 := TRUE;
    A_Stage2 := A_FeedbackStable.Q;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Stage1 THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

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
