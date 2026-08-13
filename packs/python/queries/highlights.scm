; Red-owned Python highlighting refinements layered over the pinned Arborium query.
; Grammar revision: 26855eabccb19c6abf499fbc5b8dc7cc9ab8bc64 (MIT).

[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
] @punctuation.bracket

[
  ","
  ":"
  "."
  ";"
] @punctuation.delimiter

(function_definition
  "def" @keyword.function)

(import_statement
  "import" @keyword.import)

(import_from_statement
  [
    "from"
    "import"
  ] @keyword.import)

[
  "async"
  "await"
] @keyword.coroutine

(parameters
  (identifier) @variable.parameter)

(call
  function: (identifier) @function.call)

(call
  function: (attribute
    attribute: (identifier) @function.method.call))

(attribute
  attribute: (identifier) @variable.member)

((identifier) @type.builtin
  (#match? @type.builtin "^(bool|bytearray|bytes|complex|dict|float|frozenset|int|list|memoryview|object|range|set|slice|str|tuple|type)$"))

(escape_sequence) @string.escape
