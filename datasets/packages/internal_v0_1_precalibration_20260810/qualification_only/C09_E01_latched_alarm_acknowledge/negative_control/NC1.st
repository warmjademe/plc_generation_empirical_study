FUNCTION_BLOCK C09_E01_latched_alarm_acknowledge
VAR_INPUT
    AlarmCondition : BOOL;
    Acknowledge : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    AlarmActive : BOOL;
    AlarmUnacked : BOOL;
END_VAR

IF AlarmCondition THEN
    AlarmActive := FALSE;
    AlarmUnacked := TRUE;
ELSE
    IF Acknowledge THEN
        AlarmUnacked := FALSE;
    END_IF;
    IF Reset THEN
        AlarmActive := FALSE;
        AlarmUnacked := FALSE;
    END_IF;
END_IF;

END_FUNCTION_BLOCK
