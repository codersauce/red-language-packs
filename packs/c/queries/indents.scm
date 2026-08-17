; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(char_literal) (comment) (string_literal)] @indent.ignore
