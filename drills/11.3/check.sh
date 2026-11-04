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

P=${VIMDRILL_WORK:-$HOME/vimdrill}/practice/11.3
if [ ! -d "$P" ]; then
  mkdir -p "$P/src"
  cat > "$P/package.json" <<'JSON'
{ "name": "lsp-drill", "private": true }
JSON
  cat > "$P/tsconfig.json" <<'JSON'
{ "compilerOptions": { "strict": true, "target": "ES2020", "noEmit": true }, "include": ["src"] }
JSON
  cat > "$P/src/cart.ts" <<'TS'
export interface Item {
  name: string;
  price: number;
  qty: number;
}

export function calc(items: Item[]): number {
  return items.reduce((sum, item) => sum + item.price * item.qty, 0);
}

export function formatPrice(value: number): string {
  return `$${value.toFixed(2)}`;
}
TS
  cat > "$P/src/main.ts" <<'TS'
import { Item, calc } from "./cart";

const items: Item[] = [
  { name: "coffee", price: 4.5, qty: 2 },
  { name: "bagel", price: 3, qty: 1 },
];

const total: string = calc(items);
console.log(formatPrice(total));
TS
  echo "Created the practice project in $P. Follow steps 1-7, then run vimdrill --check again."
  exit 1
fi
echo "Checking $P"
grep -qw 'calc' "$P/src/cart.ts" "$P/src/main.ts" && bad "'calc' still exists" "grn on calc in cart.ts (step 5)" || ok "calc renamed"
grep -q 'function calculateTotal' "$P/src/cart.ts" && grep -q 'calculateTotal(items)' "$P/src/main.ts" \
  && ok "calculateTotal defined and used" || bad "calculateTotal missing in cart.ts or main.ts" "rename with grn, then :wa"
grep -E '^import .*formatPrice.*from "\./cart"|^import .*formatPrice.*from '"'"'\./cart'"'" "$P/src/main.ts" >/dev/null \
  && ok "formatPrice imported" || bad "formatPrice not imported" "gra on formatPrice -> Add import (step 3)"
grep -q 'total: number' "$P/src/main.ts" && ok "total is a number" || bad "total still has the wrong type" "step 4"
if command -v tsc >/dev/null; then
  (cd "$P" && tsc -p . >/tmp/vimdrill-tsc.$$ 2>&1) && ok "tsc: no type errors" || bad "tsc reports errors: $(head -3 /tmp/vimdrill-tsc.$$)" "]d / Ctrl-w d to find them"
  rm -f /tmp/vimdrill-tsc.$$
fi
finish
