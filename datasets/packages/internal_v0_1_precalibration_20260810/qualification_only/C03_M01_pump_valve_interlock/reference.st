FUNCTION_BLOCK C03_M01_pump_valve_interlock
VAR_INPUT
    RunRequest : BOOL;
    TankLevelOK : BOOL;
    ValveFeedbackOpen : BOOL;
    PumpFeedback : BOOL;
    Stop : BOOL;
END_VAR
VAR_OUTPUT
    ValveCommand : BOOL;
    PumpCommand : BOOL;
    InterlockAlarm : BOOL;
END_VAR

ValveCommand := RunRequest AND TankLevelOK AND (NOT Stop);
PumpCommand := ValveCommand AND ValveFeedbackOpen;
InterlockAlarm := PumpFeedback AND (NOT ValveFeedbackOpen);

END_FUNCTION_BLOCK
