import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
pats = {
 "formation.host": r"formation\.arnaudlegout\.fr",
 "consulting.host": r"consulting\.arnaudlegout\.fr",
 "github.io": r"github\.io",
 "apex abs": r"https://arnaudlegout\.fr(?![\w.-]*\.arnaudlegout)",
 "../": r"\.\./",
 "href index.html": r"(?:href|src)=\"[^\"]*index\.html[^\"]*\"",
 "href formations/": r"href=\"(?:\.\./)?formations/",
 "href root-abs /x": r"(?:href|src)=\"/(?!/)",
 "//gc.zgo.at": r"src=\"//gc\.zgo\.at/count\.js\"",
}
cols = list(pats)
print("file".ljust(48) + "".join(c[:14].rjust(15) for c in cols))
tot = dict.fromkeys(cols, 0)
for repo in ["homepage", "formation-consulting", "consulting"]:
    for p in sorted((root/repo).rglob("*")):
        rel = p.relative_to(root/repo).as_posix()
        if not p.is_file() or rel.startswith((".git/", ".claude/", "_migration/")) or p.suffix not in {".html",".txt",".xml",".css",".js"} or p.name in {"CLAUDE.md"}:
            continue
        t = p.read_text(encoding="utf-8")
        row = [len(re.findall(pats[c], t)) for c in cols]
        for c, n in zip(cols, row): tot[c] += n
        print(f"{repo}/{rel}".ljust(48) + "".join(str(n).rjust(15) for n in row))
print("TOTAL".ljust(48) + "".join(str(tot[c]).rjust(15) for c in cols))
