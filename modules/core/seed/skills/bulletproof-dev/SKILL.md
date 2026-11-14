---
name: bulletproof-dev
description: >-
  Advanced autonomous software engineering harness for error-free, production-grade code.
  Implements the Architect-Coder-Auditor lifecycle, AST/type-safe verification,
  test-driven development (TDD), and zero-regression compiler validation loops.
---

# Bulletproof Autonomous Engineering Harness (`bulletproof-dev`)

> [!IMPORTANT]
> This skill governs code authoring, refactoring, and debugging. It enforces a deterministic,
> multi-stage engineering pipeline designed to eliminate hallucinations, syntax errors, regressions,
> and context-dilution errors when using fast models like Gemini Flash.

---

## 1. The Core Invariants (Zero Exceptions)

1. **Read-Before-Write Invariant:**
   - NEVER modify or reference an existing function, class, variable, or configuration without first viewing its exact definition, line numbers, and imports using file viewing tools.
   - Do not guess parameter names or argument positions.

2. **Micro-Surgical Editing Invariant:**
   - Always prefer targeted, contiguous replacements (`replace_file_content`) over full-file rewrites.
   - Preserves existing comments, license headers, spacing, and surrounding architecture.

3. **Compiler & Linter Gate (Zero-Blind-Commit):**
   - NEVER declare a code change complete without executing the language-specific syntax/linter gate:
     - **Python:** `python3 -m py_compile <file>` and `ruff check <file>`
     - **JavaScript:** `node --check <file>`
     - **TypeScript:** `tsc --noEmit --skipLibCheck <file>`
     - **Bash / Shell:** `bash -n <file>` and `shellcheck <file>`
     - **Java:** `javac -cp <classpath> <file>`
     - **Unified Gate:** `python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/verify_code.py <file>`
   - If a compiler, linter, or test fails, fix it immediately before proceeding.

4. **Test-Driven Verification (TDD):**
   - Write or identify a minimal verification test/harness *before* or alongside non-trivial functional changes.
   - Run the test to confirm failure (Red), apply the patch, and verify success (Green).

5. **Zero Knowledge Gap & Ground-Truth Invariant (Anti-Hallucination):**
   - **Never Rely on Offline Memory for External APIs:** Memory contains stale, deprecated, or hallucinated APIs from training cutoffs.
   - **Mandatory Live Verification:** Proactively check local package manifests (`package.json`, `requirements.txt`, etc.) and use `search_web` / `read_url_content` to inspect official current documentation for modern libraries and SDKs prior to writing code.
   - **Verify Every Import:** Every imported function, parameter, and method must be verified against current definitions.

6. **Complete Implementation Invariant (No Lazy Stubs):**
   - NEVER emit placeholder code, ellipses (`...`), stub comments (`// TODO`, `pass # to be done`), or partial functions.
   - Every authored piece of code must be 100% complete, fully implemented, and production-ready.

7. **Defensive Engineering & Robustness Invariant:**
   - Explicit input validation, boundary checking, and typed error handling for all external calls, I/O, and IPC.
   - No silent exception swallowing or unhandled promises.

---

## 2. The 3-Stage Engineering Lifecycle

When tackling non-trivial tasks (refactoring, multi-file features, architectural changes), execute the 3 stages:

```
[ Stage 1: Architect ]  -->  [ Stage 2: Coder ]  -->  [ Stage 3: Auditor ]
  • Map code & AST             • Surgical edits          • Run compiler/linters
  • Write interface contract   • Strict types/guards     • Test edge cases
  • Plan file touchpoints      • Minimal diffs           • Verify zero regressions
```

### Stage 1: Architect (Specification & Planning)
- Inspect the target files, dependencies, and configuration.
- Check imported versions (e.g. `package.json`, `requirements.txt`, `build.gradle`).
- Define the contract: function signatures, type annotations, and return types.
- Break the task into sequential, atomic modifications.

### Stage 2: Coder (Surgical Implementation)
- Execute targeted edits using `replace_file_content`.
- Add explicit defensive guards: null checks, exception handling, and parameter assertions.
- Match existing repository style, naming conventions, and lint standards.

### Stage 3: Auditor (Verification & Regression Gate)
- Run `verify_code.py` on all touched files.
- Run project build or unit test commands (`npm test`, `pytest`, `build.sh`, etc.).
- Inspect `git diff` to ensure no accidental whitespace bloat or unintended file modifications occurred.

---

## 3. Subagent Delegation Schema

For complex, multi-module features, invoke specialized subagents using `invoke_subagent`:

1. **`code-architect` (Role: Codebase Architect):**
   - Prompt: Research repository architecture, trace call graphs, and return a precise implementation specification.
2. **`bulletproof-coder` (Role: Surgical Implementer):**
   - Prompt: Implement the exact specification provided by the architect using targeted `replace_file_content` calls.
3. **`code-auditor` (Role: Quality & Security Auditor):**
   - Prompt: Review git diffs, run linters and test suites, test edge cases (null inputs, boundary conditions), and report verification status.

---

## 4. Ground-Truth & Verification Tool Suite

Antigravity includes a native suite of zero-hallucination tools:

```bash
# 1. AST Symbol Outliner (classes, functions, signatures without context bloat):
python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/ast_outline.py <file>

# 2. Ground-Truth Package & API Inspector (eliminates knowledge gaps):
python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/doc_lookup.py py <module> [member]
python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/doc_lookup.py node <package>
python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/doc_lookup.py project [dir]

# 3. Universal Multi-File Verification Gate:
python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/verify_code.py <file1> <file2>
python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/verify_code.py --git [repo_dir]
python3 /data/user/0/com.agy/files/.gemini/config/skills/bulletproof-dev/scripts/verify_code.py --dir <dir>

# 4. Native Standalone Linters:
ruff check --no-cache <file.py>
shellcheck <script.sh>
tsc --noEmit --skipLibCheck <file.ts>
node --check <file.js>
```
