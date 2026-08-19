FUNCTION_BLOCK DVP_TimerScanCalibration
VAR_INPUT
    Enable : BOOL;
END_VAR
VAR_OUTPUT
    CounterDone : BOOL;
    TimerDone : BOOL;
END_VAR
VAR
    ScanCount : INT := 0;
    DelayTimer : TON;
END_VAR

IF NOT Enable THEN
    ScanCount := 0;
ELSIF ScanCount < 4 THEN
    ScanCount := ScanCount + 1;
END_IF;

DelayTimer(IN := Enable, PT := T#300ms);
CounterDone := ScanCount >= 4;
TimerDone := DelayTimer.Q;
END_FUNCTION_BLOCK
