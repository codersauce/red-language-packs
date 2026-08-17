; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(comment) (line_string_literal) (multi_line_string_literal) (multiline_comment) (raw_string_literal)] @indent.ignore
