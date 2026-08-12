FUNCTION_BLOCK C05_H02_star_delta_sequence
VAR_INPUT
    Start : BOOL;
    Stop : BOOL;
    Overload : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Main : BOOL;
    Star : BOOL;
    Delta : BOOL;
    Fault : BOOL;
END_VAR
VAR
    StarTimer : TON;
    GapTimer : TON;
END_VAR

StarTimer(IN := Main AND Star, PT := T#500ms);
GapTimer(IN := Main AND (NOT Star) AND (NOT Delta), PT := T#200ms);

IF Overload THEN
    Fault := TRUE;
END_IF;
IF Reset AND (NOT Start) AND (NOT Overload) THEN
    Fault := FALSE;
END_IF;

IF Stop OR Overload OR Fault THEN
    Main := FALSE;
    Star := FALSE;
    Delta := FALSE;
ELSIF Start AND (NOT Main) THEN
    Main := TRUE;
    Star := TRUE;
    Delta := FALSE;
ELSIF StarTimer.Q THEN
    Star := FALSE;
ELSIF GapTimer.Q AND Main THEN
    Delta := TRUE;
END_IF;

END_FUNCTION_BLOCK
