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

echo "Checking LSP"
if command -v tsc >/dev/null; then
  v=$(tsc --version 2>/dev/null | grep -o '[0-9][0-9.]*' | head -1)
  [ "${v%%.*}" -ge 7 ] 2>/dev/null && ok "tsc $v (has --lsp)" \
    || printf '  - tsc %s has no --lsp: fine if typescript-language-server attaches instead (step 5)\n' "$v"
else
  printf '  - tsc not found: fine if another TypeScript server attaches (step 5)\n'
fi
t=$(mktemp -d); echo '{}' > "$t/package.json"; printf 'const n: number = 1;\nexport { n };\n' > "$t/a.ts"
out=$(cd "$t" && nvim --headless a.ts -c 'lua vim.wait(20000, function() return #vim.lsp.get_clients({ bufnr = 0 }) > 0 end, 200); local c = vim.lsp.get_clients({ bufnr = 0 }); io.stdout:write("CLIENT=" .. (#c > 0 and c[1].name or "none"))' -c 'qa!' 2>&1)
rm -rf "$t"
c=$(printf '%s' "$out" | grep -o 'CLIENT=[^ ]*' | cut -d= -f2)
err=$(printf '%s' "$out" | grep -o 'message = "[^"]*' | head -1 | cut -c12-)
[ -n "$c" ] && [ "$c" != none ] && ok "a language server ($c) attaches to .ts files" \
  || bad "no LSP client attached to a .ts file within 20s${err:+ - server said: $err}" "steps 2-3, then :checkhealth vim.lsp in a .ts file"
finish
