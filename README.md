# vimdrill

A 12-week course that teaches Vim in Neovim, one short lesson a day. Each of the 60 lessons has a
lesson card, a hands-on drill scored by keystrokes against par, and quiz questions. `vimdrill --mix`
generates fresh practice rounds from the lessons you've done.

| Week | Topic | Week | Topic |
|---|---|---|---|
| 1 | Moving in big steps | 7 | Macros |
| 2 | Operator grammar (`d`, `c`, `y`, counts, `.`) | 8 | Ex power (`:g`, `:normal`, `:sort`, filters) |
| 3 | Precision (`f`/`t`, text objects) | 9 | Buffers, windows, tabs, many files |
| 4 | Search and substitute | 10 | Make it yours: `init.lua`, mappings, plugins |
| 5 | Visual mode | 11 | Neovim as an IDE: treesitter, LSP, completion |
| 6 | Registers and marks | 12 | Fluency: real-world edits, your own cheat sheet |

It works on its own, in the terminal. With [Claude Code](https://claude.com/claude-code) you can also
take it as a coached course, with a daily graded quiz.

## Install

You need Python 3.10+, Neovim 0.11+ and bash, on Linux, macOS or WSL on Windows. No Python packages.

```sh
git clone https://github.com/GreggGut/vimdrill.git ~/vimdrill-course
echo 'export PATH="$HOME/vimdrill-course/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
```

Clone it anywhere except `~/vimdrill`: that's where the files you write in lessons go (see
[Your files](#your-files)).

Optional, for zsh: a one-line status in every new terminal, so you don't forget today's lesson.

```sh
echo 'source ~/vimdrill-course/nudge.zsh' >> ~/.zshrc
```

Weeks 10 and 11 set up your own Neovim config. They also need git, ripgrep, a C compiler (e.g. gcc,
for treesitter parsers) and Node.js with npm (for the TypeScript language server).

## Learn on your own (self-paced)

This is where everyone starts. Every lesson is open.

```sh
vimdrill --show        # read the lesson card: the keys to learn and a tip
vimdrill               # run the drill of the first lesson you haven't passed yet
vimdrill --quiz        # test yourself on it: answer, see the answer, mark yourself
```

| Command | What it does |
|---|---|
| `vimdrill <id>` | Run any lesson's drill, e.g. `vimdrill 4.2` |
| `vimdrill --show [id]` | Print a lesson card |
| `vimdrill --quiz [id]` | Self-check quiz: 5 questions on the lesson plus up to 5 review questions. Questions you miss come back in later quizzes until you get them right twice. Nothing is gated. |
| `vimdrill --mix` | 4 freshly generated rounds from the lessons you've passed and the one you're on |
| `vimdrill --mix --all` | The same, from every lesson |
| `vimdrill --review` | Replay a random drill you've passed |
| `vimdrill --check [id]` | Check a setup task (the config lessons in weeks 10 and 11) |
| `vimdrill --status` | One-line status |

## Coached, with Claude Code

The `/vim-daily` skill turns the course into a daily routine with a coach:

1. Run `vimdrill` to pass today's drill.
2. Run `/vim-daily` in Claude Code. It quizzes you on today's lesson plus review questions (10 in all),
   one at a time, and grades your answers.
3. 80% (8 of 10) unlocks the next lesson. Below that, you repeat the lesson the next day, and the repeat
   drill must come in at or under 1.5 times par.

Your streak counts weekdays with both a drill and a quiz. Weekends never break it; a missed weekday
resets it. Lessons unlock one at a time, so `vimdrill <id>` and `--mix` only use what you've unlocked.

The skill is in `.claude/skills/vim-daily` and loads automatically when you start Claude Code inside
the clone. To use `/vim-daily` from anywhere:

```sh
ln -s ~/vimdrill-course/.claude/skills/vim-daily ~/.claude/skills/vim-daily
```

The first `/vim-daily` switches you to coached mode. Lessons whose drill you've passed count as done,
and you start at the first one you haven't. `vimdrill --mode self-paced` switches back, keeping all
your progress. If you move with the arrow keys instead of hjkl, run `vimdrill --arrows on`, and the
coach writes its examples with arrows. Arrows are always accepted as answers either way.

## How drills work

A drill opens Neovim with the instructions at the top, your file on the left and the target on the
right, with the differences highlighted. Edit until your file matches the target, then save and quit
with `:wqa`.

Every key you press counts, including the `:wqa<CR>`. **Par** is the keystroke count of a good
solution. You pass when the file matches; at or under par is the goal. More than twice par means
there's a shorter way: re-read the lesson card.

Most `--mix` rounds are generated, so each one is new. When you're over par on one, it shows the par
route next to yours. Some rounds ask for a specific key, such as `gi`, and only pass if you used it.

The setup lessons in weeks 10 and 11 are tasks rather than edits: you change your own Neovim config,
then `vimdrill --check` tests the result.

## Your files

- Progress: `~/.local/state/vimdrill/` (or `$XDG_STATE_HOME/vimdrill`). Set `VIMDRILL_HOME` to use
  another folder.
- Files you create in lessons (a practice project, your cheat sheet): `~/vimdrill/`. Set
  `VIMDRILL_WORK` to use another folder.

Nothing is written inside the clone, so `git pull` updates the course safely.

## For contributors

Drills are written in `src/week*.drills.json`; `tools/make_drills.py src/weekNN.drills.json`
regenerates `drills/`. `tools/verify_drills.py` replays every drill's solution in headless Neovim and
checks that it reaches the target (`--mix N` also checks N generated rounds per lesson). Lesson cards
and quiz questions live in `curriculum/`.

## License

[MIT](LICENSE)
