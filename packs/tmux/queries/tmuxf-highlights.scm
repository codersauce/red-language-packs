; Reviewed for Red against tree-sitter-tmuxf bf2eee4772551c0801ece5e746c6016b9cb61ab2.
; Derived from upstream's MIT-licensed query. Parent tmux strings provide the
; default color, so plain text in a format string keeps its original style.

[
  (format)
  (simple_expansion)
] @variable.builtin

((expansion) @variable.builtin
  (#not-match? @variable.builtin "^#[{]@"))

((expansion) @variable
  (#match? @variable "^#[{]@"))

(identifier) @variable
(condition) @variable
(key) @property
(value) @constant.builtin
(rgb) @constant.builtin
(function) @function.call
(shell) @string

["{" "}" "(" ")" "[" "]"] @punctuation.bracket
; Restrict separators to expressions: an ordinary comma/colon in status text
; must retain the surrounding string color, even during error recovery.
[
  (syntax "," @punctuation.delimiter)
  (if "," @punctuation.delimiter)
  (binary "," @punctuation.delimiter)
  (binary ":" @punctuation.delimiter)
  (logic "," @punctuation.delimiter)
  (logic ":" @punctuation.delimiter)
  (unary ";" @punctuation.delimiter)
  (unary ":" @punctuation.delimiter)
]
["@" "%" "#"] @punctuation.special
["=" "?"] @operator
