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

echo "Checking lazy.nvim + telescope"
[ -d "$DATA/lazy/lazy.nvim" ] && ok "lazy.nvim installed" || bad "lazy.nvim not found in $DATA/lazy" "bootstrap it (step 1) and restart nvim"
[ -d "$DATA/lazy/telescope.nvim" ] && ok "telescope installed" || bad "telescope.nvim not installed" "add it to the spec and restart"
[ "$(q 'pcall(require, "telescope")')" = true ] && ok "require('telescope') works" || bad "require('telescope') fails" "check :Lazy for errors"
f=$(q 'vim.fn.maparg("<leader>ff", "n") ~= "" or (vim.fn.maparg("<leader>ff", "n", false, true).callback ~= nil)'); [ "$f" = true ] && ok "<leader>ff mapped" || bad "<leader>ff not mapped" "step 2"
g=$(q 'next(vim.fn.maparg("<leader>fg", "n", false, true)) ~= nil'); [ "$g" = true ] && ok "<leader>fg mapped" || bad "<leader>fg not mapped" "step 2"
command -v rg >/dev/null && ok "ripgrep present" || bad "ripgrep missing" "apt install ripgrep, or brew install ripgrep"
e=$(startup_errors); [ -z "$e" ] && ok "clean startup" || bad "startup errors: $e"
finish
