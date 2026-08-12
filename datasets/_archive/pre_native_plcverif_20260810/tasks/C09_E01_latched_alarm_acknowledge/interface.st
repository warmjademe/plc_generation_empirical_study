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
END_FUNCTION_BLOCK
