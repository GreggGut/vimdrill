#!/usr/bin/env bash
# --- shared helpers (read-only checks) ---
fail=0
ok()  { printf '  \033[32m✔\033[0m %s\n' "$1"; }
bad() { printf '  \033[31m✘\033[0m %s\n' "$1"; [ -n "$2" ] && printf '      → %s\n' "$2"; fail=1; }
# q 'lua expression' : evaluate with your real config, print the result
q() { nvim --headless -c "lua io.stdout:write(tostring($1))" -c 'qa!' 2>/dev/null; }
CFG=$(nvim --headless --clean -c 'lua io.stdout:write(vim.fn.stdpath("config"))' -c 'qa!' 2>/dev/null)
DATA=$(nvim --headless --clean -c 'lua io.stdout:write(vim.fn.stdpath("data"))' -c 'qa!' 2>/dev/null)
startup_errors() { nvim --headless -c 'qa!' 2>&1 | grep -iE 'error|E[0-9]{3,4}:' | head -5; }
finish() { if [ $fail -eq 0 ]; then echo "All checks passed."; exit 0; else echo "Not done yet - fix the ✘ items and run: vimdrill --check"; exit 1; fi; }
# ---

F=${VIMDRILL_WORK:-$HOME/vimdrill}/cheatsheet.md
if [ ! -f "$F" ]; then bad "no $F yet" "nvim $F, then :w ++p"; finish; fi
n=$(grep -c '[^[:space:]]' "$F")
[ "$n" -ge 40 ] && ok "$n non-empty lines" || bad "only $n non-empty lines (need 40)" "keep writing"
s=$(grep -c '^#' "$F"); [ "$s" -ge 3 ] && ok "$s section headings" || bad "fewer than 3 headings (# ...)" "group it into sections"
finish
