# Copilot Instructions / Repository Language Policy

## Primary Rule: English Only
All newly added or modified content MUST be written in English:
- Source code (Python, shell scripts, service files, desktop entries, udev rules, etc.)
- Inline code comments and docstrings
- Configuration file keys and values (unless they are fixed system paths)
- Commit messages / pull request titles & descriptions
- Documentation (README additions, HOWTOs)
- Variable / function / class names

## Exceptions (allowed to stay non-English only if already present)
- Existing historical German strings in user-visible UI messages may remain temporarily, but SHOULD be progressively migrated to English.
- System paths or hardware identifiers (e.g. `/sys/class/backlight`, `evdev`) remain unchanged.

## UI / User-Facing Text
Prefer English for all GUI labels, dialog titles, and messages. If localization is ever introduced, implement a proper i18n mechanism rather than mixing languages inline.

## Comment & Docstring Style
- Be concise, action-oriented, and technical.
- Use full sentences for docstrings; fragments are acceptable for short inline comments.
- Avoid redundant comments that restate obvious code.

Bad example:
```python
# Set variable x to 1
x = 1
```
Good example:
```python
# Reset inactivity timer (user interaction detected)
last_event_ts = now
```

## Naming Conventions
- Descriptive, explicit names (e.g. `rescan_devices`, not `doScan`).
- Constants: UPPER_SNAKE_CASE
- Functions / variables: lower_snake_case
- Classes (if added): PascalCase

## Commit Message Format
```
<type>: <short imperative summary>

Optional longer body explaining reasoning (wrap ~72 chars)
```
Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `perf`, `test`, `build`.

Examples:
```
fix: prevent brightness write failure when device disappears
feat: add optional user-level systemd unit variant
```

## Python Specific
- Prefer explicit imports.
- Avoid unused imports and trailing whitespace.
- Keep functions short & single-purpose.
- Use f-strings for string interpolation.

## Shell Script Specific
- Use `#!/usr/bin/env bash` and `set -euo pipefail` (already standard here).
- Prefer explicit paths (`/usr/bin/systemctl`).
- Quote all variable expansions unless intentional globbing.

## Error Messages
- Clear, actionable, English.
- Mention remediation if non-obvious.

Example:
```
ERROR: Could not write brightness (permission denied). Ensure user is in group 'video'.
```

## AI Assistant Guidance
When generating or modifying code:
1. Produce English-only code & comments.
2. Do not introduce German text in new revisions.
3. If you encounter German legacy strings, you MAY refactor them to English in the same change if it does not obscure the functional intent.
4. Prefer minimal diffs—only change language where needed, avoid gratuitous rewrites.

## Migration Plan (Optional)
If desired later: create an issue "Migrate remaining German UI strings to English" and perform incremental cleanups.

---
Enforcement: Pull requests not following this policy should be revised before merge.

