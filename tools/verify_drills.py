#!/usr/bin/env python3
"""Verify every drill: replay its solution in headless nvim and compare with target.

Runs each edit drill twice: with --clean and with the user's own config,
so a drill is solvable in both. Also validates curriculum/drill consistency.

  python3 tools/verify_drills.py [lesson-id ...]
  python3 tools/verify_drills.py --mix N [lesson-id ...]   replay N generated rounds per generator
"""
import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("vimdrill", str(ROOT / "bin" / "vimdrill"))
spec = importlib.util.spec_from_loader("vimdrill", loader)
vd = importlib.util.module_from_spec(spec)
loader.exec_module(vd)

FEED = vd.SCREEN_LUA + r"""
local h = tonumber(vim.env.VM_SCREEN or '')
if h then
  vim.o.lines = h + 10
  assert(VM_screen(0, h), 'could not size the window')
end
vim.cmd('normal! gg0')  -- vimdrill's layout starts every drill here
local keys = vim.fn.readfile(vim.env.VM_SOLUTION, 'b')
keys = table.concat(keys, '\n')
local ok, err = pcall(vim.api.nvim_feedkeys, vim.api.nvim_replace_termcodes(keys, true, false, true), 'xt', false)
if not ok then io.stderr:write('feedkeys error: ' .. tostring(err) .. '\n') end
vim.cmd('silent! wall')
vim.cmd('qa!')
"""


def replay(lid, drill, clean, src=None):
    src = src or vd.drill_dir(lid)
    work = Path(tempfile.mkdtemp(prefix=f"verify-{lid}-"))
    shutil.copytree(src / "start", work, dirs_exist_ok=True)
    sol = work.parent / (work.name + ".sol")
    sol.write_text(drill["solution"])
    feed = work.parent / (work.name + ".lua")
    feed.write_text(FEED)
    cmd = ["nvim", "--headless"] + (["--clean"] if clean else []) + \
          ["-n", *drill.get("open", ["main.txt"]), "-c", f"luafile {feed}"]
    env = {**__import__("os").environ, "VM_SOLUTION": str(sol)}
    if drill.get("screen"):
        env["VM_SCREEN"] = str(drill["screen"])
    res = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=30)
    bad = vd.compare_dirs(work, src / "target")
    detail = ""
    if bad:
        f = bad[0]
        got = (work / f).read_text() if (work / f).exists() else "<missing>"
        detail = f"\n--- got {f} ---\n{got}\n--- expected ---\n{(src / 'target' / f).read_text()}"
    shutil.rmtree(work)
    sol.unlink()
    feed.unlink()
    return bad, (res.stderr.strip() + detail)


def verify_mix(n, only):
    sys.path.insert(0, str(ROOT / "bin"))
    import mixgen
    problems = 0
    for lid, gen in mixgen.GENERATORS.items():
        if only and lid not in only:
            continue
        pars = []
        for seed in range(n):
            spec = gen(__import__("random").Random(seed))
            src = Path(tempfile.mkdtemp(prefix=f"verify-mix-{lid}-"))
            drill = vd.write_spec(spec, src)
            if spec["start"] == spec["target"]:
                print(f"{lid} seed {seed}: start == target"); problems += 1
            for clean in (True, False):
                bad, err = replay(lid, drill, clean, src)
                if bad:
                    problems += 1
                    print(f"{lid} seed {seed}: FAIL ({'clean' if clean else 'user-config'}) {err}")
                    print("solution:", drill["solution"])
            shutil.rmtree(src)
            pars.append(vd.par(drill))
        print(f"{lid}: {n} seeds, par {min(pars)}-{max(pars)}")
    print(f"\n{problems} problem(s)")
    sys.exit(1 if problems else 0)


def main(only):
    lessons = vd.load_curriculum()
    ids = [l["id"] for l in lessons]
    problems = 0
    if len(ids) != len(set(ids)):
        print("DUPLICATE lesson ids"); problems += 1
    qids = [q["id"] for l in lessons for q in l["quiz"]]
    if len(qids) != len(set(qids)):
        print("DUPLICATE quiz ids"); problems += 1
    for lesson in lessons:
        lid = lesson["id"]
        if only and lid not in only:
            continue
        for key in ("title", "concepts", "quiz"):
            if not lesson.get(key):
                print(f"{lid}: missing {key}"); problems += 1
        if len(lesson.get("quiz", [])) < 5:
            print(f"{lid}: fewer than 5 quiz items"); problems += 1
        if not (vd.drill_dir(lid) / "drill.json").exists():
            print(f"{lid}: NO DRILL"); problems += 1
            continue
        drill = vd.load_drill(lid)
        if drill.get("type") == "task":
            ok = (vd.drill_dir(lid) / "check.sh").exists()
            print(f"{lid}: task  {'ok' if ok else 'MISSING check.sh'}")
            problems += 0 if ok else 1
            continue
        if not (vd.drill_dir(lid) / "target").is_dir():
            print(f"{lid}: missing target/"); problems += 1
            continue
        if not vd.compare_dirs(vd.drill_dir(lid) / "start", vd.drill_dir(lid) / "target"):
            print(f"{lid}: start == target (nothing to do)"); problems += 1
        for clean in (True, False):
            bad, err = replay(lid, drill, clean)
            label = "clean" if clean else "user-config"
            if bad:
                problems += 1
                print(f"{lid}: FAIL ({label}) {bad} {err}")
            else:
                print(f"{lid}: ok ({label}) par={vd.par(drill)}")
    print(f"\n{problems} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--mix"]:
        verify_mix(int(sys.argv[2]), sys.argv[3:])
    main(sys.argv[1:])
