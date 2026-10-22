"""Phase 2: turn ../formation-consulting and ../consulting into redirect stubs.

From url-map.csv, writes one stub per old_url of each host at the same path
(formations/index.html for the directory), a 404.html stub to the section root, a
robots.txt and a sitemap.xml listing the old URLs (those of the old sitemap, lastmod =
cutover date). Keeps CNAME, .gitignore and the images; deletes every other tracked file.
Works on the sibling working trees, which must be on the redirect-stubs branch.

    python -I _migration/make_stubs.py [--cutover-date 2026-10-22]
"""
import argparse
import csv
import html
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
WEB = HERE.parent.parent
TAG = "pre-subdir-migration-2026-10"
REPOS = {"formation.arnaudlegout.fr": WEB / "formation-consulting",
         "consulting.arnaudlegout.fr": WEB / "consulting"}
ROOTS = {"formation.arnaudlegout.fr": "https://arnaudlegout.fr/formation/",
         "consulting.arnaudlegout.fr": "https://arnaudlegout.fr/consulting/"}
KEEP = re.compile(r"^(CNAME|\.gitignore|assets/images/.*|assets/og-image[^/]*\.jpg)$")

STUB = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{verification}<title>Page déplacée — {title}</title>
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={url}">
<script>location.replace("{url}" + location.search + location.hash);</script>
</head>
<body>
<p>Cette page a déménagé&nbsp;: <a href="{url}">{url}</a></p>
</body>
</html>
"""


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True).stdout.decode("utf-8")


def stub_path(old_url):
    path = urlsplit(old_url).path.lstrip("/")
    return path + "index.html" if path == "" or path.endswith("/") else path


def title_of(page_html):
    return " ".join(re.search(r"(?s)<title>(.*?)</title>", page_html).group(1).split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutover-date", default=date.today().isoformat())
    args = ap.parse_args()
    rows = list(csv.DictReader(open(HERE / "url-map.csv", encoding="utf-8")))

    for host, repo in REPOS.items():
        if git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() != "redirect-stubs":
            sys.exit(f"{repo} is not on the redirect-stubs branch")
        tracked = git(repo, "ls-files").split("\n")
        old = {p: git(repo, "show", f"{TAG}:{p}") for p in git(repo, "ls-tree", "-r", "--name-only", TAG).split("\n")
               if p.endswith((".html", ".xml"))}
        verification = "".join(m + "\n" for m in re.findall(
            r'<meta name="(?:google-site-verification|msvalidate\.01)" content="[^"]*">', old["index.html"]))

        stubs = {}  # path -> (new_url, title)
        for r in rows:
            if urlsplit(r["old_url"]).netloc != host:
                continue
            path, new = stub_path(r["old_url"]), r["new_url"]
            if path in old and path != "consulting.html":
                title = title_of(old[path])
            else:  # no ordinary original (a directory, an earlier redirect): the target's title
                title = title_of((HERE.parent / stub_path(new)).read_text(encoding="utf-8"))
            assert stubs.get(path, (new,))[0] == new, (path, new)
            stubs[path] = (new, title)
        stubs["404.html"] = (ROOTS[host], title_of(old["404.html"]))

        for p in tracked:
            if p and not KEEP.match(p) and (repo / p).exists():
                (repo / p).unlink()
        for d in sorted((x for x in repo.rglob("*") if x.is_dir() and ".git" not in x.parts), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()

        for path, (new, title) in sorted(stubs.items()):
            f = repo / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(STUB.format(url=new, title=html.escape(title, quote=False),
                                     verification=verification if path == "index.html" else ""),
                         encoding="utf-8", newline="\n")

        locs = re.findall(r"<loc>([^<]+)</loc>", old["sitemap.xml"])
        assert all(stub_path(u) in stubs for u in locs), locs
        (repo / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{args.cutover_date}</lastmod>\n  </url>\n" for u in locs)
            + "</urlset>\n", encoding="utf-8", newline="\n")
        (repo / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: https://{host}/sitemap.xml\n",
                                         encoding="utf-8", newline="\n")
        print(f"{host}: {len(stubs)} stubs, sitemap {len(locs)} URLs, lastmod {args.cutover_date}")


if __name__ == "__main__":
    main()
