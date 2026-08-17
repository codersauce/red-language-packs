; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(comment) (string_value)] @indent.ignore
