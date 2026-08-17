; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(block_comment) (character_literal) (line_comment) (string_literal)] @indent.ignore
