"""Phase 2 check: serve each stub repo locally and verify every url-map row.

For each old_url: 200; canonical, meta refresh, location.replace and the body link all
equal new_url; no noindex, no analytics. 404.html points to the section root; the root
index.html keeps the host's verification tags; sitemap URLs all have a stub; only
CNAME, .gitignore, images, stubs, robots.txt and sitemap.xml remain.
"""
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import serve, url_map  # noqa: E402

REPOS = {"formation.arnaudlegout.fr": ("formation-consulting", "https://arnaudlegout.fr/formation/", 3),
         "consulting.arnaudlegout.fr": ("consulting", "https://arnaudlegout.fr/consulting/", 2)}
WEB = __import__("pathlib").Path(__file__).resolve().parent.parent.parent
fail, rows_out = [], []


def targets(page):
    return {
        "canonical": re.findall(r'<link rel="canonical" href="([^"]*)">', page),
        "refresh": re.findall(r'<meta http-equiv="refresh" content="0; url=([^"]*)">', page),
        "js": re.findall(r'location\.replace\("([^"]*)" \+ location\.search \+ location\.hash\)', page),
        "link": re.findall(r'<a href="([^"]*)">', page),
    }


for host, (name, root, n_verif) in REPOS.items():
    repo = WEB / name
    base = serve(repo)
    rows = [r for r in url_map() if urlsplit(r["old_url"]).netloc == host] + \
           [{"old_url": f"https://{host}/404.html", "new_url": root}]
    for r in rows:
        path = urlsplit(r["old_url"]).path
        try:
            with urlopen(base + path) as resp:
                status, page = resp.status, resp.read().decode("utf-8")
        except HTTPError as e:
            status, page = e.code, ""
        t = targets(page)
        ok = status == 200 and all(v == [r["new_url"]] for v in t.values())
        bad = [k for k, v in t.items() if v != [r["new_url"]]]
        if re.search(r"noindex|goatcounter|gc\.zgo\.at", page):
            ok, bad = False, bad + ["noindex/analytics"]
        rows_out.append((r["old_url"], status, r["new_url"], "OK" if ok else "FAIL " + ",".join(bad)))
        if not ok:
            fail.append(r["old_url"])
    index = (repo / "index.html").read_text(encoding="utf-8")
    nv = len(re.findall(r'<meta name="(?:google-site-verification|msvalidate\.01)"', index))
    if nv != n_verif:
        fail.append(f"{name}/index.html: {nv} verification tags, expected {n_verif}")
    stubs = {p.relative_to(repo).as_posix() for p in repo.rglob("*.html")}
    for loc in re.findall(r"<loc>([^<]+)</loc>", (repo / "sitemap.xml").read_text(encoding="utf-8")):
        p = urlsplit(loc).path.lstrip("/")
        if (p + "index.html" if p == "" or p.endswith("/") else p) not in stubs:
            fail.append(f"sitemap {loc}: no stub")
    others = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*")
                    if p.is_file() and ".git" not in p.parts and p.suffix != ".html"
                    and not re.match(r"(CNAME|\.gitignore|robots\.txt|sitemap\.xml|CLAUDE\.md|README\.md|"
                                     r"CONTEXTE.*|prompt_.*|\.claude/.*|articles/README\.md|assets/images/.*|assets/og-image.*\.jpg)$",
                                     p.relative_to(repo).as_posix()))
    if others:
        fail.append(f"{name}: unexpected files left {others}")
    robots = (repo / "robots.txt").read_text(encoding="utf-8")
    if robots != f"User-agent: *\nAllow: /\n\nSitemap: https://{host}/sitemap.xml\n":
        fail.append(f"{name}/robots.txt: {robots!r}")
    print(f"{name}: {len(stubs)} stub pages, {nv} verification tags in index.html")

w = max(len(r[0]) for r in rows_out)
for old, status, new, res in rows_out:
    print(f"{old:<{w}}  {status}  -> {new}  {res}")
print("\n".join(fail) if fail else "check_stubs: OK")
sys.exit(1 if fail else 0)
