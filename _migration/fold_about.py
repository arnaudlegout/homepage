"""One-shot (October 2026): fold the two "about" pages into the section homepages.

The site homepage now presents Arnaud Legout; what was specific to each "about" page
moves, verbatim, to its section homepage:
- formation: "Ma façon de former" -> under the reasons of "Pourquoi me confier...";
- consulting: the positioning (paragraphs 2-5) -> a "Pourquoi un regard indépendant"
  section before the final call to action (which becomes white, to keep the
  alternation of backgrounds).
Then: the two pages are deleted; their old URLs redirect to the section homepage
(url-map.csv); sitemap.xml and llms.txt drop them; JSON-LD links to them
(instructor, about, article author) point to the homepage, where the Person lives;
each section root gets a JSON-LD BreadcrumbList (rendered by site_chrome.py).

    python -I _migration/fold_about.py
"""
import json
import re
import subprocess
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent
APEX = "https://arnaudlegout.fr"


def read(rel):
    with open(HOME / rel, encoding="utf-8", newline="") as f:
        return f.read()


def write(rel, text):
    with open(HOME / rel, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def once(pattern, repl, text, flags=re.S):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    assert n == 1, pattern
    return new


def add_breadcrumb(rel, section, name):
    t = read(rel)
    m = re.search(r'(?s)(<script type="application/ld\+json">)(.*?)(</script>)', t)
    body = m.group(2)
    assert '"@graph"' in body and "BreadcrumbList" not in body
    node = ('      {\n        "@type": "BreadcrumbList",\n        "itemListElement": [\n'
            f'          {{ "@type": "ListItem", "position": 1, "name": "Arnaud Legout", "item": "{APEX}/" }},\n'
            f'          {{ "@type": "ListItem", "position": 2, "name": "{name}", "item": "{APEX}/{section}/" }}\n'
            '        ]\n      }')
    k = body.rindex("]")
    new = body[:k].rstrip() + ",\n" + node + "\n    " + body[k:]
    json.loads(new)
    write(rel, t[:m.start(2)] + new + t[m.end(2):])


def main():
    # 1. formation: "Ma façon de former" under the reasons
    about = read("formation/a-propos.html")
    paras = re.search(r'(?s)<h2>Ma façon de former</h2>\s*(<p>.*?</p>)\s*(<p>.*?</p>)', about).groups()
    block = ('\n\n        <div class="reason reason--wide">\n          <h3>Ma façon de former</h3>\n'
             + "".join(f"          {p}\n" for p in paras) + "        </div>")
    t = read("formation/index.html")
    t = once(r'(<section class="section section--alt" aria-labelledby="pourquoi-title">.*?<div class="reasons-grid">.*?\n        </div>)',
             lambda m: m.group(1) + block, t)
    write("formation/index.html", t)

    # 2. consulting: positioning before the final call to action
    about = read("consulting/a-propos.html").replace("\r\n", "\n")
    lead = re.search(r'(?s)<div class="page-section">\s*<p class="lead">.*?</p>\s*((?:<p>.*?</p>\s*){4})</div>', about).group(1)
    paras = re.findall(r"(?s)<p>.*?</p>", lead)
    assert len(paras) == 4
    section = ('    <!-- POURQUOI UN REGARD INDÉPENDANT -->\n'
               '    <section class="section section--alt" aria-labelledby="regard-title">\n'
               '      <div class="container container--text">\n'
               '        <h2 id="regard-title">Pourquoi un regard indépendant</h2>\n'
               + "".join(f"        {p}\n" for p in paras) +
               '      </div>\n    </section>\n\n')
    t = read("consulting/index.html")
    crlf = "\r\n" in t
    t = t.replace("\r\n", "\n")
    t = once(r'\n(    <section class="cta-section) section--alt(">)', lambda m: "\n" + section + m.group(1) + m.group(2), t)
    write("consulting/index.html", t.replace("\n", "\r\n") if crlf else t)

    # 3. breadcrumbs of the section roots (JSON-LD; the visible one comes from site_chrome.py)
    add_breadcrumb("formation/index.html", "formation", "Formation")
    add_breadcrumb("consulting/index.html", "consulting", "Conseil")

    # 4. links to the about pages -> the homepage (Person), the section root (url-map)
    for p in sorted(HOME.glob("formation/**/*.html")):
        rel = p.relative_to(HOME).as_posix()
        t = read(rel)
        new = t.replace(f"{APEX}/formation/a-propos.html", f"{APEX}/")
        if new != t:
            write(rel, new)
    m = read("_migration/url-map.csv")
    for sec in ("formation", "consulting"):
        m = once(rf"(https://{sec}\.arnaudlegout\.fr/a-propos\.html,){APEX}/{sec}/a-propos\.html",
                 lambda x, s=sec: x.group(1) + f"{APEX}/{s}/", m)
    write("_migration/url-map.csv", m)
    s = read("sitemap.xml")
    for sec in ("formation", "consulting"):
        s = once(rf"\n  <url>\s*<loc>{APEX}/{sec}/a-propos\.html</loc>.*?</url>\n", "", s)
    write("sitemap.xml", s)
    llms = read("llms.txt")
    for sec in ("formation", "consulting"):
        llms = once(rf"\n- \[[^\]]*\]\({APEX}/{sec}/a-propos\.html\)[^\n]*", "", llms)
    write("llms.txt", llms)

    # 5. the pages themselves
    subprocess.run(["git", "-C", str(HOME), "rm", "-q", "-f", "formation/a-propos.html", "consulting/a-propos.html"], check=True)


if __name__ == "__main__":
    main()
