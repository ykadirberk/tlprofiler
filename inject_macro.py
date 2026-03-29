#!/usr/bin/env python3
"""
inject_macro.py

Injects a macro call as the first statement in every C++ function body,
and adds a #include for the macro's header file to each modified .cpp file.

Usage:
    python inject_macro.py --folder <folder> --macro <macro_call> --header <header_file> [--dry-run] [--no-recurse]

Options:
    --folder      Root folder to search for .cpp files
    --macro       Macro invocation to inject, e.g. "MY_MACRO()" or "TRACE(__FUNCTION__)"
    --header      Header filename to #include,  e.g. "trace.h" or "profiler/trace.h"
    --dry-run     Show a preview of every injection site without writing files
    --no-recurse  Only search the given folder, not subdirectories

Examples:
    python inject_macro.py --folder ./src --macro "MY_TRACE()" --header "my_trace.h"
    python inject_macro.py --folder ./src --macro "PROFILE(__FUNCTION__)" --header "profiler.h" --dry-run
"""

import sys
import argparse
from pathlib import Path


# These keywords introduce blocks that are NOT function bodies
BLOCK_KEYWORDS = frozenset({
    'if', 'else', 'for', 'while', 'do', 'switch',
    'try', 'catch', 'finally',
    'namespace', 'class', 'struct', 'union', 'enum',
    '__if_exists', '__if_not_exists',
})

# Qualifiers that may appear between the closing ')' and '{' of a function
TRAILING_QUALIFIERS = frozenset({
    'const', 'volatile', 'override', 'final',
    'noexcept', 'mutable', 'abstract',
})


# ---------------------------------------------------------------------------
# Step 1 – strip comments and string/char literals
# ---------------------------------------------------------------------------

def blank_non_code(source: str) -> str:
    """
    Return a copy of source where all comment and string/char literal content
    is replaced with spaces.  Newlines are preserved so line numbers stay valid.
    """
    result = list(source)
    i, n = 0, len(source)

    while i < n:
        # Line comment  //...
        if source[i:i+2] == '//':
            j = source.find('\n', i)
            j = j if j != -1 else n
            for k in range(i, j):
                result[k] = ' '
            i = j

        # Block comment  /*...*/
        elif source[i:i+2] == '/*':
            j = source.find('*/', i + 2)
            j = j + 2 if j != -1 else n
            for k in range(i, j):
                if result[k] != '\n':
                    result[k] = ' '
            i = j

        # Raw string literal  R"delim(...)delim"
        elif source[i] == 'R' and i + 1 < n and source[i+1] == '"':
            j = i + 2
            while j < n and source[j] != '(':
                j += 1
            end_delim = ')' + source[i+2:j] + '"'
            j += 1  # skip the opening '('
            end = source.find(end_delim, j)
            end = end + len(end_delim) if end != -1 else n
            for k in range(i, end):
                if result[k] != '\n':
                    result[k] = ' '
            i = end

        # String literal  "..."
        elif source[i] == '"':
            result[i] = ' '
            j = i + 1
            while j < n:
                if source[j] == '\\':
                    result[j] = ' '
                    j += 1
                    if j < n:
                        result[j] = ' '
                elif source[j] == '"':
                    result[j] = ' '
                    j += 1
                    break
                else:
                    if source[j] != '\n':
                        result[j] = ' '
                j += 1
            i = j

        # Char literal  '.'
        elif source[i] == "'":
            result[i] = ' '
            j = i + 1
            while j < n:
                if source[j] == '\\':
                    result[j] = ' '
                    j += 1
                    if j < n:
                        result[j] = ' '
                elif source[j] == "'":
                    result[j] = ' '
                    j += 1
                    break
                else:
                    if source[j] != '\n':
                        result[j] = ' '
                j += 1
            i = j

        else:
            i += 1

    return ''.join(result)


# ---------------------------------------------------------------------------
# Step 2 – helpers for walking backwards through stripped source
# ---------------------------------------------------------------------------

def skip_back(s: str, i: int) -> int:
    """Move i leftward past whitespace. Returns the new position."""
    while i >= 0 and s[i] in ' \t\r\n':
        i -= 1
    return i


def read_word_back(s: str, i: int):
    """
    Read an identifier/keyword leftward from position i (inclusive).
    Returns (word, new_i) where new_i is just before the first character of the word.
    """
    end = i + 1
    while i >= 0 and (s[i].isalnum() or s[i] == '_'):
        i -= 1
    return s[i+1:end], i


def skip_balanced_back(s: str, i: int, close: str, open_: str) -> int:
    """
    Starting at position i which must hold `close`, walk left to the matching
    `open_` and return the position just before it.
    """
    assert s[i] == close
    depth = 1
    i -= 1
    while i >= 0 and depth > 0:
        if s[i] == close:
            depth += 1
        elif s[i] == open_:
            depth -= 1
        i -= 1
    return i  # one position before the matching open_


# ---------------------------------------------------------------------------
# Step 3 – decide whether a '{' opens a function body
# ---------------------------------------------------------------------------

def is_function_brace(stripped: str, pos: int) -> bool:
    """
    Heuristic: return True when the '{' at `pos` is the opening brace of a
    function/method/constructor/destructor/lambda body.

    Walks backwards past:
      - whitespace
      - trailing qualifiers  (const / override / final / noexcept / volatile …)
      - noexcept(expr)
      - constructor initializer lists   : mem1(v), mem2(v)
      - try keyword (function-try-block)
    until it finds ')' closing the parameter list, then checks that the token
    immediately before '(' is not a control-flow keyword.
    """
    i = skip_back(stripped, pos - 1)
    if i < 0:
        return False

    iterations = 0

    while i >= 0 and iterations < 400:
        iterations += 1
        c = stripped[i]

        # ---- found the closing ')' of some paren group ----
        if c == ')':
            new_i = skip_balanced_back(stripped, i, ')', '(')
            before_open = skip_back(stripped, new_i)
            if before_open < 0:
                return False

            bc = stripped[before_open]

            # Identifier before '('
            if bc.isalnum() or bc == '_':
                word, _ = read_word_back(stripped, before_open)
                if word == 'noexcept':
                    # noexcept(expr) is a qualifier — keep searching for ')'
                    i = skip_back(stripped, new_i)
                    continue
                if word in BLOCK_KEYWORDS:
                    return False
                # Looks like a real function name
                return True

            # operator>>  /  operator[]  /  ~Destructor
            if bc in ('>', ']', '~'):
                return True

            # Chained call: foo()()  — treat as function
            if bc == ')':
                return True

            return False

        # ---- whitespace ----
        elif c in ' \t\r\n':
            i -= 1

        # ---- word token ----
        elif c.isalnum() or c == '_':
            word, new_i = read_word_back(stripped, i)
            if word in BLOCK_KEYWORDS:
                return False
            if word == 'try':
                # function-try-block:  void f() try { ... }
                i = skip_back(stripped, new_i)
                continue
            if word in TRAILING_QUALIFIERS:
                i = skip_back(stripped, new_i)
                continue
            # Part of trailing return type or initializer list — skip over it
            i = new_i
            i = skip_back(stripped, i)

        # ---- ref / pointer / destructor decorators ----
        elif c in '&*~':
            i -= 1

        # ---- constructor initializer-list separator or scope operator ----
        elif c == ':':
            i -= 1

        elif c == ',':
            i -= 1

        # ---- trailing return type '->' or template '>' ----
        elif c in ('-', '>'):
            i -= 1

        # ---- = delete / = default / = 0  →  NOT a function body ----
        elif c == ';':
            return False

        elif c == '=':
            return False

        else:
            return False

    return False


# ---------------------------------------------------------------------------
# Step 4 – injection helpers
# ---------------------------------------------------------------------------

def first_token_after_brace(source: str, brace_pos: int) -> str:
    """Return the first non-whitespace identifier token after '{' (for idempotency check)."""
    i = brace_pos + 1
    n = len(source)
    while i < n and source[i] in ' \t\r\n':
        i += 1
    if i >= n:
        return ''
    if source[i].isalnum() or source[i] == '_':
        j = i
        while j < n and (source[j].isalnum() or source[j] == '_'):
            j += 1
        return source[i:j]
    return source[i]


def body_indent(source: str, brace_pos: int) -> str:
    """
    Determine the indentation string for the line being injected.
    Prefers the actual indentation of the first line of the body;
    falls back to brace-line-indent + 4 spaces.
    """
    n = len(source)

    # Indentation of the line containing '{'
    ls = source.rfind('\n', 0, brace_pos)
    ls = 0 if ls == -1 else ls + 1
    brace_line_indent = ''
    k = ls
    while k < brace_pos and source[k] in ' \t':
        brace_line_indent += source[k]
        k += 1

    # Look at the next line's indentation
    nl = source.find('\n', brace_pos)
    if nl != -1 and nl + 1 < n:
        p = nl + 1
        candidate = ''
        while p < n and source[p] in ' \t':
            candidate += source[p]
            p += 1
        if len(candidate) > len(brace_line_indent):
            return candidate

    return brace_line_indent + '    '


def collect_injection_sites(source: str, macro_name: str):
    """
    Return a list of (brace_pos, line_number) for every function-opening '{'
    that does not already have the macro injected.  Line numbers are 1-based.
    """
    stripped = blank_non_code(source)
    # Build a position → line-number map lazily via cumulative newline count
    sites = []
    line = 1
    prev = 0
    newlines = [i for i, c in enumerate(source) if c == '\n']
    nl_idx = 0

    for pos, ch in enumerate(stripped):
        if ch == '{' \
                and is_function_brace(stripped, pos) \
                and first_token_after_brace(source, pos) != macro_name:
            # Compute 1-based line number for this position
            while nl_idx < len(newlines) and newlines[nl_idx] < pos:
                nl_idx += 1
            sites.append((pos, nl_idx + 1))  # nl_idx+1 == line number of brace

    return sites


# ---------------------------------------------------------------------------
# Step 5 – dry-run preview
# ---------------------------------------------------------------------------

def find_signature_start(lines: list, brace_idx: int) -> int:
    """
    Walk backward from brace_idx to find the first line of the function signature.
    Stops at an empty line or a line ending with ; { } (end of a previous construct).
    Returns a 0-based line index.
    """
    idx = brace_idx - 1
    while idx >= 0:
        stripped = lines[idx].strip()
        if not stripped:
            return idx + 1
        if stripped.endswith((';', '{', '}')):
            return idx + 1
        if stripped.startswith('#'):
            return idx + 1
        idx -= 1
    return 0


def find_first_body_line(lines: list, brace_idx: int) -> int:
    """Return the 0-based index of the first non-empty line after the brace line."""
    idx = brace_idx + 1
    while idx < len(lines):
        if lines[idx].strip():
            return idx
        idx += 1
    return brace_idx + 1


def show_preview(path: Path, source: str, sites: list, macro_call: str, indent_map: dict) -> None:
    """Print a contextual diff-style preview for the given injection sites."""
    if not sites:
        return

    lines = source.splitlines()
    total = len(lines)
    print(f"\n=== {path}  [{len(sites)} injection(s)] ===")

    for brace_pos, brace_line_no in sites:
        indent = indent_map[brace_pos]
        injected_line = indent + macro_call
        brace_idx = brace_line_no - 1

        sig_start  = find_signature_start(lines, brace_idx)
        body_idx   = find_first_body_line(lines, brace_idx)
        max_ln     = body_idx + 1
        w          = len(str(max_ln))

        # Signature lines (from return type / function name down to the opening brace)
        for idx in range(sig_start, brace_idx + 1):
            print(f"  {idx+1:{w}} |   {lines[idx]}")

        # Injected macro line
        print(f"  {'+':{w}} | + {injected_line}")

        # First non-empty body line
        if body_idx < total:
            print(f"  {body_idx+1:{w}} |   {lines[body_idx]}")

        print()


# ---------------------------------------------------------------------------
# Step 6 – process a single file
# ---------------------------------------------------------------------------

def inject_macro_in_source(source: str, macro_call: str, header: str,
                            dry_run: bool, path: Path) -> str:
    """
    In normal mode: return modified source with macro injected and #include added.
    In dry-run mode: print the preview and return the original source unchanged.
    Idempotent: a second run on an already-modified file makes no further changes.
    """
    macro_name = macro_call.split('(')[0].strip()
    sites = collect_injection_sites(source, macro_name)

    # Pre-compute indentation for each site (needed for both preview and injection)
    indent_map = {brace_pos: body_indent(source, brace_pos) for brace_pos, _ in sites}

    if dry_run:
        show_preview(path, source, sites, macro_call, indent_map)
        return source  # no changes in dry-run

    if not sites:
        return source

    # Insert in reverse order so earlier positions stay valid
    chars = list(source)
    for brace_pos, _ in reversed(sites):
        indent = indent_map[brace_pos]
        injection = '\n' + indent + macro_call
        chars[brace_pos+1:brace_pos+1] = list(injection)

    modified = ''.join(chars)

    # Add #include if not already present in any form
    include_quoted = f'#include "{header}"'
    include_angle  = f'#include <{header}>'

    if include_quoted not in modified and include_angle not in modified:
        lines = modified.split('\n')

        last_include = -1
        for idx, line in enumerate(lines):
            if line.strip().startswith('#include'):
                last_include = idx

        if last_include >= 0:
            lines.insert(last_include + 1, include_quoted)
        else:
            # No existing includes — insert after any leading file-header comment
            insert_at = 0
            in_block = False
            for idx, line in enumerate(lines):
                s = line.strip()
                if in_block:
                    insert_at = idx + 1
                    if '*/' in s:
                        in_block = False
                elif s.startswith('/*'):
                    in_block = True
                    insert_at = idx + 1
                    if '*/' in s:
                        in_block = False
                elif s.startswith('//') or s == '':
                    insert_at = idx + 1
                else:
                    break
            lines.insert(insert_at, include_quoted)

        modified = '\n'.join(lines)

    return modified


# ---------------------------------------------------------------------------
# Step 7 – walk the folder
# ---------------------------------------------------------------------------

def process_folder(folder: str, macro_call: str, header: str,
                   dry_run: bool = False, recursive: bool = True) -> None:
    root = Path(folder)
    if not root.is_dir():
        sys.exit(f"Error: '{folder}' is not a directory.")

    files = sorted(root.rglob('*.cpp') if recursive else root.glob('*.cpp'))

    if not files:
        print(f"No .cpp files found in '{folder}'.")
        return

    modified_count = 0
    for path in files:
        try:
            original = path.read_text(encoding='utf-8', errors='replace')
        except Exception as exc:
            print(f"  SKIP (read error): {path}: {exc}")
            continue

        new_source = inject_macro_in_source(original, macro_call, header, dry_run, path)

        if dry_run:
            # Preview already printed inside inject_macro_in_source
            continue

        if new_source != original:
            modified_count += 1
            path.write_text(new_source, encoding='utf-8')
            print(f"Modified : {path}")
        else:
            print(f"Unchanged: {path}")

    if not dry_run:
        print(f"\nModified {modified_count} of {len(files)} file(s).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def strip_quotes(value: str) -> str:
    """Strip a single layer of surrounding single or double quotes if present."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Inject a macro as the first statement in every C++ function body.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--folder',      required=True, help='Folder to search for .cpp files')
    parser.add_argument('--macro',       required=True, help='Macro invocation, e.g. "MY_MACRO()" or "TRACE(__FUNCTION__)"')
    parser.add_argument('--header',      required=True, help='Header to #include, e.g. "trace.h"')
    parser.add_argument('--dry-run',     action='store_true', help='Show injection preview without writing files')
    parser.add_argument('--no-recurse',  action='store_true', help='Do not recurse into subdirectories')
    args = parser.parse_args()

    process_folder(
        folder=strip_quotes(args.folder),
        macro_call=strip_quotes(args.macro),
        header=strip_quotes(args.header),
        dry_run=args.dry_run,
        recursive=not args.no_recurse,
    )


if __name__ == '__main__':
    main()
