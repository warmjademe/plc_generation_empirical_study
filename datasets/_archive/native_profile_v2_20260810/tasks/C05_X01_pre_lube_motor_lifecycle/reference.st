FUNCTION_BLOCK C05_X01_pre_lube_motor_lifecycle
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
    Permit : BOOL;
    OilPressure : BOOL;
    MotorFeedback : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    LubePump : BOOL;
    MotorCommand : BOOL;
    Cooldown : BOOL;
    Fault : BOOL;
    State : INT;
END_VAR
VAR
    PreLube : TON;
    FeedbackWait : TON;
    CoolTimer : TON;
END_VAR

PreLube(IN := (State = 1) AND OilPressure, PT := T#300ms);
FeedbackWait(IN := (State = 2) AND (NOT MotorFeedback), PT := T#400ms);
CoolTimer(IN := (State = 4), PT := T#300ms);
IF (State <> 0) AND (State <> 4) AND (Stop OR (NOT Permit)) THEN
    State := 4;
ELSIF (State = 3) AND (NOT OilPressure) THEN
    Fault := TRUE;
    State := 4;
ELSIF (State = 2) AND FeedbackWait.Q THEN
    Fault := TRUE;
    State := 4;
ELSIF (State = 0) AND Start AND Permit AND (NOT Stop) AND (NOT Fault) THEN
    State := 1;
ELSIF (State = 1) AND PreLube.Q THEN
    State := 2;
ELSIF (State = 2) AND MotorFeedback THEN
    State := 3;
ELSIF (State = 4) AND CoolTimer.Q THEN
    State := 0;
END_IF;
IF Reset AND (State = 0) AND (NOT Start) THEN Fault := FALSE; END_IF;
LubePump := ((State = 1) OR (State = 2) OR (State = 3) OR (State = 4));
MotorCommand := ((State = 2) OR (State = 3)) AND (NOT Fault);
Cooldown := (State = 4);

END_FUNCTION_BLOCK
