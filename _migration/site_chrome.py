"""Shared header, breadcrumb and footer of every page: their single source.

The site has no build step, so the navigation and footer are written into each page.
This script rewrites, in every page:
- <header class="header">...</header>: one navigation for the whole site (logo -> /,
  Formation, Conseil and Recherche dropdowns, and in a section its action button), with
  the current section and page marked by aria-current;
- the visible breadcrumb of every section page, root included (<nav class="breadcrumb">),
  rendered from the page's JSON-LD BreadcrumbList, whose section names are set here too;
- <footer class="footer">...</footer>: one footer for the whole site;
- the burger script: the shared assets/js/nav.js instead of an inline copy;
- links inside the site: no target="_blank" (same site, same tab);
- the <link rel="alternate" hreflang> of the pages that exist in both languages.

Two languages: French at the root, English under /en/ (to come) and /research/ (English
only). The language of a page comes from its path (lang_of); the header and footer are
written in that language, and a link to a page of the other language carries hreflang.
The English chrome links to the English version of a page when ALTERNATES has one, to
the French page otherwise. No visible language switcher yet (author's decision, until
the home page, training and consulting exist in English).

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
SECTIONS = ("research", "formation", "consulting")  # menu and footer order: research first
# Root of each section, per language (research exists in English only)
SECTION_ROOT = {"research": {"fr": "/research/", "en": "/research/"},
                "formation": {"fr": "/formation/", "en": "/en/training/"},
                "consulting": {"fr": "/consulting/", "en": "/en/consulting/"}}
# Where the breadcrumb goes: "header" (the logo becomes "Arnaud Legout / Section" in the
# menu bar) or "hero" (a full trail above the page title)
BREADCRUMB = "header"
# Pages that exist in both languages: (French path, English path). Each page of a pair
# gets <link rel="alternate" hreflang="fr|en|x-default">, the chrome of each language
# links to the page in its language, and the language switch links to the other one.
ALTERNATES = [
    ("/", "/en/"),
    ("/mentions-legales.html", "/en/legal-notice.html"),
    ("/formation/", "/en/training/"),
    ("/formation/python-data-science-niveau-1.html", "/en/training/python-data-science-level-1.html"),
    ("/formation/python-data-science-niveau-2.html", "/en/training/python-data-science-level-2.html"),
    ("/formation/python-machine-learning.html", "/en/training/python-machine-learning.html"),
    ("/formation/python-niveau-1.html", "/en/training/python-level-1.html"),
    ("/formation/python-avance.html", "/en/training/python-advanced.html"),
    ("/formation/contact.html", "/en/training/contact.html"),
    ("/consulting/", "/en/consulting/"),
    ("/consulting/audit-performance-cout-traitements-data.html", "/en/consulting/audit-performance-cost-data-processing.html"),
    ("/consulting/audit-agents-ia-data-science.html", "/en/consulting/audit-ai-agents-data-science.html"),
    ("/consulting/revue-scientifique-analyses-data.html", "/en/consulting/scientific-review-data-analyses.html"),
    ("/consulting/contact.html", "/en/consulting/contact.html"),
]
EN_OF = {fr: en for fr, en in ALTERNATES}
FR_OF = {en: fr for fr, en in ALTERNATES}
# Every label of the chrome, per language
T = {
    "fr": {"formation": "Formation", "consulting": "Conseil", "research": "Recherche",
           "breadcrumb": "Fil d'Ariane", "main_nav": "Navigation principale",
           "burger": "Ouvrir le menu de navigation",
           "contact": "Contact",
           "contact_formation": "Contact formation", "contact_consulting": "Contact conseil",
           "legal": "Mentions légales", "switch": ("EN", "English version of this page"),
           "copyright": "© 2026 Arnaud Legout. Site statique, sans cookie."},
    "en": {"formation": "Training", "consulting": "Consulting", "research": "Research",
           "breadcrumb": "Breadcrumb", "main_nav": "Main navigation",
           "burger": "Open the navigation menu",
           "contact": "Contact",
           "contact_formation": "Training contact", "contact_consulting": "Consulting contact",
           "legal": "Legal notice", "switch": ("FR", "Version française de cette page"),
           "copyright": "© 2026 Arnaud Legout. Static site, no cookies."},
}
SECTION_NAME = {lang: {s: T[lang][s] for s in SECTIONS} for lang in T}
# A label is a string (same in both languages) or {"fr": ..., "en": ...}
FORMATION_MENU = [
    ("Data science",
     [("/formation/python-data-science-niveau-1.html", {"fr": "Python data science — niveau 1", "en": "Python data science — level 1"}),
      ("/formation/python-data-science-niveau-2.html", {"fr": "Python data science — niveau 2", "en": "Python data science — level 2"}),
      ("/formation/python-machine-learning.html", "Python machine learning")]),
    ({"fr": "Compléments Python", "en": "Python essentials"},
     [("/formation/python-niveau-1.html", {"fr": "Python — niveau 1", "en": "Python — level 1"}),
      ("/formation/python-avance.html", {"fr": "Python — avancé", "en": "Python — advanced"})]),
]
CONSEIL_MENU = [("/consulting/audit-performance-cout-traitements-data.html", {"fr": "Audit performance et coût", "en": "Performance and cost audit"}),
                ("/consulting/audit-agents-ia-data-science.html", {"fr": "Audit des agents IA", "en": "AI agents audit"}),
                ("/consulting/revue-scientifique-analyses-data.html", {"fr": "Revue scientifique des analyses", "en": "Scientific review of analyses"})]
# Research (English only): a single Projects entry, to the projects section of
# /research/, which lists them all (author's decision)
RESEARCH_MENU = [
    (None, [("/research/publications.html", "Publications"),
            ("/research/#projects", {"fr": "Projets", "en": "Projects"}),
            ("/research/phdstudents.html", {"fr": "Conseils aux doctorants", "en": "Recommendations for Ph.D. students"})]),
]
CTA = {"formation": ("/formation/contact.html", {"fr": ("Demander un devis", "Devis"), "en": ("Request a quote", "Quote")}),
       "consulting": ("/consulting/contact.html", {"fr": ("Demander un diagnostic", "Diagnostic"), "en": ("Request a diagnostic", "Diagnostic")})}
BREADCRUMB_FALLBACK = {"formation/articles.html": [("Articles", None)]}

BLANK = ' target="_blank" rel="noopener"'


def lang_of(path):
    """Language of a page of the site, from its root-absolute path."""
    return "en" if path.startswith(("/en/", "/research/")) else "fr"


class Page:
    def __init__(self, rel, lang=None):
        self.rel = rel
        self.path = "/" + (rel[:-len("index.html")] if rel.endswith("index.html") else rel)
        self.dir = posixpath.dirname("/" + rel)
        self.absolute = rel == "404.html"  # served from any missing URL
        self.lang = lang or lang_of(self.path)
        self.t = T[self.lang]
        self.section = next((s for s in SECTIONS if self.path.startswith(SECTION_ROOT[s][self.lang])), None)
        self.root = SECTION_ROOT[self.section][self.lang] if self.section else None

    def link(self, target):
        """Inside the section: relative; elsewhere: root-absolute."""
        path, sep, frag = target.partition("#")
        if self.absolute or not self.section or not path.startswith(self.root):
            return target
        rel = posixpath.relpath(path, self.dir)
        if path.endswith("/"):
            rel = "./" if rel == "." else rel + "/"
        return rel + sep + frag

    def local(self, target):
        """The version of a page of the site in the language of this page, if it exists."""
        path, sep, frag = target.partition("#")
        return (EN_OF.get(path, path) if self.lang == "en" else path) + sep + frag

    def other(self):
        """The language switch: this page in the other language, or that language's home."""
        if self.lang == "fr":
            return EN_OF.get(self.path, EN_OF.get("/", "/"))
        return FR_OF.get(self.path, "/")

    def hreflang(self, target):
        """hreflang on a link to a page of the site in the other language."""
        lang = lang_of(target)
        return f' hreflang="{lang}"' if lang != self.lang else ""

    def asset(self, target):
        return target if self.absolute else posixpath.relpath(target, self.dir)

    def current(self, target):
        return ' aria-current="page"' if target == self.path else ""

    def typo(self, text):
        """French typography of the section: &nbsp; entity (formation, root) or U+00A0."""
        if isinstance(text, dict):
            text = text[self.lang]
        text = html.escape(text, quote=False)
        if self.lang == "en":
            return text
        nb = " " if self.section == "consulting" else "&nbsp;"
        text = re.sub(r" ([:;!?»])", nb + r"\1", text)
        return re.sub(r"« ", "«" + nb, text)


def header(p, ind):
    def a(target, label, cls="", extra=""):
        if re.match(r"^https?:", target):
            return f'<a href="{target}"{BLANK}>{p.typo(label)}</a>'
        target = p.local(target)
        c = f' class="{cls}"' if cls else ""
        return f'<a href="{p.link(target)}"{c}{p.hreflang(target)}{p.current(target) or extra}>{p.typo(label)}</a>'

    def trigger(sec):
        # the section the page belongs to (its root included): aria-current="true"; the
        # page itself is marked once, by the breadcrumb or the dropdown
        inside = ' aria-current="true"' if p.section == sec else ""
        target = p.local(SECTION_ROOT[sec]["fr"])
        return (f'<a href="{p.link(target)}" class="nav__link"{p.hreflang(target)}{inside}>'
                f'{p.typo(SECTION_NAME[p.lang][sec])}</a>')

    def dropdown(sec, groups):  # sec: the French root of a section, e.g. "formation"
        L = [f'{ind}        <li class="nav__item nav__item--has-dropdown">',
             f'{ind}          {trigger(sec)}',
             f'{ind}          <ul class="nav__dropdown">']
        for label, items in groups:
            if label:
                L.append(f'{ind}            <li class="nav__dropdown-label">{p.typo(label)}</li>')
            L += [f'{ind}            <li>{a(t, n)}</li>' for t, n in items]
        return L + [f'{ind}          </ul>',
                    f'{ind}        </li>']

    if BREADCRUMB == "header" and p.section:
        # breadcrumb landmark next to (not inside) the main navigation landmark
        brand = [f'{ind}    <nav class="nav__brand" aria-label="{html.escape(p.t["breadcrumb"], quote=False)}">',
                 f'{ind}      <ol>',
                 f'{ind}        <li>{a("/", "Arnaud Legout", "nav__logo")}</li>',
                 f'{ind}        <li>{a(SECTION_ROOT[p.section]["fr"], SECTION_NAME[p.lang][p.section], "nav__section")}</li>',
                 f'{ind}      </ol>',
                 f'{ind}    </nav>']
    else:
        brand = [f'{ind}    {a("/", "Arnaud Legout", "nav__logo")}']
    L = [f'{ind}<header class="header">',
         f'{ind}  <div class="nav container">',
         *brand,
         f'{ind}    <nav class="nav__menu" id="nav-menu" aria-label="{p.t["main_nav"]}">',
         f'{ind}      <ul class="nav__list">',
         *dropdown("research", RESEARCH_MENU),
         *dropdown("formation", FORMATION_MENU),
         *dropdown("consulting", [(None, CONSEIL_MENU)]),
         f'{ind}      </ul>',
         f'{ind}    </nav>',
         f'{ind}    <div class="nav__actions">']
    if p.section in CTA:  # no action button at the root, whose role is to route to the sections
        target, labels = CTA[p.section]
        long, short = labels[p.lang]
        L.append(f'{ind}      <a href="{p.link(p.local(target))}" class="nav__cta btn btn--primary"><span class="nav__cta-long">{p.typo(long)}</span><span class="nav__cta-short">{p.typo(short)}</span></a>')
    code, label = p.t["switch"]
    other = "fr" if p.lang == "en" else "en"
    if p.section != "research":  # research is in English only: no switch (author's decision)
        L.append(f'{ind}      <a href="{p.other()}" class="nav__lang" hreflang="{other}" lang="{other}" aria-label="{label}">{code}</a>')
    L += [f'{ind}      <button type="button" class="nav__burger" aria-label="{p.t["burger"]}" aria-expanded="false" aria-controls="nav-menu">',
          *[f'{ind}        <span class="nav__burger-bar"></span>'] * 3,
          f'{ind}      </button>',
          f'{ind}    </div>',
          f'{ind}  </div>',
          f'{ind}</header>']
    return "\n".join(L)


def footer(p, ind):
    def li(target, label):
        target = p.local(target)
        return f'<li><a href="{p.link(target)}"{p.hreflang(target)}>{p.typo(label)}</a></li>'

    def col(title, items, href=None):
        if href:
            href = p.local(href)
            title = f'<a href="{p.link(href)}"{p.hreflang(href)}>{p.typo(title)}</a>'
        else:
            title = p.typo(title)
        return [f'{ind}      <div class="footer__col">',
                f'{ind}        <p class="footer__col-title">{title}</p>',
                f'{ind}        <ul class="footer__link-list">',
                *[f'{ind}          {x}' for x in items],
                f'{ind}        </ul>',
                f'{ind}      </div>']
    # one column per section, as in the menu bar, then Contact
    formation = [li(t, n) for _, items in FORMATION_MENU for t, n in items]
    conseil = [li(t, n) for t, n in CONSEIL_MENU]
    research = [li(t, n) for _, items in RESEARCH_MENU for t, n in items]
    t = p.t
    L = [f'{ind}<footer class="footer">',
         f'{ind}  <div class="container">',
         f'{ind}    <div class="footer__grid">',
         *col(t["research"], research, href="/research/"),
         *col(t["formation"], formation, href="/formation/"),
         *col(t["consulting"], conseil, href="/consulting/"),
         *col(t["contact"], [li("/formation/contact.html", t["contact_formation"]),
                             li("/consulting/contact.html", t["contact_consulting"]),
                             '<li><a href="mailto:arnaud.legout@gmail.com">Email</a></li>',
                             li("/mentions-legales.html", t["legal"])]),
         f'{ind}    </div>',
         f'{ind}    <div class="footer__bottom">',
         f'{ind}      <p>{p.typo(t["copyright"])}</p>',
         f'{ind}    </div>',
         f'{ind}  </div>',
         f'{ind}</footer>']
    return "\n".join(L)


def alternates(p, text):
    """<link rel="alternate" hreflang> right after the canonical, for the pages of ALTERNATES."""
    text = re.sub(r'\n[ \t]*<link rel="alternate" hreflang="[^"]*" href="[^"]*">', "", text)
    pair = next(((fr, en) for fr, en in ALTERNATES if p.path in (fr, en)), None)
    if not pair:
        return text
    links = [("fr", pair[0]), ("en", pair[1]), ("x-default", pair[0])]

    def add(m):
        return m.group(0) + "".join(f'\n{m.group(1)}<link rel="alternate" hreflang="{h}" href="{APEX}{u}">'
                                    for h, u in links)
    text, n = re.subn(r'(?m)^([ \t]*)<link rel="canonical" href="[^"]*">', add, text, count=1)
    assert n == 1, (p.rel, "canonical for hreflang")
    return text


def name_breadcrumbs(p, text):
    """JSON-LD BreadcrumbList: the section roots carry the navigation names."""
    roots = {r: s for s in SECTIONS for r in SECTION_ROOT[s].values()}

    def sub(m):
        return m.group(1) + json.dumps(SECTION_NAME[p.lang][roots[m.group(4)]], ensure_ascii=False) + m.group(2) + m.group(3)
    return re.sub(r'("name":\s*)"(?:[^"\\]|\\.)*"(\s*,\s*"item":\s*")(https://arnaudlegout\.fr(/(?:en/training|en/consulting|formation|consulting|research)/))(?=")',
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
        return [("Arnaud Legout", p.local("/")), (SECTION_NAME[p.lang][p.section], p.root)] + BREADCRUMB_FALLBACK[p.rel]
    return None


def breadcrumb(p, items, ind):
    L = [f'{ind}<nav class="breadcrumb" aria-label="{html.escape(p.t["breadcrumb"], quote=False)}">', f'{ind}  <ol>']
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

    t = name_breadcrumbs(p, t)
    t = alternates(p, t)
    # 404.html (one file for every missing URL) also carries the English chrome in
    # <template> elements, which nav.js swaps in for English URLs: set apart here, rebuilt below
    t = re.sub(r'(?s)\n[ \t]*<template data-chrome="[^"]*">.*?</template>', "", t)
    t, n = re.subn(r'(?ms)^([ \t]*)<header class="header">.*?</header>', lambda m: header(p, m.group(1)), t)
    assert n == 1, (rel, "header", n)
    t, n = re.subn(r'(?ms)^([ \t]*)<footer class="footer">.*?</footer>', lambda m: footer(p, m.group(1)), t)
    assert n == 1, (rel, "footer", n)
    if p.absolute:
        en = Page(rel, lang="en")
        templates = (f'\n  <template data-chrome="header-en">\n{header(en, "  ")}\n  </template>'
                     f'\n  <template data-chrome="footer-en">\n{footer(en, "  ")}\n  </template>')
        t, n = re.subn(r"(?m)^(  </footer>)$", lambda m: m.group(1) + templates, t, count=1)
        assert n == 1, (rel, "templates")

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
