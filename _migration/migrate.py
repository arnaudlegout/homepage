"""Build the monorepo layout of prompt_migration_subdirs.md (Phase 1, decisions D1-D16).

Copies ../formation-consulting to formation/ (formations/<slug>.html flattened to
formation/<slug>.html) and ../consulting to consulting/, then rewrites URLs:

- moved pages: links stay relative inside a section; links leaving the section
  (other section, homepage, legal page, sitemap) become root-absolute; canonical,
  og:*, twitter:* and JSON-LD become absolute https://arnaudlegout.fr/... URLs;
- JSON-LD: section WebSite nodes removed (D9), the two subdomains removed from the
  Person sameAs (D8), a root item added to every BreadcrumbList (D11);
- visible text naming an old host: the D6 list only;
- homepage pages: links to the old hosts, D5 legal paragraph, dateModified;
- root sitemap.xml, llms.txt (D12); robots.txt is already correct.

Idempotent: always rebuilt from the pre-subdir-migration-2026-10 tags (the sibling
working trees must be clean and at that tag). Run from anywhere:

    python -I _migration/migrate.py [--deploy-date 2026-10-22] [--date-modified ISO]
"""
import argparse
import csv
import json
import posixpath
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
WEB = HOME.parent
TAG = "pre-subdir-migration-2026-10"
APEX = "https://arnaudlegout.fr"
OLD = {"formation.arnaudlegout.fr": "formation", "consulting.arnaudlegout.fr": "consulting"}
REPOS = {"formation": WEB / "formation-consulting", "consulting": WEB / "consulting"}
SKIP = {"CNAME", "robots.txt", "sitemap.xml", "404.html", "mentions-legales.html",
        "llms.txt", ".gitignore", "consulting.html", "CLAUDE.md", "README.md"}
WEBSITE = APEX + "/#website"
OLD_SAMEAS = ("https://formation.arnaudlegout.fr/", "https://consulting.arnaudlegout.fr/")
LABEL = {"formation.arnaudlegout.fr": "arnaudlegout.fr/formation",
         "consulting.arnaudlegout.fr": "arnaudlegout.fr/consulting"}
D6_FILES = {"index.html", "formation/contact.html", "consulting/a-propos.html",
            "consulting/audit-agents-ia-data-science.html"}
ROOT_NAME = "Arnaud Legout"  # D11: name of the homepage (its WebSite name)

LEGAL_OLD = ("<p>Ce site ne comporte aucun formulaire et ne dépose aucun cookie. Il ne charge "
             "aucune ressource externe en dehors de l'outil de mesure d'audience décrit ci-dessous.</p>")
LEGAL_NEW = ("<p>La seule collecte de données du site passe par les formulaires des pages contact "
             "des sections formation et conseil, opérés par Tally. Les informations que vous y "
             "saisissez servent uniquement à répondre à votre demande et ne sont transmises à aucun "
             "tiers.</p>\n        <p>Ce site ne dépose aucun cookie et ne charge aucune ressource "
             "externe en dehors de ces formulaires et de l'outil de mesure d'audience décrit "
             "ci-dessous.</p>")

ROWS = {r["old_url"]: r["new_url"] for r in csv.DictReader(open(HERE / "url-map.csv", encoding="utf-8"))}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True).stdout


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


# --- URLs -------------------------------------------------------------------------

def map_url(u):
    """Absolute old-host URL -> absolute new URL (url-map.csv rows first, then prefix rules)."""
    s = urlsplit(u)
    if s.netloc not in OLD:
        return u
    sec, path = OLD[s.netloc], s.path or "/"
    if path == "/" and s.fragment == "website":
        return WEBSITE
    base = f"https://{s.netloc}{path}"
    if base in ROWS:
        new = ROWS[base]
    elif path == "/sitemap.xml":
        new = APEX + path
    elif sec == "formation" and path.startswith("/formations/"):
        new = f"{APEX}/formation/{path[len('/formations/'):]}"
    else:
        new = f"{APEX}/{sec}{path}"
    return new + ("?" + s.query if s.query else "") + ("#" + s.fragment if s.fragment else "")


def nav(value, ctx):
    """Rewrite a navigational href/src (D4, point 6 of Phase 0)."""
    if not value or value.startswith(("#", "mailto:", "tel:", "data:", "javascript:", "//")):
        return value
    s = urlsplit(value)
    if s.scheme and s.scheme not in ("http", "https"):
        return value
    if s.netloc and s.netloc not in OLD and s.netloc != "arnaudlegout.fr":
        return value
    if ctx["section"] is None and s.netloc not in OLD:
        return value  # homepage pages: only links to the old hosts change
    new = value if s.netloc == "arnaudlegout.fr" else map_url(urljoin(ctx["old_url"], value))
    n = urlsplit(new)
    assert n.netloc == "arnaudlegout.fr", (ctx["out"], value, new)
    tail = ("?" + n.query if n.query else "") + ("#" + n.fragment if n.fragment else "")
    sec = ctx["section"]
    if sec and n.path.startswith(f"/{sec}/"):
        rel = posixpath.relpath(n.path, posixpath.dirname(ctx["new_path"]))
        if n.path.endswith("/"):
            rel = "./" if rel == "." else rel + "/"
        return rel + tail
    return n.path + tail


ATTR = re.compile(r'(\s)(href|src|content)="([^"]*)"')


def rewrite_tag(tag, ctx):
    canonical = tag.lower().startswith("<link") and re.search(r'\brel="canonical"', tag)

    def sub(m):
        attr, val = m.group(2), m.group(3)
        if attr == "content" or canonical:
            new = map_url(val) if val.startswith("https://") else val
        else:
            new = nav(val, ctx)
        return f'{m.group(1)}{attr}="{new}"'
    return ATTR.sub(sub, tag)


# --- JSON-LD ----------------------------------------------------------------------

def spans(txt):
    """[start, end, kind, parent] for every {...} / [...] of a JSON text."""
    out, stack, i = [], [], 0
    while i < len(txt):
        c = txt[i]
        if c == '"':
            i += 1
            while txt[i] != '"':
                i += 2 if txt[i] == "\\" else 1
        elif c in "{[":
            out.append([i, None, c, stack[-1] if stack else None])
            stack.append(len(out) - 1)
        elif c in "}]":
            out[stack.pop()][1] = i + 1
        i += 1
    return out


def old_website(v):
    return isinstance(v, dict) and v.get("@type") == "WebSite" and urlsplit(v.get("@id", "")).netloc in OLD


def edit_website_once(txt):
    sp = spans(txt)
    for j, (a, b, kind, par) in enumerate(sp):
        if kind != "{" or not old_website(json.loads(txt[a:b])):
            continue
        if sp[par][2] == "{":  # value of isPartOf: becomes a reference
            assert re.search(r'"isPartOf":\s*$', txt[:a])
            return txt[:a] + '{ "@id": "' + WEBSITE + '" }' + txt[b:]
        sib = [k for k, x in enumerate(sp) if x[3] == par]
        pos = sib.index(j)
        if pos + 1 < len(sib):
            return txt[:a] + txt[sp[sib[pos + 1]][0]:]
        return txt[:sp[sib[pos - 1]][1]] + txt[b:]
    return None


def edit_breadcrumbs(txt):
    sp = spans(txt)
    lists = [j for j, x in enumerate(sp) if x[2] == "{" and json.loads(txt[x[0]:x[1]]).get("@type") == "BreadcrumbList"]
    for j in reversed(lists):
        arr = [k for k, x in enumerate(sp) if x[3] == j and x[2] == "["]
        assert len(arr) == 1
        items = [sp[k] for k, x in enumerate(sp) if x[3] == arr[0]]
        assert len(items) >= 2 and json.loads(txt[items[0][0]:items[0][1]])["position"] == 1
        first = txt[items[0][0]:items[0][1]]
        sep = txt[items[0][1]:items[1][0]]
        root = re.sub(r'("name":\s*)"(?:[^"\\]|\\.)*"', lambda m: m.group(1) + json.dumps(ROOT_NAME, ensure_ascii=False), first, count=1)
        root = re.sub(r'("item":\s*)"[^"]*"', lambda m: m.group(1) + f'"{APEX}/"', root, count=1)
        for a, b, _, _ in reversed(items):
            txt = txt[:a] + re.sub(r'("position":\s*)(\d+)', lambda m: m.group(1) + str(int(m.group(2)) + 1), txt[a:b], count=1) + txt[b:]
        txt = txt[:items[0][0]] + root + sep + txt[items[0][0]:]
    return txt


def expected_ld(o, date_modified):
    """What the edited JSON-LD must parse to: the same edits, applied to the parsed data."""
    if isinstance(o, dict):
        if old_website(o):
            return {"@id": WEBSITE}
        d = {}
        for k, v in o.items():
            if k == "@graph":
                v = [x for x in v if not old_website(x)]
            if k == "sameAs" and o.get("@type") == "Person":
                v = [x for x in v if x not in OLD_SAMEAS]
            d[k] = expected_ld(v, date_modified)
        if d.get("@type") == "BreadcrumbList":
            for it in d["itemListElement"]:
                it["position"] += 1
            d["itemListElement"].insert(0, {"@type": "ListItem", "position": 1, "name": ROOT_NAME, "item": APEX + "/"})
        if d.get("@type") == "ProfilePage" and date_modified:
            d["dateModified"] = date_modified
        return d
    if isinstance(o, list):
        return [expected_ld(x, date_modified) for x in o]
    if isinstance(o, str) and o.startswith("https://"):
        return map_url(o)
    return o


def rewrite_ld(txt, date_modified=None):
    before = json.loads(txt)
    txt = re.sub(r'\r?\n[ \t]*"https://(?:formation|consulting)\.arnaudlegout\.fr/",(?=\r?\n)', "", txt)
    while (new := edit_website_once(txt)) is not None:
        txt = new
    txt = edit_breadcrumbs(txt)
    txt = re.sub(r'https://(?:formation|consulting)\.arnaudlegout\.fr[^"\s]*', lambda m: map_url(m.group(0)), txt)
    if date_modified:
        txt, n = re.subn(r'("dateModified":\s*)"[^"]*"', lambda m: f'{m.group(1)}"{date_modified}"', txt)
        assert n == 1
    assert json.loads(txt) == expected_ld(before, date_modified), "JSON-LD edit does not match the model"
    return txt


# --- pages ------------------------------------------------------------------------

SEG = re.compile(r'(?is)(<!--.*?-->)|(<script\b[^>]*>)(.*?)(</script\s*>)|(<style\b[^>]*>.*?</style\s*>)|(<[^>]+>)')


def rewrite_html(html, ctx, d6_hits):
    out, pos = [], 0

    def text(t):
        for host, label in LABEL.items():
            if host in t:
                d6_hits.add(ctx["out"])
                t = t.replace(host, label)
        return t
    for m in SEG.finditer(html):
        out.append(text(html[pos:m.start()]))
        pos = m.end()
        if m.group(1):  # comment: commented-out links follow the same rules
            out.append(rewrite_tag(m.group(1), ctx))
        elif m.group(5):  # <style>: untouched
            out.append(m.group(0))
        elif m.group(2):
            open_tag = rewrite_tag(m.group(2), ctx)
            body = m.group(3)
            if "application/ld+json" in open_tag:
                body = rewrite_ld(body, ctx.get("date_modified"))
            out.append(open_tag + body + m.group(4))
        else:
            out.append(rewrite_tag(m.group(6), ctx))
    out.append(text(html[pos:]))
    return "".join(out)


def check_sibling(repo):
    if git(repo, "status", "--porcelain").strip():
        sys.exit(f"{repo} has uncommitted changes")
    if git(repo, "rev-parse", "HEAD") != git(repo, "rev-parse", TAG + "^{commit}"):
        sys.exit(f"{repo}: HEAD is not {TAG}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy-date", default=date.today().isoformat())
    ap.add_argument("--date-modified", default=datetime.now().astimezone().replace(microsecond=0).isoformat())
    args = ap.parse_args()

    d6_hits, gc_before, written = set(), 0, []
    for sec, repo in REPOS.items():
        check_sibling(repo)
        shutil.rmtree(HOME / sec, ignore_errors=True)
        for rel in git(repo, "ls-files").decode().split("\n"):
            if not rel or rel in SKIP:
                continue
            flat = rel[len("formations/"):] if sec == "formation" and rel.startswith("formations/") else rel
            dst = HOME / sec / flat
            if not rel.endswith(".html"):
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo / rel, dst)
                if rel.endswith((".css", ".js")):
                    assert not re.search(r"arnaudlegout\.fr|github\.io", read(dst)), dst
                continue
            src = read(repo / rel)
            gc_before += src.count('src="//gc.zgo.at/count.js"')
            ctx = {"section": sec, "out": f"{sec}/{flat}",
                   "old_url": f"https://{[h for h, s in OLD.items() if s == sec][0]}/{rel}",
                   "new_path": f"/{sec}/{flat}"}
            write(dst, rewrite_html(src, ctx, d6_hits))
            written.append(dst)

    # Homepage pages, from the tag (idempotent)
    for name in ("index.html", "404.html", "mentions-legales.html"):
        src = git(HOME, "show", f"{TAG}:{name}").decode("utf-8")
        gc_before += src.count('src="//gc.zgo.at/count.js"')
        ctx = {"section": None, "out": name, "old_url": f"{APEX}/{name}", "new_path": f"/{name}",
               "date_modified": args.date_modified if name == "index.html" else None}
        html = rewrite_html(src, ctx, d6_hits)
        if name == "mentions-legales.html":
            assert html.count(LEGAL_OLD) == 1
            html = html.replace(LEGAL_OLD, LEGAL_NEW)
        write(HOME / name, html)
        written.append(HOME / name)
    assert d6_hits == D6_FILES, f"D6 text replacements in {sorted(d6_hits)}"

    # sitemap.xml: homepage + every URL of the two section sitemaps, lastmod = deploy date
    home_sm = git(HOME, "show", f"{TAG}:sitemap.xml").decode()
    blocks = [re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{args.deploy_date}</lastmod>",
                     re.search(r"(?s)<url>.*?</url>", home_sm).group(0))]
    for repo in REPOS.values():
        for b in re.findall(r"(?s)<url>.*?</url>", read(repo / "sitemap.xml")):
            b = re.sub(r"<loc>([^<]*)</loc>", lambda m: f"<loc>{map_url(m.group(1))}</loc>", b)
            blocks.append(re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{args.deploy_date}</lastmod>", b))
    write(HOME / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n\n  '
          + "\n\n  ".join(blocks) + "\n\n</urlset>\n")
    assert len(blocks) == 15

    # llms.txt (D12)
    llms = re.sub(r"https://(?:formation|consulting)\.arnaudlegout\.fr/[^)\s]*",
                  lambda m: map_url(m.group(0)), git(HOME, "show", f"{TAG}:llms.txt").decode())
    for title, repo in (("Formation", REPOS["formation"]), ("Conseil", REPOS["consulting"])):
        pages = re.search(r"(?s)## Pages\n(.*?)\n\n", read(repo / "llms.txt")).group(1)
        pages = re.sub(r"https://(?:formation|consulting)\.arnaudlegout\.fr/[^)\s]*", lambda m: map_url(m.group(0)), pages)
        llms += f"\n## {title}\n{pages}\n"
    write(HOME / "llms.txt", llms)

    assert read(HOME / "robots.txt") == "User-agent: *\nAllow: /\n\nSitemap: https://arnaudlegout.fr/sitemap.xml\n"

    gc_after = sum(read(p).count('src="//gc.zgo.at/count.js"') for p in written)
    assert gc_after == gc_before == len(written), (gc_before, gc_after, len(written))
    print(f"{len(written)} pages written, D6 text in {sorted(d6_hits)}, "
          f"deploy date {args.deploy_date}, dateModified {args.date_modified}")


if __name__ == "__main__":
    main()
