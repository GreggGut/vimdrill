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

echo "Checking your Lua config in $CFG"
[ -f "$CFG/init.lua" ] && ok "init.lua exists" || bad "no $CFG/init.lua" "create it (step 2)"
[ ! -f "$CFG/init.vim" ] && ok "init.vim is gone (no conflict)" || bad "init.vim still exists" "move it away (step 4)"
if [ -f "$CFG/init.lua" ]; then
  e=$(startup_errors); [ -z "$e" ] && ok "nvim starts without errors" || bad "startup errors: $e" "run nvim and read :messages"
  grep -qE '^[[:space:]]*vim\.(opt|o)\.[a-z]+' "$CFG/init.lua" && ok "init.lua sets options in Lua" || bad "no vim.opt / vim.o lines in init.lua" "step 2"
fi
finish
