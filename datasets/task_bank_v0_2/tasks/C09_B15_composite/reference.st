FUNCTION_BLOCK C09_B15_composite
VAR_INPUT
    A_SensorA : REAL;
    A_SensorB : REAL;
    A_MaxDifference : REAL;
    A_Enable : BOOL;
    A_Reset : BOOL;
    B_Value : REAL;
    B_HighLimit : REAL;
    B_HighHighLimit : REAL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_Alarm : BOOL;
    A_Disagreeing : BOOL;
    B_HighAlarm : BOOL;
    B_HighHighAlarm : BOOL;
    B_Shutdown : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    A_DisagreeTimer : TON;
END_VAR

A_Disagreeing := A_Enable AND (ABS(A_SensorA - A_SensorB) > A_MaxDifference);
A_DisagreeTimer(IN := A_Disagreeing, PT := T#300ms);
IF A_DisagreeTimer.Q THEN
    A_Alarm := TRUE;
ELSIF A_Reset AND (NOT A_Disagreeing) THEN
    A_Alarm := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_Alarm THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := SubsystemBEnable AND (NOT CrossReady);

IF SubsystemBEnable AND CrossReady THEN
    IF B_Value >= B_HighHighLimit THEN
        B_HighAlarm := TRUE;
        B_HighHighAlarm := TRUE;
        B_Shutdown := TRUE;
    ELSIF B_Value >= B_HighLimit THEN
        B_HighAlarm := TRUE;
    END_IF;
    IF B_Reset AND (B_Value < B_HighLimit) THEN
        B_HighAlarm := FALSE;
        B_HighHighAlarm := FALSE;
        B_Shutdown := FALSE;
    END_IF;
ELSE
    B_HighAlarm := FALSE;
    B_HighHighAlarm := FALSE;
    B_Shutdown := FALSE;
END_IF;

END_FUNCTION_BLOCK
