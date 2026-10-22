"""Checks 2, 3 and 5 (static, on the files of the repo).

2. no formation.arnaudlegout.fr / consulting.arnaudlegout.fr / github.io outside
   _migration/ and CLAUDE.md; //gc.zgo.at/count.js intact, once per page;
3. per page: one canonical = its new URL, og:url = canonical, no noindex except legal,
   articles, 404 (and the unpublished article template); sitemap = indexable pages;
5. every JSON-LD block parses, holds no old host, one variant of the Person
   name / jobTitle / sameAs, and every {"@id": ...} reference resolves to a node
   defined somewhere on the site.
"""
import json
import re
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import HOME, NOINDEX_OK, TEMPLATE, new_url, pages, parse, read  # noqa: E402

PERSON = "https://arnaudlegout.fr/#arnaud-legout"
fail = []

# 2 ---------------------------------------------------------------------------------
n = 0
for p in sorted(HOME.rglob("*")):
    rel = p.relative_to(HOME).as_posix()
    if not p.is_file() or rel.startswith((".git/", "_migration/")) or rel == "CLAUDE.md" \
            or p.suffix in (".woff2", ".jpg", ".png"):
        continue
    n += 1
    for m in re.finditer(r"formation\.arnaudlegout\.fr|consulting\.arnaudlegout\.fr|github\.io", p.read_text(encoding="utf-8")):
        fail.append(f"old host: {rel}: {m.group(0)}")
gc = {rel: read(rel).count('src="//gc.zgo.at/count.js"') for rel in pages()}
if set(gc.values()) != {1}:
    fail.append(f"gc.zgo.at count per page: { {k: v for k, v in gc.items() if v != 1} }")
print(f"2. {n} text files scanned for old hosts; //gc.zgo.at/count.js: {sum(gc.values())} for {len(gc)} pages")

# 3 ---------------------------------------------------------------------------------
indexable = set()
for rel in pages():
    p = parse(read(rel))
    canon = [a.get("href") for a in p.links if a.get("rel") == "canonical"]
    robots = ",".join(c or "" for c in p.meta.get("robots", []))
    noindex = "noindex" in robots
    if noindex and rel not in NOINDEX_OK:
        fail.append(f"noindex on {rel}")
    if not noindex and rel != TEMPLATE:  # the template is not published (leading "_")
        indexable.add(new_url(rel))
    if rel == TEMPLATE:
        continue  # canonical is a your-slug placeholder
    want = new_url(rel)
    if rel == "404.html":
        if canon:
            fail.append(f"404.html has a canonical {canon}")
        continue
    if canon != [want]:
        fail.append(f"canonical of {rel}: {canon}, expected {want}")
    og = p.meta.get("og:url", [])
    if og and og != canon:
        fail.append(f"og:url of {rel}: {og} != canonical {canon}")
    if not og and rel not in NOINDEX_OK:
        fail.append(f"no og:url on {rel}")
sitemap = set(re.findall(r"<loc>([^<]+)</loc>", read("sitemap.xml")))
if sitemap != indexable:
    fail.append(f"sitemap vs indexable pages: missing {sorted(indexable - sitemap)}, extra {sorted(sitemap - indexable)}")
print(f"3. {len(pages())} pages: canonical, og:url, robots checked; sitemap has {len(sitemap)} URLs = indexable pages")

# 5 ---------------------------------------------------------------------------------
defined, refs, variants, blocks = set(), [], defaultdict(set), 0
richest = defaultdict(lambda: (0, ""))


def walk(o, rel):
    if isinstance(o, dict):
        if set(o) == {"@id"}:
            refs.append((rel, o["@id"]))
        elif "@id" in o:
            defined.add(o["@id"])
            richest[o["@id"]] = max(richest[o["@id"]], (len(o), rel))
        if o.get("@id") == PERSON:
            for k in ("name", "jobTitle", "sameAs"):
                if k in o:
                    variants[k].add(json.dumps(o[k], ensure_ascii=False))
        for v in o.values():
            walk(v, rel)
    elif isinstance(o, list):
        for v in o:
            walk(v, rel)


for rel in pages():
    for body in re.findall(r'(?is)<script type="application/ld\+json">(.*?)</script>', read(rel)):
        blocks += 1
        try:
            walk(json.loads(body), rel)
        except json.JSONDecodeError as e:
            fail.append(f"JSON-LD parse error in {rel}: {e}")
for k, v in variants.items():
    if len(v) != 1:
        fail.append(f"Person {k}: {len(v)} variants: {sorted(v)}")
for rel, ref in refs:
    if ref not in defined:
        fail.append(f"unresolved @id reference in {rel}: {ref}")
print(f"5. {blocks} JSON-LD blocks parse; Person variants: "
      + ", ".join(f"{k}={len(v)}" for k, v in sorted(variants.items()))
      + f"; {len(refs)} @id references, {len({r for _, r in refs})} distinct, all resolved" * (not any("unresolved" in f for f in fail)))
print("sameAs:", next(iter(variants["sameAs"])))
print("@id inventory (richest definition: number of properties, page):")
for i in sorted(defined | {r for _, r in refs}):
    n, rel = richest[i]
    print(f"   {i}  ->  {n} props in {rel}" if n else f"   {i}  ->  NOT DEFINED")

print("\n".join(fail) if fail else "checks: OK")
sys.exit(1 if fail else 0)
