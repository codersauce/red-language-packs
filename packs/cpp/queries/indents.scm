; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(char_literal) (comment) (raw_string_literal) (string_literal)] @indent.ignore
