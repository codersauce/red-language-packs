; Red-owned indentation rules, query contract v1.
["(" "["] @indent.begin
[")" "]"] @indent.end
([(keyword_begin) (keyword_case)] @indent.begin
  (#set! indent.match "sql-block"))
((keyword_end) @indent.end
  (#set! indent.match "sql-block"))
[(comment)] @indent.ignore
