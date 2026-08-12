FUNCTION_BLOCK C09_B11_composite
VAR_INPUT
    A_Value : REAL;
    A_HighLimit : REAL;
    A_HighHighLimit : REAL;
    A_Reset : BOOL;
    B_SensorA : REAL;
    B_SensorB : REAL;
    B_MaxDifference : REAL;
    B_Enable : BOOL;
    B_Reset : BOOL;
    SubsystemBEnable : BOOL;
    CrossReset : BOOL;
END_VAR
VAR_OUTPUT
    A_HighAlarm : BOOL;
    A_HighHighAlarm : BOOL;
    A_Shutdown : BOOL;
    B_Alarm : BOOL;
    B_Disagreeing : BOOL;
    CrossReady : BOOL;
    CrossBlocked : BOOL;
END_VAR
VAR
    B_DisagreeTimer : TON;
END_VAR

IF A_Value >= A_HighHighLimit THEN
    A_HighAlarm := TRUE;
    A_HighHighAlarm := TRUE;
    A_Shutdown := TRUE;
ELSIF A_Value >= A_HighLimit THEN
    A_HighAlarm := TRUE;
END_IF;
IF A_Reset AND (A_Value < A_HighLimit) THEN
    A_HighAlarm := FALSE;
    A_HighHighAlarm := FALSE;
    A_Shutdown := FALSE;
END_IF;

IF CrossReset THEN
    CrossReady := FALSE;
ELSIF A_HighAlarm THEN
    CrossReady := TRUE;
END_IF;
CrossBlocked := FALSE;

IF SubsystemBEnable AND CrossReady THEN
    B_Disagreeing := B_Enable AND (ABS(B_SensorA - B_SensorB) > B_MaxDifference);
    B_DisagreeTimer(IN := B_Disagreeing, PT := T#300ms);
    IF B_DisagreeTimer.Q THEN
        B_Alarm := TRUE;
    ELSIF B_Reset AND (NOT B_Disagreeing) THEN
        B_Alarm := FALSE;
    END_IF;
ELSE
    B_Alarm := FALSE;
    B_Disagreeing := FALSE;
END_IF;

END_FUNCTION_BLOCK
