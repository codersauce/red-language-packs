; Red-owned indentation rules, query contract v1.
["{" "["] @indent.begin
["}" "]"] @indent.end
(line_continuation) @indent.continuation
[(comment) (double_quoted_string) (json_string) (single_quoted_string)] @indent.ignore
