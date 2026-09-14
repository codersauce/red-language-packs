# Third-party notices

## tmux grammar and adapted highlighting queries

- Project: <https://github.com/Freed-Wu/tree-sitter-tmux>
- Revision: `58147321fa1f00daec15dd4d371bc9e2e9373459`
- Source archive SHA-256: `9ecfcc82c6be13a2e3a8e92fe033dbcc81d91548df5ff7c9189bdb4ed9e75785`
- License: `MIT`
- Source review: The pinned Arborium inventory has no tmux grammar; use the reviewed upstream grammar and a packaged tmuxf companion for embedded formats.
- Reviewed local patch: `patches/tmux.patch`, SHA-256 `c6d4abe5a33f944c8f7e771c14664da014f28825110d78f821d35c745879656c`

```text
MIT License

Copyright (c) 2024 Neorocks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## tmux format strings grammar and adapted highlighting queries

- Project: <https://github.com/Freed-Wu/tree-sitter-tmuxf>
- Revision: `bf2eee4772551c0801ece5e746c6016b9cb61ab2`
- Source archive SHA-256: `f151ea060d511b2d3eb1266f4d4da6f11c8e2e98d019b78f065ad566c464a5c9`
- License: `MIT`
- Source review: Current tmux grammar delegates format expressions and inline styles to tmuxf; bundle the reviewed grammar in the same package without claiming file selectors.
- Reviewed local patch: `patches/tmuxf.patch`, SHA-256 `c53436b203257bffdc1e5bcdb419437de843817ccf4b72d6c44192dde2ba2e10`

```text
MIT License

Copyright (c) 2024 Neorocks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
