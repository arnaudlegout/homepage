"""Check 4: the migration is content-neutral.

Old page (sibling working tree; homepage pages from the pre-migration tag) vs new page:
<title>, meta description, <h1>, and a hash of the visible body text outside
head/header/nav/footer/script/style. All identical, except the expected differences:
the D6 hostname labels and the D5 legal paragraph (printed as a diff).
Header, nav and footer text are compared too, separately: only link targets change there.
"""
import difflib
import hashlib
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import old_html, pages, parse, read  # noqa: E402

EXPECTED = {
    "index.html": "D6 hub card labels",
    "formation/contact.html": "D6 label",
    "consulting/a-propos.html": "D6 label",
    "consulting/audit-agents-ia-data-science.html": "D6 label",
    "mentions-legales.html": "D5 data paragraph",
}


def chrome_text(html):
    """Visible text of header/nav/footer only."""
    return [" ".join(re.sub(r"<[^>]+>", " ", t).split())
            for t in re.findall(r"(?is)<(header|footer)\b.*?</\1>", html)]


fail, rows = [], []
for rel in pages():
    old, new = parse(old_html(rel)), parse(read(rel))
    o_html, n_html = old_html(rel), read(rel)
    same = {
        "title": old.title == new.title,
        "description": old.meta.get("description") == new.meta.get("description"),
        "h1": old.h1 == new.h1,
        "body": hashlib.sha256("\n".join(old.text).encode()).digest() == hashlib.sha256("\n".join(new.text).encode()).digest(),
        "chrome": chrome_text(o_html) == chrome_text(n_html),
    }
    bad = [k for k, v in same.items() if not v]
    status = "identical" if not bad else ("expected: " + EXPECTED[rel] if rel in EXPECTED and bad == ["body"] else "DIFFERENT: " + ", ".join(bad))
    if rel in EXPECTED and not bad:
        status = "UNEXPECTEDLY identical (" + EXPECTED[rel] + ")"
    rows.append((rel, status))
    if status.startswith(("DIFFERENT", "UNEXPECTEDLY")):
        fail.append(rel)
    if bad:
        for k in bad:
            a = old.text if k == "body" else chrome_text(o_html) if k == "chrome" else [str(getattr(old, k, old.meta.get(k)))]
            b = new.text if k == "body" else chrome_text(n_html) if k == "chrome" else [str(getattr(new, k, new.meta.get(k)))]
            for line in difflib.unified_diff(a, b, f"old {rel} [{k}]", f"new {rel} [{k}]", n=0, lineterm=""):
                rows.append(("", "    " + line))

w = max(len(r) for r, _ in rows)
for rel, status in rows:
    print(f"{rel:<{w}}  {status}" if rel else status)
print("neutrality: OK" if not fail else f"neutrality: FAILED for {fail}")
sys.exit(1 if fail else 0)
