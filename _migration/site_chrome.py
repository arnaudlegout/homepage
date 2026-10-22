"""Shared header, breadcrumb and footer of every page: their single source.

The site has no build step, so the navigation and footer are written into each page.
This script rewrites, in every page:
- <header class="header">...</header>: one navigation for the whole site (logo -> /,
  Formation and Conseil dropdowns, and in a section its action button), with the
  current section and page marked by aria-current;
- the visible breadcrumb of every section page, root included (<nav class="breadcrumb">),
  rendered from the page's JSON-LD BreadcrumbList, whose section names are set here too;
- <footer class="footer">...</footer>: one footer for the whole site;
- the burger script: the shared assets/js/nav.js instead of an inline copy;
- links inside the site: no target="_blank" (same site, same tab).

Links follow the site rules: relative inside a section and to the shared assets,
root-absolute to leave the section; 404.html is root-absolute throughout.
To change the navigation or the footer, edit the tables below and run:

    python _migration/site_chrome.py          # rewrite the pages
    python _migration/site_chrome.py --check  # fail if a page is not up to date
"""
import argparse
import html
import json
import posixpath
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HOME, TEMPLATE, pages  # noqa: E402

APEX = "https://arnaudlegout.fr"
SECTIONS = ("formation", "consulting")
# Where the breadcrumb goes: "header" (the logo becomes "Arnaud Legout / Section" in the
# menu bar) or "hero" (a full trail above the page title)
BREADCRUMB = "header"
SECTION_NAME = {"formation": "Formation", "consulting": "Conseil"}
FORMATION_MENU = [
    ("Data science", [("/formation/python-data-science-niveau-1.html", "Python data science — niveau 1"),
                      ("/formation/python-data-science-niveau-2.html", "Python data science — niveau 2"),
                      ("/formation/python-machine-learning.html", "Python machine learning")]),
    ("Compléments Python", [("/formation/python-niveau-1.html", "Python — niveau 1"),
                            ("/formation/python-avance.html", "Python — avancé")]),
]
CONSEIL_MENU = [("/consulting/audit-performance-cout-traitements-data.html", "Audit performance et coût"),
                ("/consulting/audit-agents-ia-data-science.html", "Audit des agents IA"),
                ("/consulting/revue-scientifique-analyses-data.html", "Revue scientifique des analyses")]
CTA = {"formation": ("/formation/contact.html", "Demander un devis", "Devis"),
       "consulting": ("/consulting/contact.html", "Demander un diagnostic", "Diagnostic")}
EXTERNAL = [("https://www-sop.inria.fr/members/Arnaud.Legout/", "Recherche Inria"),
            ("https://www.linkedin.com/in/arnaud-legout-866a404/", "LinkedIn"),
            ("https://scholar.google.com/citations?user=uGy5lroAAAAJ", "Google Scholar")]
BREADCRUMB_FALLBACK = {"formation/articles.html": [("Articles", None)]}

BLANK = ' target="_blank" rel="noopener"'


class Page:
    def __init__(self, rel):
        self.rel = rel
        self.section = rel.split("/")[0] if rel.split("/")[0] in SECTIONS else None
        self.path = "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
        self.dir = posixpath.dirname("/" + rel)
        self.absolute = rel == "404.html"  # served from any missing URL

    def link(self, target):
        """Inside the section: relative; elsewhere: root-absolute."""
        path, sep, frag = target.partition("#")
        if self.absolute or not self.section or not path.startswith(f"/{self.section}/"):
            return target
        rel = posixpath.relpath(path, self.dir)
        if path.endswith("/"):
            rel = "./" if rel == "." else rel + "/"
        return rel + sep + frag

    def asset(self, target):
        return target if self.absolute else posixpath.relpath(target, self.dir)

    def current(self, target):
        return ' aria-current="page"' if target == self.path else ""

    def typo(self, text):
        """French typography of the section: &nbsp; entity (formation, root) or U+00A0."""
        nb = " " if self.section == "consulting" else "&nbsp;"
        text = html.escape(text, quote=False)
        text = re.sub(r" ([:;!?»])", nb + r"\1", text)
        return re.sub(r"« ", "«" + nb, text)


def header(p, ind):
    def a(target, label, cls="", extra=""):
        c = f' class="{cls}"' if cls else ""
        return f'<a href="{p.link(target)}"{c}{p.current(target) or extra}>{p.typo(label)}</a>'

    def trigger(sec):
        # the section the page belongs to (its root included): aria-current="true"; the
        # page itself is marked once, by the breadcrumb or the dropdown
        inside = ' aria-current="true"' if p.section == sec else ""
        return f'<a href="{p.link(f"/{sec}/")}" class="nav__link"{inside}>{p.typo(SECTION_NAME[sec])}</a>'

    if BREADCRUMB == "header" and p.section:
        # breadcrumb landmark next to (not inside) the main navigation landmark
        brand = [f'{ind}    <nav class="nav__brand" aria-label="Fil d\'Ariane">',
                 f'{ind}      <ol>',
                 f'{ind}        <li>{a("/", "Arnaud Legout", "nav__logo")}</li>',
                 f'{ind}        <li>{a(f"/{p.section}/", SECTION_NAME[p.section], "nav__section")}</li>',
                 f'{ind}      </ol>',
                 f'{ind}    </nav>']
    else:
        brand = [f'{ind}    {a("/", "Arnaud Legout", "nav__logo")}']
    L = [f'{ind}<header class="header">',
         f'{ind}  <div class="nav container">',
         *brand,
         f'{ind}    <nav class="nav__menu" id="nav-menu" aria-label="Navigation principale">',
         f'{ind}      <ul class="nav__list">',
         f'{ind}        <li class="nav__item nav__item--has-dropdown">',
         f'{ind}          {trigger("formation")}',
         f'{ind}          <ul class="nav__dropdown">']
    for label, items in FORMATION_MENU:
        L.append(f'{ind}            <li class="nav__dropdown-label">{p.typo(label)}</li>')
        L += [f'{ind}            <li>{a(t, n)}</li>' for t, n in items]
    L += [f'{ind}          </ul>',
          f'{ind}        </li>',
          f'{ind}        <li class="nav__item nav__item--has-dropdown">',
          f'{ind}          {trigger("consulting")}',
          f'{ind}          <ul class="nav__dropdown">']
    L += [f'{ind}            <li>{a(t, n)}</li>' for t, n in CONSEIL_MENU]
    L += [f'{ind}          </ul>',
          f'{ind}        </li>']
    L += [f'{ind}      </ul>',
          f'{ind}    </nav>',
          f'{ind}    <div class="nav__actions">']
    if p.section:  # no action button at the root, whose role is to route to the sections
        target, long, short = CTA[p.section]
        L.append(f'{ind}      <a href="{p.link(target)}" class="nav__cta btn btn--primary"><span class="nav__cta-long">{p.typo(long)}</span><span class="nav__cta-short">{p.typo(short)}</span></a>')
    L += [f'{ind}      <button type="button" class="nav__burger" aria-label="Ouvrir le menu de navigation" aria-expanded="false" aria-controls="nav-menu">',
          *[f'{ind}        <span class="nav__burger-bar"></span>'] * 3,
          f'{ind}      </button>',
          f'{ind}    </div>',
          f'{ind}  </div>',
          f'{ind}</header>']
    return "\n".join(L)


def footer(p, ind):
    def li(target, label, external=False):
        href = target if external else p.link(target)
        return f'<li><a href="{href}"{BLANK if external else ""}>{p.typo(label)}</a></li>'

    def col(title, items, extra="", href=None):
        t = f'<a href="{p.link(href)}">{p.typo(title)}</a>' if href else p.typo(title)
        return [f'{ind}      <div class="footer__col">',
                f'{ind}        <p class="footer__col-title">{t}</p>', *extra,
                f'{ind}        <ul class="footer__link-list">',
                *[f'{ind}          {x}' for x in items],
                f'{ind}        </ul>',
                f'{ind}      </div>']
    formation = [li(t, n) for _, items in FORMATION_MENU for t, n in items]
    conseil = [li(t, n) for t, n in CONSEIL_MENU]
    L = [f'{ind}<footer class="footer">',
         f'{ind}  <div class="container">',
         f'{ind}    <div class="footer__grid">',
         *col("Arnaud Legout", [li("/", "Parcours")] + [li(u, n, True) for u, n in EXTERNAL],
              [f'{ind}        <p class="footer__tagline">Directeur de recherche Inria — Sophia Antipolis, France</p>']),
         *col("Formation", formation, href="/formation/"),
         *col("Conseil", conseil, href="/consulting/"),
         *col("Contact", [li("/formation/contact.html", "Contact formation"),
                          li("/consulting/contact.html", "Contact conseil"),
                          '<li><a href="mailto:arnaud.legout@gmail.com">Email</a></li>',
                          li("/mentions-legales.html", "Mentions légales")]),
         f'{ind}    </div>',
         f'{ind}    <div class="footer__bottom">',
         f'{ind}      <p>© 2026 Arnaud Legout. Site statique, sans cookie.</p>',
         f'{ind}    </div>',
         f'{ind}  </div>',
         f'{ind}</footer>']
    return "\n".join(L)


def name_breadcrumbs(text):
    """JSON-LD BreadcrumbList: the section roots carry the navigation names."""
    def sub(m):
        return m.group(1) + json.dumps(SECTION_NAME[m.group(4)], ensure_ascii=False) + m.group(2) + m.group(3)
    return re.sub(r'("name":\s*)"(?:[^"\\]|\\.)*"(\s*,\s*"item":\s*")(https://arnaudlegout\.fr/(formation|consulting)/)(?=")',
                  sub, text)


def trail(p, text):
    for body in re.findall(r'(?s)<script type="application/ld\+json">(.*?)</script>', text):
        data = json.loads(body)
        nodes = data.get("@graph", [data])
        for n in nodes:
            if n.get("@type") == "BreadcrumbList":
                return [(i["name"], i["item"][len(APEX):] if i["item"].startswith(APEX) else i["item"])
                        for i in sorted(n["itemListElement"], key=lambda i: i["position"])]
    if p.rel in BREADCRUMB_FALLBACK:
        return [("Arnaud Legout", "/"), (SECTION_NAME[p.section], f"/{p.section}/")] + BREADCRUMB_FALLBACK[p.rel]
    return None


def breadcrumb(p, items, ind):
    L = [f'{ind}<nav class="breadcrumb" aria-label="Fil d\'Ariane">', f'{ind}  <ol>']
    for k, (name, target) in enumerate(items):
        if k == len(items) - 1:
            L.append(f'{ind}    <li aria-current="page">{p.typo(name)}</li>')
        else:
            L.append(f'{ind}    <li><a href="{p.link(target)}">{p.typo(name)}</a></li>')
    L += [f'{ind}  </ol>', f'{ind}</nav>']
    return "\n".join(L)


def internal(href):
    return not re.match(r"^[a-z]+:|^//", href) or href.startswith(APEX)


def rewrite(rel):
    p = Page(rel)
    f = HOME / rel
    text = f.read_text(encoding="utf-8")
    crlf = "\r\n" in text
    t = text.replace("\r\n", "\n")

    t = name_breadcrumbs(t)
    t, n = re.subn(r'(?ms)^([ \t]*)<header class="header">.*?</header>', lambda m: header(p, m.group(1)), t)
    assert n == 1, (rel, "header", n)
    t, n = re.subn(r'(?ms)^([ \t]*)<footer class="footer">.*?</footer>', lambda m: footer(p, m.group(1)), t)
    assert n == 1, (rel, "footer", n)

    # breadcrumb in the page ("hero"): every page of the sections, first thing in the first
    # container of <main>, above the title (columns are aligned on the logo)
    t = re.sub(r'(?ms)\n[ \t]*<div class="breadcrumb-bar">.*?</nav>\s*</div>\s*</div>\n', "\n", t)
    t = re.sub(r'(?ms)\n[ \t]*<nav class="breadcrumb".*?</nav>\n', "", t)
    items = trail(p, t) if p.section and BREADCRUMB == "hero" else None
    if items:
        t, n = re.subn(r'(<main id="main">\s*(?:<!--.*?-->\s*)?<(?:div|section) class="[^"]*">\s*<div class="container[^"]*">)(\n)([ \t]*)',
                       lambda m: m.group(1) + "\n" + breadcrumb(p, items, m.group(3)) + "\n\n" + m.group(3), t, count=1)
        assert n == 1, (rel, "breadcrumb")

    # burger script: shared file, last thing before </body>
    t = re.sub(r"(?s)\n[ \t]*<script>\s*\(function \(\) \{\s*var btn = document\.querySelector\('\.nav__burger'\);.*?</script>", "", t)
    t = re.sub(r'\n[ \t]*<script src="[^"]*assets/js/nav\.js"></script>', "", t)
    t, n = re.subn(r"\n</body>", f'\n  <script src="{p.asset("/assets/js/nav.js")}"></script>\n</body>', t)
    assert n == 1, (rel, "body")

    # same site, same tab
    def same_tab(m):  # attributes may be split over several lines
        tag = m.group(0)
        href = re.search(r'href="([^"]*)"', tag)
        if href and internal(href.group(1)):
            tag = re.sub(r'\s+target="_blank"', "", tag)
            tag = re.sub(r'\s+rel="noopener(?: noreferrer)?"', "", tag)
        return tag
    t = re.sub(r"<a\s[^>]*>", same_tab, t)

    if crlf:
        t = t.replace("\n", "\r\n")
    return text, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale = []
    for rel in pages():
        old, new = rewrite(rel)
        if old != new:
            stale.append(rel)
            if not args.check:
                with open(HOME / rel, "w", encoding="utf-8", newline="") as f:
                    f.write(new)
    if args.check:
        print("site_chrome: up to date" if not stale else f"site_chrome: NOT up to date: {stale}")
        sys.exit(1 if stale else 0)
    print(f"site_chrome: {len(stale)} pages rewritten")


if __name__ == "__main__":
    main()
