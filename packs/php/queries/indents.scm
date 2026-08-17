; Red-owned indentation rules, query contract v1.
["{" "(" "["] @indent.begin
["}" ")" "]"] @indent.end
[(comment) (encapsed_string) (heredoc) (nowdoc) (nowdoc_string) (string)] @indent.ignore
