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

echo "Checking options and autocmds"
for o in relativenumber undofile smartcase splitright splitbelow; do
  [ "$(q "vim.o.$o")" = true ] && ok "$o" || bad "$o is off" "vim.opt.$o = true"
done
s=$(q 'vim.o.scrolloff'); [ "${s:-0}" -ge 4 ] && ok "scrolloff=$s" || bad "scrolloff is ${s:-0}" "vim.opt.scrolloff = 8"
y=$(q '#vim.api.nvim_get_autocmds({ event = "TextYankPost" })'); [ "${y:-0}" -ge 1 ] && ok "TextYankPost autocmd" || bad "no TextYankPost autocmd" "see step 2"
finish
