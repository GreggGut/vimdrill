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

fq() { # fq <file> <lua-expr> [wait-ms]
  nvim --headless "$1" -c "lua vim.wait(${3:-300}, function() return false end); io.stdout:write(tostring($2))" -c 'qa!' 2>/dev/null
}

echo "Checking treesitter setup"
t=$(mktemp -d); printf 'int main(void) {\n  return 0;\n}\n' > "$t/a.c"; printf 'let x = 1\n' > "$t/a.vim"
[ "$(fq "$t/a.c" 'vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()] ~= nil')" = true ] \
  && ok "treesitter highlighting active in C files" || bad "no treesitter highlighting in a .c file" "FileType autocmd with vim.treesitter.start() (step 2)"
[ "$(fq "$t/a.vim" 'vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()] ~= nil')" = true ] \
  && ok "treesitter highlighting active in Vimscript files" || bad "no treesitter highlighting in a .vim file" "add 'vim' to the pattern"
[ "$(fq "$t/a.c" 'vim.wo.foldmethod')" = expr ] && ok "foldmethod=expr" || bad "foldmethod isn't expr" "vim.opt.foldmethod = 'expr'"
fq "$t/a.c" 'vim.wo.foldexpr' | grep -q 'treesitter' && ok "treesitter foldexpr" || bad "foldexpr isn't treesitter's" "vim.opt.foldexpr = 'v:lua.vim.treesitter.foldexpr()'"
l=$(fq "$t/a.c" 'vim.wo.foldlevel'); [ "${l:-0}" -ge 20 ] && ok "folds start open (foldlevel=$l)" || bad "foldlevel=${l:-0}: files open fully folded" "vim.opt.foldlevel = 99"
rm -rf "$t"
finish
