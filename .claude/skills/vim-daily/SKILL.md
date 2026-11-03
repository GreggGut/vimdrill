---
name: vim-daily
description: Daily coached vim check-in for the vimdrill course. Checks today's drill passed, quizzes the user (today's lesson plus spaced review), applies the 80% gate that unlocks the next lesson, and syncs a tracker page if one is set up. Use when the user runs /vim-daily or asks for their vim quiz or check-in.
---

# /vim-daily

The user is working through vimdrill, a 12-week Vim course in Neovim. The `vimdrill` command owns all
state and rules. Never edit its state files by hand and never bend the gate: coached mode is strict
(under 80% repeats the lesson; a missed weekday resets the streak).

If `vimdrill` isn't on PATH, run it from the repo this skill lives in:
`$(dirname "$(readlink -f <this skill's base directory>)")/../../bin/vimdrill`, and tell the user once
that adding the repo's `bin` folder to PATH makes `vimdrill` work everywhere.

This is a short, friendly coach session, not an engineering task. Keep messages brief.

## 1. Check in

Run `vimdrill --state` and read it.

- `mode` is `self-paced`: run `vimdrill --mode coached` and tell the user in one line that /vim-daily
  is the coached course (daily graded quiz, 80% gate, streak); lessons whose drill they passed count
  as done, and `vimdrill --mode self-paced` switches back. Then run `vimdrill --state` again.
- `today_record.drill_passed` isn't true: tell them today's lesson (id + title), show the card from
  `vimdrill --show`, and tell them to run `vimdrill` in a terminal and come back. Stop. Do not quiz.
  (On weekends, say the drill is optional and offer the quiz only if they did the drill.)
- `today_record.quiz_taken` is true: they're done for today. Report streak and tomorrow's lesson, offer
  `vimdrill --mix` for extra practice (rounds mixed from the unlocked lessons; never counts),
  then go to step 4 (sync) and stop.
- Otherwise open with one line: streak, lesson, and keystrokes vs par from `today_record` if it has
  them (task lessons don't). If keys > 2x par, give one concrete hint for doing that drill in fewer keys.

## 2. Quiz

Run `vimdrill --quiz-pool`. Ask the 5 `current` questions and up to 5 `review` questions (review items
are past misses first, then random earlier material), mixed in order.

- Ask ONE question per message, plain text, numbered ("3/10"). Wait for the answer. Don't use the
  AskUserQuestion tool (multiple choice makes it too easy).
- Grade on meaning, not exact wording: any key sequence that does the job counts (`:120<CR>` and
  `120G` are both right). The stored `a` is the reference, not the only answer. "I don't know" is a miss.
- Arrow keys count the same as hjkl: treat ← ↓ ↑ → (or <Left> etc.) as equal to h j k l everywhere,
  e.g. `5↓`, `Ctrl-v 9↓`, `Ctrl-w →`. Never mark an answer wrong for using arrows. When `arrows` is
  true in `--state` (the user moves with the arrow keys), also write your own example answers with
  arrows.
- After each answer: ✅ or ❌ plus the correct answer in one line, with a one-line why when it's ❌.
- Track which ids were asked and which were missed.

## 3. Record

Score = correct / asked, rounded to 3 decimals. Run:

`vimdrill --record-quiz <score> --asked <id,id,...> --missed <id,id,...>`

(omit `--missed` if none). It prints JSON with `passed_gate`, `advanced_to` and `streak`. It refuses
if the drill hasn't passed or the quiz was already recorded; report the refusal and don't work around it.

- Passed: congratulate briefly, then show the next lesson card with `vimdrill --show` (tomorrow's
  lesson; they may start it today if they want).
- Failed: say they'll repeat the lesson tomorrow (for an edit drill, the repeat must come in at or
  under 1.5x par), and name the 1-2 concepts to revise. Suggest `vimdrill --mix` to practice them before tomorrow.

## 4. Sync the tracker page (only if one is set up)

1. `vimdrill --sync-files <a temporary directory>/vim-sync` prints the two file paths and `tracker_url`.
   If `tracker_url` is null, skip the rest of this step without mentioning it.
2. `ArtifactData` `list` with `collection: "progress"` on `tracker_url` to read the current `version`
   of the `summary` and `lessons` docs.
3. `ArtifactData` `batch` with two `set` writes: `{op: "set", collection: "progress", doc_id: "summary",
   file_path: <summary.json>, if_version: <version>}` and the same for `lessons` / `lessons.json`.
   Omit `if_version` for a doc that doesn't exist yet. If a pin fails, re-list and retry once.

End with one line: score, gate result, streak, and the tracker link if there is one.
