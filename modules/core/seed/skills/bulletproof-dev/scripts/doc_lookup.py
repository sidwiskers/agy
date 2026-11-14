#!/usr/bin/env python3
"""
doc_lookup.py - Ground-truth package & API inspector.
Inspects locally installed Python, Node, and Android packages to eliminate
knowledge gaps and hallucinated APIs before writing code.

Usage:
    python3 doc_lookup.py py <package_or_module> [member]
    python3 doc_lookup.py node <package_name>
    python3 doc_lookup.py project [dir]
"""
import sys
import os
import json
import importlib
import inspect

def inspect_python(module_name, member_name=None):
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        print(f"[ERROR] Cannot import Python module '{module_name}': {e}")
        return

    ver = getattr(mod, "__version__", "unknown")
    doc = getattr(mod, "__doc__", "") or ""
    file_path = getattr(mod, "__file__", "built-in")

    print(f"=== Python Module: {module_name} (v{ver}) ===")
    print(f"File: {file_path}")
    if doc:
        first_line = doc.strip().split("\n")[0]
        print(f"Doc: {first_line}")

    target = mod
    if member_name:
        if not hasattr(mod, member_name):
            print(f"[ERROR] '{module_name}' has no attribute '{member_name}'")
            return
        target = getattr(mod, member_name)
        print(f"\n--- Member: {member_name} ---")
        try:
            sig = inspect.signature(target)
            print(f"Signature: {member_name}{sig}")
        except Exception:
            pass
        member_doc = getattr(target, "__doc__", "")
        if member_doc:
            print(f"Docstring:\n{member_doc[:400]}")
        return

    # List public functions and classes
    members = []
    for name in dir(target):
        if name.startswith("_"):
            continue
        try:
            val = getattr(target, name)
            if inspect.isclass(val):
                members.append(f"[class]    {name}")
            elif inspect.isfunction(val) or inspect.isbuiltin(val):
                try:
                    sig = inspect.signature(val)
                    members.append(f"[def]      {name}{sig}")
                except Exception:
                    members.append(f"[def]      {name}()")
            else:
                members.append(f"[var]      {name}")
        except Exception:
            continue

    print(f"\nPublic exports ({len(members)} total):")
    for m in members[:40]:
        print(f"  {m}")
    if len(members) > 40:
        print(f"  ... and {len(members) - 40} more")
    print("=" * 50)

def inspect_node(package_name, start_dir="."):
    cur = os.path.abspath(start_dir)
    pkg_json_path = None
    while cur != os.path.dirname(cur):
        test_path = os.path.join(cur, "node_modules", package_name, "package.json")
        if os.path.isfile(test_path):
            pkg_json_path = test_path
            break
        cur = os.path.dirname(cur)

    if not pkg_json_path:
        print(f"[ERROR] Node package '{package_name}' not found in any parent node_modules.")
        return

    try:
        with open(pkg_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ver = data.get("version", "unknown")
        desc = data.get("description", "")
        main_entry = data.get("main", "")
        types_entry = data.get("types", data.get("typings", ""))

        print(f"=== Node Package: {package_name} (v{ver}) ===")
        if desc:
            print(f"Description: {desc}")
        print(f"Location: {os.path.dirname(pkg_json_path)}")
        if main_entry:
            print(f"Main Entry: {main_entry}")
        if types_entry:
            print(f"TypeScript Types: {types_entry}")

        exports = data.get("exports")
        if exports:
            print("\nDeclared Exports:")
            if isinstance(exports, dict):
                for k, v in list(exports.items())[:10]:
                    print(f"  {k} -> {v}")
        print("=" * 50)
    except Exception as e:
        print(f"[ERROR] Failed to read package.json: {e}")

def inspect_project(directory="."):
    directory = os.path.abspath(directory)
    print(f"=== Project Manifest Audit: {directory} ===")
    found = False

    # 1. package.json
    pkg_json = os.path.join(directory, "package.json")
    if os.path.isfile(pkg_json):
        found = True
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                d = json.load(f)
            print(f"[Node/JS] Project: {d.get('name', 'unnamed')} v{d.get('version', '0.0.0')}")
            deps = d.get("dependencies", {})
            dev_deps = d.get("devDependencies", {})
            if deps:
                print(f"  Dependencies ({len(deps)}): {', '.join(list(deps.keys())[:15])}")
            if dev_deps:
                print(f"  DevDependencies ({len(dev_deps)}): {', '.join(list(dev_deps.keys())[:15])}")
        except Exception as e:
            print(f"[Node/JS] Failed to read package.json: {e}")

    # 2. requirements.txt / pyproject.toml
    req_txt = os.path.join(directory, "requirements.txt")
    if os.path.isfile(req_txt):
        found = True
        with open(req_txt, "r", encoding="utf-8", errors="ignore") as f:
            reqs = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"[Python] requirements.txt found ({len(reqs)} items):")
        for r in reqs[:10]:
            print(f"  {r}")

    # 3. Android build.gradle / AndroidManifest.xml
    manifest = os.path.join(directory, "app", "src", "main", "AndroidManifest.xml")
    if os.path.isfile(manifest):
        found = True
        print(f"[Android] AndroidManifest.xml found -> {manifest}")

    if not found:
        print("[INFO] No standard package manifests found in current directory.")
    print("=" * 50)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 doc_lookup.py py <mod> [member] | node <pkg> | project [dir]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "py":
        if len(sys.argv) < 3:
            print("Usage: python3 doc_lookup.py py <module_name> [member_name]")
            sys.exit(1)
        inspect_python(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "node":
        if len(sys.argv) < 3:
            print("Usage: python3 doc_lookup.py node <package_name>")
            sys.exit(1)
        inspect_node(sys.argv[2])
    elif cmd == "project":
        d = sys.argv[2] if len(sys.argv) > 2 else "."
        inspect_project(d)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
