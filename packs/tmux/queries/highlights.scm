; Reviewed for Red against tree-sitter-tmux 58147321fa1f00daec15dd4d371bc9e2e9373459.
; Derived from upstream's MIT-licensed query; use Rust Tree-sitter predicates.

(comment) @comment
(string) @string
(shell) @string
(int) @constant.builtin

(path (string) @string.special.path)
(variable_name) @variable
(name (string) @variable)

((option) @variable
  (#match? @variable "^@"))

((option) @property
  (#not-match? @property "^@"))

(command_line_option) @variable.parameter
(key (string) @constant.builtin)
(key_table (string) @constant.builtin)
(hook_name) @property

((value (string) @constant.builtin)
  (#match? @constant.builtin "^[0-9]+$"))

((value (string) @constant.builtin)
  (#any-of? @constant.builtin "on" "off"))

[
  (if_keyword)
  (elif_keyword)
  (else_keyword)
  (endif_keyword)
] @keyword.conditional

[
  (hidden_keyword)
] @keyword

(command) @function.builtin

(source_file_directive (command) @keyword.import)

"=" @operator
";" @punctuation.delimiter

["{" "}" "[" "]"] @punctuation.bracket
