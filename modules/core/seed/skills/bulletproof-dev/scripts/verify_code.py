#!/usr/bin/env python3
"""
verify_code.py - Universal compiler & linter gate for Antigravity agents.
Verifies syntax, type safety, and static analysis across multiple languages.

Usage:
    python3 verify_code.py <file1> [file2 ...]
    python3 verify_code.py --dir <directory>
"""
import sys
import os
import subprocess
import shutil

def run_cmd(cmd):
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def verify_file(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return True, [f"[SKIP] Not a file: {path}"]

    ext = os.path.splitext(path)[1].lower()
    errors = []

    # 1. Python (.py)
    if ext == ".py":
        code, out, err = run_cmd(["python3", "-m", "py_compile", path])
        if code != 0:
            errors.append(f"Python Syntax Error:\n{err or out}")
        if shutil.which("ruff"):
            code, out, err = run_cmd([
                "ruff", "check", "--no-cache", "--line-length", "120",
                "--select", "E,F,W", path
            ])
            if code != 0 and (out or err):
                errors.append(f"Ruff Lint Warnings/Errors:\n{out or err}")

    # 2. JavaScript (.js, .mjs, .cjs)
    elif ext in [".js", ".mjs", ".cjs"]:
        if shutil.which("node"):
            code, out, err = run_cmd(["node", "--check", path])
            if code != 0:
                errors.append(f"Node V8 Syntax Error:\n{err or out}")

    # 3. TypeScript (.ts, .tsx)
    elif ext in [".ts", ".tsx"]:
        if shutil.which("tsc"):
            code, out, err = run_cmd([
                "tsc", "--noEmit", "--skipLibCheck", path
            ])
            if code != 0:
                errors.append(f"TypeScript Type/Syntax Error:\n{err or out}")

    # 4. Shell script (.sh, .bash)
    elif ext in [".sh", ".bash"]:
        code, out, err = run_cmd(["bash", "-n", path])
        if code != 0:
            errors.append(f"Bash Syntax Error:\n{err or out}")
        if shutil.which("shellcheck"):
            code, out, err = run_cmd(["shellcheck", "-s", "bash", path])
            if code != 0 and (out or err):
                errors.append(f"ShellCheck Error:\n{out or err}")

    # 5. JSON (.json)
    elif ext == ".json":
        code, out, err = run_cmd(["python3", "-m", "json.tool", path])
        if code != 0:
            errors.append(f"JSON Parse Error:\n{err or out}")

    # 6. YAML (.yaml, .yml)
    elif ext in [".yaml", ".yml"]:
        cmd = ["python3", "-c", f"import yaml; yaml.safe_load(open('{path}'))"]
        code, out, err = run_cmd(cmd)
        if code != 0 and "No module named" not in err:
            errors.append(f"YAML Syntax Error:\n{err or out}")

    if errors:
        return False, errors
    return True, [f"[PASS] {os.path.basename(path)} verified successfully."]

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 verify_code.py <file1> [file2...] | --dir <dir> | --git [repo_dir]")
        sys.exit(1)

    targets = []
    if sys.argv[1] == "--git":
        repo_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        code, out, _ = run_cmd(["git", "-C", repo_dir, "status", "--porcelain"])
        if code == 0 and out:
            for line in out.splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    fpath = os.path.join(repo_dir, parts[1])
                    ext = os.path.splitext(fpath)[1].lower()
                    if ext in [".py", ".js", ".ts", ".tsx", ".sh", ".bash", ".json", ".yaml", ".yml"]:
                        targets.append(fpath)
        if not targets:
            print("[OK] No modified code files detected in git.")
            sys.exit(0)
    elif sys.argv[1] == "--dir":
        search_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        skip_patterns = [".git", "node_modules", ".gemini", "dist", "build"]
        for root, _, files in os.walk(search_dir):
            if any(p in root for p in skip_patterns):
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".py", ".js", ".ts", ".tsx", ".sh", ".bash", ".json"]:
                    targets.append(os.path.join(root, f))
    else:
        targets = sys.argv[1:]

    all_passed = True
    for target in targets:
        ok, msgs = verify_file(target)
        for m in msgs:
            print(m)
        if not ok:
            all_passed = False

    if not all_passed:
        print("\n[FAIL] One or more verification checks failed.")
        sys.exit(1)
    else:
        print("\n[OK] All files verified clean with zero syntax or lint errors.")
        sys.exit(0)

if __name__ == "__main__":
    main()
