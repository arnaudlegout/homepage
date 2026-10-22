"""Check 1: serve the repo root, crawl from /, follow every internal link and asset.

- zero 404 (pages, CSS, CSS url(), fonts, favicon, images, js/quiz.js), and every
  internal #fragment exists on its target page;
- every new_url of url-map.csv, every sitemap <loc> and every llms.txt link -> 200;
- /formation and /consulting without slash: 301 to the slash form, assets still load;
- static pass over every HTML file on disk (also unlinked ones: 404.html, the article
  template): every internal reference resolves to a file; 404.html uses root-absolute
  references only (GitHub Pages serves it from any missing URL).
"""
import http.client
import re
import sys
from collections import defaultdict
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import urlopen
from urllib.error import HTTPError

sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import APEX, HOME, TEMPLATE, pages, parse, read, serve, url_map  # noqa: E402

fail = []


def get(url):
    try:
        with urlopen(url) as r:
            return r.status, r.geturl(), r.headers.get_content_type(), r.read()
    except HTTPError as e:
        return e.code, url, None, b""


def local(u):
    return u.replace(APEX, BASE, 1)


BASE = serve(HOME)
seen, refs_to, queue = {}, defaultdict(set), [BASE + "/"]
frag_checks = []
while queue:
    url = queue.pop()
    if url in seen:
        continue
    status, final, ctype, body = get(url)
    seen[url] = status
    if status != 200:
        continue
    if ctype == "text/html":
        p = parse(body.decode("utf-8"))
        for tag, attr, val, a in p.refs:
            if val.startswith(("mailto:", "tel:", "data:")) or (tag == "link" and a.get("rel") == "canonical"):
                continue
            target, frag = urldefrag(urljoin(final, val))
            if not target.startswith(BASE):
                continue
            refs_to[target].add(final)
            if frag:
                frag_checks.append((final, target, frag))
            queue.append(target)
    elif ctype == "text/css":
        for val in re.findall(r"url\(\s*['\"]?([^'\")]+)", body.decode("utf-8")):
            target = urljoin(final, val)
            refs_to[target].add(final)
            queue.append(target)

bad = {u: s for u, s in seen.items() if s != 200}
for u, s in sorted(bad.items()):
    fail.append(f"crawl: {s} {u[len(BASE):]}  (from {', '.join(r[len(BASE):] for r in sorted(refs_to[u]))})")
html_cache = {}
for src, target, frag in frag_checks:
    if target not in html_cache:
        html_cache[target] = parse(get(target)[3].decode("utf-8")).ids
    if frag not in html_cache[target]:
        fail.append(f"fragment: #{frag} missing in {target[len(BASE):]} (from {src[len(BASE):]})")
kinds = defaultdict(int)
for u in seen:
    kinds[u.rsplit(".", 1)[-1] if "." in u.rsplit("/", 1)[-1] else "page/"] += 1
print(f"crawl: {len(seen)} internal URLs fetched ({dict(sorted(kinds.items()))}), {len(bad)} not 200, "
      f"{len(frag_checks)} fragment links checked")

# url-map, sitemap, llms.txt targets
targets = {r["new_url"] for r in url_map()}
targets |= set(re.findall(r"<loc>([^<]+)</loc>", read("sitemap.xml")))
targets |= set(re.findall(r"\]\((https://arnaudlegout\.fr/[^)]*)\)", read("llms.txt")))
for t in sorted(targets):
    s = get(local(t))[0]
    if s != 200:
        fail.append(f"target: {s} {t}")
print(f"targets: {len(targets)} URLs from url-map.csv, sitemap.xml and llms.txt checked")

# no trailing slash
host, port = BASE[len("http://"):].split(":")
for sec in ("formation", "consulting"):
    c = http.client.HTTPConnection(host, int(port))
    c.request("GET", f"/{sec}")
    r = c.getresponse()
    loc = r.getheader("Location")
    r.read()
    c.close()
    if r.status != 301 or urlsplit(loc).path != f"/{sec}/":
        fail.append(f"/{sec}: expected 301 to /{sec}/, got {r.status} {loc}")
        continue
    status, final, _, body = get(urljoin(BASE + f"/{sec}", loc))
    assets = [urljoin(final, v) for t, k, v, a in parse(body.decode()).refs
              if t in ("link", "script", "img") and a.get("rel") != "canonical" and not v.startswith(("http", "//"))]
    broken = [a for a in assets if get(a)[0] != 200]
    if status != 200 or broken:
        fail.append(f"/{sec}: final {status}, broken assets {broken}")
    print(f"/{sec} -> {r.status} {loc} -> {status}, {len(assets)} assets resolved against {final[len(BASE):]}, {len(broken)} broken")

# static pass over every HTML file on disk
n = 0
for rel in pages():
    page_url = f"/{rel}"
    for tag, attr, val, a in parse(read(rel)).refs:
        if val.startswith(("#", "mailto:", "tel:", "data:", "http://", "https://", "//")):
            continue
        if rel == "404.html" and not val.startswith("/"):
            fail.append(f"404.html: relative reference {val}")
        path = urlsplit(urljoin(page_url, val)).path
        if rel == TEMPLATE and "your-slug" in path:
            continue
        f = HOME / path.lstrip("/")
        if path.endswith("/"):
            f = f / "index.html"
        n += 1
        if not f.is_file():
            fail.append(f"static: {rel}: {val} -> {path} does not exist")
print(f"static: {n} internal references in {len(pages())} HTML files checked on disk")

print("\n".join(fail) if fail else "check_local: OK")
sys.exit(1 if fail else 0)
