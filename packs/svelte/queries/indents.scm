; Red-owned indentation rules, query contract v1.
((start_tag (tag_name) @indent.match) @indent.begin
  (#not-match? @indent.match "^(?i:area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$"))
(end_tag (tag_name) @indent.match) @indent.end
([(if_start) (each_start) (await_start) (key_start) (snippet_start)] @indent.begin
  (#set! indent.match "svelte-block"))
([(if_end) (each_end) (await_end) (key_end) (snippet_end)] @indent.end
  (#set! indent.match "svelte-block"))
([(else_start) (else_if_start) (then_start) (catch_start)] @indent.branch
  (#set! indent.match "svelte-block"))
[(comment)] @indent.ignore
