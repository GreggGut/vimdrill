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

echo "Checking mappings"
[ "$(q 'vim.g.mapleader')" = " " ] && ok "leader is Space" || bad "mapleader isn't ' '" "vim.g.mapleader = ' ' at the top of init.lua"
w=$(q 'vim.fn.maparg("<leader>w", "n")'); echo "$w" | grep -qi 'w' && ok "<leader>w -> $w" || bad "no <leader>w mapping" "vim.keymap.set('n', '<leader>w', '<cmd>write<CR>')"
x=$(q 'vim.fn.maparg("<leader>q", "n")'); [ -n "$x" ] && ok "<leader>q -> $x" || bad "no <leader>q mapping"
e=$(q 'vim.fn.maparg("<Esc>", "n")'); echo "$e" | grep -qi 'noh' && ok "<Esc> clears search highlight" || bad "<Esc> doesn't run :nohlsearch" "vim.keymap.set('n', '<Esc>', '<cmd>nohlsearch<CR>')"
n=$(q '#vim.tbl_filter(function(m) return m.lhs:sub(1,1) == " " end, vim.api.nvim_get_keymap("n"))')
[ "${n:-0}" -ge 3 ] && ok "$n leader mappings" || bad "only ${n:-0} leader mapping(s)" "add your own in step 3 (a non-leader one is fine too, it just isn't counted here)"
finish
