"""One-shot (October 2026): one stylesheet and one assets/ folder for the whole site.

Moves the section OG images and js/quiz.js under /assets/, deletes the section copies of
the fonts, favicon and portrait (byte-identical to the root ones, or the same picture at
a smaller size), drops the unused v1 OG images, and rewrites every reference: relative
paths stay relative (../style.css, ../assets/...), absolute URLs stay absolute.
The section stylesheets were merged into /style.css by hand before this script.

    python -I _migration/merge_assets.py
"""
import hashlib
import posixpath
import re
import subprocess
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent
APEX = "https://arnaudlegout.fr"
FONTS = ("inter.woff2", "source-serif-4.woff2", "jetbrains-mono.woff2")

MOVES = {  # kept files: old path -> new path
    "formation/assets/images/og-image-v2.jpg": "assets/og-formation.jpg",
    "consulting/assets/og-image-v2.jpg": "assets/og-consulting.jpg",
    "consulting/js/quiz.js": "assets/js/quiz.js",
}
MAP = {"/" + k: "/" + v for k, v in MOVES.items()}
for sec in ("formation", "consulting"):
    MAP[f"/{sec}/style.css"] = "/style.css"
    MAP[f"/{sec}/assets/favicon.svg"] = "/assets/favicon.svg"
    MAP[f"/{sec}/assets/images/photo-arnaud-legout.jpg"] = "/assets/images/photo-arnaud-legout.jpg"
    for f in FONTS:
        MAP[f"/{sec}/assets/fonts/{f}"] = f"/assets/fonts/{f}"


def git(*args):
    subprocess.run(["git", "-C", str(HOME), *args], check=True)


def sha(p):
    return hashlib.sha256((HOME / p).read_bytes()).hexdigest()


def rel_ref(value, page):
    """Rewrite one relative href/src of page (path relative to HOME)."""
    if re.match(r"^[a-z]+:|^//|^#|^/", value):
        return value
    base, sep, tail = re.match(r"([^?#]*)([?#]?)(.*)", value).groups()
    target = posixpath.normpath(posixpath.join("/" + posixpath.dirname(page), base))
    if target not in MAP:
        return value
    return posixpath.relpath(MAP[target], "/" + posixpath.dirname(page)) + sep + tail


def main():
    # identical copies only
    for sec in ("formation", "consulting"):
        for f in FONTS:
            assert sha(f"{sec}/assets/fonts/{f}") == sha(f"assets/fonts/{f}"), f
        assert sha(f"{sec}/assets/favicon.svg") == sha("assets/favicon.svg")
    for old, new in MOVES.items():
        if (HOME / old).exists():
            (HOME / new).parent.mkdir(parents=True, exist_ok=True)
            git("mv", old, new)
    leftovers = [d for d in ("formation/assets", "consulting/assets") if (HOME / d).exists()]
    if leftovers:
        git("rm", "-r", "-q", *leftovers)

    for page in sorted(p.relative_to(HOME).as_posix() for p in HOME.rglob("*.html")
                       if not p.relative_to(HOME).as_posix().startswith("_")):
        f = HOME / page
        text = f.read_text(encoding="utf-8")
        new = re.sub(r'(\s(?:href|src)=")([^"]*)(")', lambda m: m.group(1) + rel_ref(m.group(2), page) + m.group(3), text)
        for old_path, new_path in MAP.items():
            new = new.replace(APEX + old_path, APEX + new_path)
        if new != text:
            with open(f, "w", encoding="utf-8", newline="") as out:
                out.write(new)
            print("rewritten", page)


if __name__ == "__main__":
    main()
