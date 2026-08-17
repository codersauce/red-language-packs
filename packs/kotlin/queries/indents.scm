; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(character_literal) (line_comment) (multiline_comment) (string_literal)] @indent.ignore
