; Red-owned indentation rules, query contract v1.
["{" "["] @indent.begin
["}" "]"] @indent.end
[(comment) (string)] @indent.ignore
