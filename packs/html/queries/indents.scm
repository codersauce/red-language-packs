; Red-owned indentation rules, query contract v1.
((start_tag (tag_name) @indent.match) @indent.begin
  (#not-match? @indent.match "^(?i:area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$"))
(end_tag (tag_name) @indent.match) @indent.end
[(comment)] @indent.ignore
