"""Check 6: headless Chrome screenshots, old vs new, pixel diff.

Old pages are served from the sibling working trees (the homepage from the
pre-migration tag), new ones from this repo. Headless Chrome will not render a
viewport narrower than 500 px, so each page is loaded in a same-origin iframe of the
exact width (375 or 1280 px; media queries apply to the iframe), sized to the full
page height measured in a first pass. gc.zgo.at and tally.so are blocked.

    python _migration/screenshots.py [OUT_DIR]
"""
import io
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageChops

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HOME, OLD_REPOS, TAG, serve  # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
WIDTHS = (375, 1280)
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="shots-"))
OUT.mkdir(parents=True, exist_ok=True)

old_home = OUT / "old-homepage"
if not old_home.exists():
    tar = subprocess.run(["git", "-C", str(HOME), "archive", "--format=tar", TAG], capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(old_home, filter="data")

new = serve(HOME)
old = {"home": serve(old_home), "formation": serve(OLD_REPOS["formation"]), "consulting": serve(OLD_REPOS["consulting"])}
PAGES = [  # name, old server, old path, new path
    ("home", old["home"], "/", "/"),
    ("formation-index", old["formation"], "/", "/formation/"),
    ("formation-course", old["formation"], "/formations/python-niveau-1.html", "/formation/python-niveau-1.html"),
    ("consulting-index", old["consulting"], "/", "/consulting/"),
    ("consulting-offer", old["consulting"], "/audit-agents-ia-data-science.html", "/consulting/audit-agents-ia-data-science.html"),
]
n = 0


def chrome(*args, width, height):
    global n
    n += 1
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                           "--force-device-scale-factor=1", f"--user-data-dir={OUT / f'profile{n}'}",
                           f"--window-size={max(width, 500) + 16},{height + 100}", "--virtual-time-budget=4000",
                           "--host-resolver-rules=MAP gc.zgo.at ~NOTFOUND, MAP tally.so ~NOTFOUND", *args],
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def shot(base, path, width, png):
    wrapper = f"{base}/__shot__?src={quote(path)}&w={width}"
    dom = chrome("--dump-dom", wrapper + "&h=900", width=width, height=900).stdout
    height = int(re.search(r"<title>H=(\d+)</title>", dom).group(1))
    chrome(f"--screenshot={png}", wrapper + f"&h={height}", width=width, height=height)
    return Image.open(png).convert("RGB").crop((0, 0, width, height))


fail = []
for name, old_base, old_path, new_path in PAGES:
    for w in WIDTHS:
        a = shot(old_base, old_path, w, OUT / f"{name}-{w}-old.png")
        b = shot(new, new_path, w, OUT / f"{name}-{w}-new.png")
        if a.size != b.size:
            h = min(a.height, b.height)
            box = ImageChops.difference(a.crop((0, 0, w, h)), b.crop((0, 0, w, h))).getbbox()
            print(f"{name:17} {w:>4}px  SIZE DIFFERS old {a.size} new {b.size}; diff in common area: {box}")
            fail.append((name, w))
            continue
        box = ImageChops.difference(a, b).getbbox()
        if box:
            ImageChops.difference(a, b).crop(box).point(lambda v: 255 if v else 0).save(OUT / f"{name}-{w}-diff.png")
            for img, tag in ((a, "old"), (b, "new")):
                img.crop((0, max(box[1] - 20, 0), w, min(box[3] + 20, img.height))).save(OUT / f"{name}-{w}-{tag}-crop.png")
        print(f"{name:17} {w:>4}px  {a.size[0]}x{a.size[1]}  diff bbox: {box or 'none'}")
print(f"screenshots in {OUT}")
