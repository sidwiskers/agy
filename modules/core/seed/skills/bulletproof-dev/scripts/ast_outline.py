#!/usr/bin/env python3
"""
ast_outline.py - Ultra-fast AST symbol outliner for Python, JS/TS, and Shell.
Extracts classes, methods, signatures, types, and imports without context bloat.

Usage:
    python3 ast_outline.py <file_path>
"""
import sys
import os
import ast
import re

def outline_python(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=path)
    except Exception as e:
        print(f"[ERROR] Failed to parse Python AST: {e}")
        return

    print(f"=== AST Outline: {os.path.basename(path)} (Python) ===")
    imports = []
    classes = []
    functions = []
    globals_list = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = ", ".join(a.name for a in node.names)
            imports.append(f"from {mod} import {names}")
        elif isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
            base_str = f"({', '.join(bases)})" if bases else ""
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in item.args.args]
                    ret = ""
                    if hasattr(ast, "unparse") and item.returns:
                        ret = f" -> {ast.unparse(item.returns)}"
                    prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                    methods.append(
                        f"  • {prefix}def {item.name}({', '.join(args)}){ret} [line {item.lineno}]"
                    )
            classes.append((f"class {node.name}{base_str} [line {node.lineno}]:", methods))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            ret = ""
            if hasattr(ast, "unparse") and node.returns:
                ret = f" -> {ast.unparse(node.returns)}"
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            functions.append(
                f"• {prefix}def {node.name}({', '.join(args)}){ret} [line {node.lineno}]"
            )
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    globals_list.append(f"{t.id} [line {node.lineno}]")

    if imports:
        print("\n--- Imports ---")
        for imp in imports[:25]:
            print(f"  {imp}")
        if len(imports) > 25:
            print(f"  ... and {len(imports) - 25} more")

    if globals_list:
        print("\n--- Constants / Globals ---")
        for g in globals_list[:20]:
            print(f"  {g}")

    if classes:
        print("\n--- Classes & Methods ---")
        for cname, cmeths in classes:
            print(f"{cname}")
            for m in cmeths:
                print(f"  {m}")

    if functions:
        print("\n--- Module Functions ---")
        for f in functions:
            print(f"  {f}")
    print("=" * 50)

def outline_text_symbols(path):
    print(f"=== Symbol Outline: {os.path.basename(path)} ===")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return

    fn_pattern = re.compile(
        r'^\s*(?:export\s+)?(?:async\s+)?(?:function\s+([A-Za-z0-9_$]+)|'
        r'(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|'
        r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+([A-Za-z0-9_$]+)\s*\([^)]*\))'
    )
    class_pattern = re.compile(r'^\s*(?:export\s+)?(?:class|interface|type|struct|enum)\s+([A-Za-z0-9_$]+)')

    symbols = []
    for i, line in enumerate(lines, 1):
        cm = class_pattern.search(line)
        if cm:
            symbols.append(f"Line {i:4d}: {line.strip()}")
            continue
        fm = fn_pattern.search(line)
        if fm:
            symbols.append(f"Line {i:4d}: {line.strip()}")

    for s in symbols[:60]:
        print(f"  {s}")
    if len(symbols) > 60:
        print(f"  ... and {len(symbols) - 60} more symbols")
    print("=" * 50)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ast_outline.py <file_path>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)

    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        outline_python(path)
    else:
        outline_text_symbols(path)

if __name__ == "__main__":
    main()
