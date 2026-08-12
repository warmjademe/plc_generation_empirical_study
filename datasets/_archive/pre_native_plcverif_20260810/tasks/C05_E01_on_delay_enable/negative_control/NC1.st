FUNCTION_BLOCK C05_E01_on_delay_enable
VAR_INPUT
    Enable : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Delayed : BOOL;
END_VAR
VAR
    DelayTimer : TON;
END_VAR

DelayTimer(IN := Enable OR (NOT Reset), PT := T#300ms);
Delayed := DelayTimer.Q;

END_FUNCTION_BLOCK
