# Shows today's vim drill status in every new interactive terminal.
# Skipped inside Claude Code tool shells and non-interactive shells.
if [[ -o interactive && -t 1 && -z "$CLAUDECODE" ]]; then
  vimdrill --status 2>/dev/null
fi
