; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(character_literal) (comment) (interpolated_string_expression) (raw_string_literal) (string_literal) (verbatim_string_literal)] @indent.ignore
