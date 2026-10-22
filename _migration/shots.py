"""Full-page screenshots of every page of the site, and pixel comparison of two runs.

    python _migration/shots.py capture OUT_DIR [--widths 375,900,1280] [--root DIR] [--open-menu]
    python _migration/shots.py compare BEFORE_DIR AFTER_DIR

capture serves the working tree and shoots every page (the article template excluded).
Headless Chrome will not render a viewport under 500 px, so each page is loaded in a
same-origin iframe of the exact width, sized to the full page height measured in a
first pass. gc.zgo.at and tally.so are blocked. --open-menu opens the burger menu
(.nav__menu.is-open) before the shot; --root serves another copy of the site (e.g. a
`git archive` of an earlier commit). compare prints, per page and width, the bounding
box of the changed pixels and writes before/after crops of that area.
"""
import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageChops

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HOME, TEMPLATE, pages, serve  # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def url_path(rel):
    return "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)


def name(rel, w):
    return f"{rel.replace('/', '__').removesuffix('.html')}-{w}.png"


def chrome(out, n, *args, width, height):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                           "--force-device-scale-factor=1", f"--user-data-dir={out / '_profiles' / str(n)}",
                           f"--window-size={max(width, 500) + 16},{height + 100}", "--virtual-time-budget=4000",
                           "--host-resolver-rules=MAP gc.zgo.at ~NOTFOUND, MAP tally.so ~NOTFOUND", *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=180)


def shoot(job):
    out, base, rel, w, n, open_menu = job
    wrapper = f"{base}/__shot__?src={quote(url_path(rel))}&w={w}" + ("&open=1" if open_menu else "")
    dom = chrome(out, f"{n}a", "--dump-dom", wrapper + "&h=900", width=w, height=900).stdout
    h = int(re.search(r"<title>H=(\d+)</title>", dom).group(1))
    png = out / name(rel, w)
    chrome(out, f"{n}b", f"--screenshot={png}", wrapper + f"&h={h}", width=w, height=h)
    Image.open(png).convert("RGB").crop((0, 0, w, h)).save(png)
    return png


def capture(out, widths, root=HOME, open_menu=False):
    out.mkdir(parents=True, exist_ok=True)
    base = serve(root)
    jobs = [(out, base, rel, w, i, open_menu) for i, (rel, w) in enumerate((r, w) for r in pages() if r != TEMPLATE for w in widths)]
    with ThreadPoolExecutor(4) as ex:
        done = list(ex.map(shoot, jobs))
    print(f"{len(done)} screenshots in {out}")


def compare(before, after):
    diffdir = after / "_diff"
    diffdir.mkdir(exist_ok=True)
    changed = 0
    for a_png in sorted(before.glob("*.png")):
        b_png = after / a_png.name
        if not b_png.exists():
            print(f"{a_png.stem:60} MISSING in {after}")
            continue
        a, b = Image.open(a_png).convert("RGB"), Image.open(b_png).convert("RGB")
        w, h = min(a.width, b.width), min(a.height, b.height)
        box = ImageChops.difference(a.crop((0, 0, w, h)), b.crop((0, 0, w, h))).getbbox()
        size = "" if a.size == b.size else f"  height {a.height} -> {b.height}"
        if box or size:
            changed += 1
            top = box[1] if box else h
            for img, tag in ((a, "before"), (b, "after")):
                img.crop((0, max(top - 40, 0), img.width, min((box[3] if box else top) + 40, img.height, top + 1500))).save(
                    diffdir / f"{a_png.stem}-{tag}.png")
        print(f"{a_png.stem:60} {('diff ' + str(box)) if box else 'identical'}{size}")
    print(f"{changed} of {len(list(before.glob('*.png')))} screenshots differ; crops in {diffdir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("out", type=Path)
    c.add_argument("--widths", default="375,900,1280")
    c.add_argument("--root", type=Path, default=HOME)
    c.add_argument("--open-menu", action="store_true")
    k = sub.add_parser("compare")
    k.add_argument("before", type=Path)
    k.add_argument("after", type=Path)
    args = ap.parse_args()
    if args.cmd == "capture":
        capture(args.out, [int(x) for x in args.widths.split(",")], args.root, args.open_menu)
    else:
        compare(args.before, args.after)
