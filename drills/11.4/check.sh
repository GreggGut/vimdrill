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

echo "Checking completion and surround"
if grep -rqs 'vim.lsp.completion.enable' "$CFG" || [ -d "$DATA/lazy/blink.cmp" ]; then ok "completion configured"; else
  bad "no LSP completion setup found in $CFG" "step 1 (or install blink.cmp)"; fi
if [ -d "$DATA/lazy/nvim-surround" ] || [ -d "$DATA/lazy/mini.surround" ] || [ -d "$DATA/lazy/mini.nvim" ]; then
  s=$(q 'pcall(require, "nvim-surround") or pcall(require, "mini.surround")'); [ "$s" = true ] && ok "surround plugin loads" || bad "surround plugin installed but doesn't load" "check :Lazy"
else bad "no surround plugin installed" "add kylechui/nvim-surround to your lazy spec (step 2)"; fi
co=$(q 'vim.o.completeopt'); echo "$co" | grep -q menuone && ok "completeopt=$co" || bad "completeopt lacks menuone ($co)" "vim.opt.completeopt = { 'menuone', 'noselect', 'popup' }"
finish
