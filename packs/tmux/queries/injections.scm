; Only tmux format contexts use the packaged tmuxf companion. Ordinary strings,
; shell commands, comments, and plugin values keep the main grammar's highlights.
; Capture the inner string node so quote delimiters are outside the injection.

([
  (set_option_directive
    (option) @_option
    (value (string) @injection.content))
  (set_window_option_directive
    (option) @_option
    (value (string) @injection.content))
]
  (#not-match? @_option "^@")
  (#match? @_option "(^status-(left|right)$|^set-titles-string$|-format(\\[[0-9]+\\])?$)")
  (#set! injection.language "tmuxf"))

; These nodes are arguments explicitly defined as tmux formats by the grammar.
([
  (format (string) @injection.content)
  (key_format (string) @injection.content)
  (filter (string) @injection.content)
  (inputs (string) @injection.content)
  (name_what_format (string) @injection.content)
  (message (string) @injection.content)
  (condition (string) @injection.content)
]
  (#set! injection.language "tmuxf"))

; if-shell's first argument is a format only when the F flag is present.
(if_shell_directive
  (command_line_option) @_flags
  (shell) @injection.content
  (#match? @_flags "^-.*F")
  (#set! injection.language "tmuxf"))
