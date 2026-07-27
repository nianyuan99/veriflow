"""Tree-sitter AST 分析器 — 结构化代码分析"""

from __future__ import annotations


class TreeSitterAnalyzer:
    """使用 Tree-sitter 进行结构化代码分析

    如果 tree-sitter 不可用，回退到纯文本正则分析。
    """

    def __init__(self):
        self._available = False
        self._parser = None
        self._language_modules: dict[str, object] = {}

        try:
            import tree_sitter

            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def analyze_file(self, file_path: str, source_code: str) -> dict:
        """分析单个文件的 AST 结构"""
        if not self._available:
            return self._fallback_analyze(file_path, source_code)

        language = self._detect_language(file_path)
        if not language:
            return {"error": f"Unsupported language: {file_path}"}

        # 尝试加载对应语言的 parser
        try:
            parser = self._get_parser(language)
            tree = parser.parse(bytes(source_code, "utf-8"))
            return self._extract_ast_info(tree.root_node, source_code)
        except Exception as e:
            return {"error": str(e)}

    def _detect_language(self, file_path: str) -> str | None:
        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        mapping = {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "go": "go",
            "rs": "rust",
        }
        return mapping.get(ext.lower())

    def _get_parser(self, language: str):
        """获取或创建语言 parser"""
        import tree_sitter

        if language not in self._language_modules:
            # 尝试动态加载
            try:
                lang_module = tree_sitter.Language(
                    f"tree_sitter_{language}.so", language
                )
            except Exception:
                # 回退: 尝试从 tree_sitter_languages 导入
                try:
                    import tree_sitter_languages

                    lang_module = tree_sitter_languages.get_language(language)
                except ImportError:
                    raise RuntimeError(
                        f"Cannot load tree-sitter parser for {language}"
                    )

            self._language_modules[language] = lang_module
            parser = tree_sitter.Parser()
            parser.set_language(lang_module)
            return parser
        return self._language_modules.get(language)

    def _extract_ast_info(self, node, source_code: str) -> dict:
        """提取 AST 关键信息"""
        functions = []
        classes = []
        imports = []

        def _walk(n, depth=0):
            if depth > 50:
                return
            node_type = n.type
            if node_type in ("function_definition", "function_declaration", "method_definition"):
                name_node = n.child_by_field_name("name")
                if name_node:
                    functions.append({
                        "name": source_code[name_node.start_byte:name_node.end_byte],
                        "start_line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    })
            elif node_type in ("class_definition", "class_declaration"):
                name_node = n.child_by_field_name("name")
                if name_node:
                    classes.append({
                        "name": source_code[name_node.start_byte:name_node.end_byte],
                        "start_line": n.start_point[0] + 1,
                        "end_line": n.end_point[0] + 1,
                    })
            elif node_type in ("import_statement", "import_declaration", "import_from_statement"):
                imports.append({
                    "text": source_code[n.start_byte:n.end_byte],
                    "line": n.start_point[0] + 1,
                })

            for child in n.children:
                _walk(child, depth + 1)

        _walk(node)
        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
        }

    def _fallback_analyze(self, file_path: str, source_code: str) -> dict:
        """无 tree-sitter 时的纯文本分析"""
        import re

        functions = []
        for m in re.finditer(
            r"^\s*(?:def|async def|function|func|class)\s+(\w+)",
            source_code,
            re.MULTILINE,
        ):
            line = source_code[: m.start()].count("\n") + 1
            functions.append({"name": m.group(1), "start_line": line, "end_line": line})

        return {
            "functions": functions,
            "classes": [],
            "imports": [],
            "fallback": True,
        }
