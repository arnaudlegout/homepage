"""Phase 3 check, on the live sites.

    python _migration/check_live.py new [--wait]   # the new site, after the homepage push
    python _migration/check_live.py old            # the old hosts, after the stub push

new: every new_url of url-map.csv, every sitemap URL: 200, one canonical = itself,
og:url = canonical, no noindex; the live pages are byte-identical to the local commit
(--wait polls until GitHub Pages has deployed it); the old hosts still serve their own
pages (self canonical), since they are only switched in the old-host step.
old: every old_url: 200, meta refresh, canonical and location.replace = new_url;
extensionless form too; arnaudlegout.github.io/<repo>/... -> one 301 to the old host.
"""
import argparse
import http.client
import re
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import APEX, HOME, read, url_map  # noqa: E402

UA = {"User-Agent": "check_live (arnaudlegout.fr migration)", "Cache-Control": "no-cache"}


def get(url):
    try:
        with urlopen(Request(url, headers=UA), timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, ""


def head_once(url):
    """First response only (no redirect following)."""
    u = urlsplit(url)
    c = http.client.HTTPSConnection(u.netloc, timeout=30)
    c.request("GET", u.path or "/", headers=UA)
    r = c.getresponse()
    loc = r.getheader("Location")
    r.read()
    c.close()
    return r.status, loc


def local_file(url):
    path = urlsplit(url).path.lstrip("/")
    return path + "index.html" if path == "" or path.endswith("/") else path


def check_new(wait):
    probe = f"{APEX}/formation/"
    want = read(local_file(probe)).replace("\r\n", "\n")
    for i in range(60):
        status, body = get(probe + f"?nocache={time.time()}")
        if status == 200 and body.replace("\r\n", "\n") == want:
            break
        if not wait:
            sys.exit(f"{probe}: not the local commit yet (status {status})")
        print(f"waiting for the deployment ({status})…", flush=True)
        time.sleep(20)
    else:
        sys.exit("deployment not visible after 20 minutes")

    urls = sorted({r["new_url"] for r in url_map()} | set(re.findall(r"<loc>([^<]+)</loc>", read("sitemap.xml"))))
    fail = []
    for u in urls:
        status, body = get(u)
        same = body.replace("\r\n", "\n") == read(local_file(u)).replace("\r\n", "\n")
        canon = re.findall(r'<link rel="canonical" href="([^"]*)"', body)
        og = re.findall(r'<meta property="og:url" content="([^"]*)"', body)
        robots = re.findall(r'<meta name="robots" content="([^"]*)"', body)
        noindex_ok = u.endswith(("/mentions-legales.html", "/articles.html"))
        problems = [p for p, bad in [
            (f"status {status}", status != 200),
            ("differs from the local commit", not same),
            (f"canonical {canon}", canon != [u]),
            (f"og:url {og}", og and og != canon),
            (f"robots {robots}", any("noindex" in r for r in robots) and not noindex_ok),
        ] if bad]
        print(f"{'OK  ' if not problems else 'FAIL'} {u}  {'; '.join(problems)}")
        fail += problems
    for host in ("formation.arnaudlegout.fr", "consulting.arnaudlegout.fr"):
        status, body = get(f"https://{host}/")
        canon = re.findall(r'<link rel="canonical" href="([^"]*)"', body)
        ok = status == 200 and canon == [f"https://{host}/"]
        print(f"{'OK  ' if ok else 'FAIL'} old host still serves its own site: https://{host}/  canonical {canon}")
        fail += [] if ok else [host]
    print("check_live new: OK" if not fail else f"check_live new: {len(fail)} problems")
    return not fail


def check_old():
    fail = []
    for r in url_map():
        old, new = r["old_url"], r["new_url"]
        forms = [old] + ([old[:-len(".html")]] if old.endswith(".html") and not old.endswith("/index.html") else [])
        for u in forms:
            status, body = get(u)
            got = {
                "canonical": re.findall(r'<link rel="canonical" href="([^"]*)"', body),
                "refresh": re.findall(r'<meta http-equiv="refresh" content="0; url=([^"]*)"', body),
                "js": re.findall(r'location\.replace\("([^"]*)"', body),
            }
            bad = [k for k, v in got.items() if v != [new]]
            print(f"{'OK  ' if status == 200 and not bad else 'FAIL'} {u} -> {new}  {status} {bad or ''}")
            fail += bad + ([] if status == 200 else [status])
    for repo, host in (("formation-consulting", "formation.arnaudlegout.fr"), ("consulting", "consulting.arnaudlegout.fr")):
        status, loc = head_once(f"https://arnaudlegout.github.io/{repo}/contact.html")
        ok = status == 301 and loc == f"https://{host}/contact.html"
        print(f"{'OK  ' if ok else 'FAIL'} arnaudlegout.github.io/{repo}/contact.html -> {status} {loc}")
        fail += [] if ok else [repo]
    print("check_live old: OK" if not fail else f"check_live old: {len(fail)} problems")
    return not fail


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["new", "old"])
    ap.add_argument("--wait", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if (check_new(a.wait) if a.which == "new" else check_old()) else 1)
