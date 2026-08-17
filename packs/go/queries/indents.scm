; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(comment) (interpreted_string_literal) (raw_string_literal) (rune_literal)] @indent.ignore
