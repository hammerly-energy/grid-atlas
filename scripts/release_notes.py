"""Print release notes (Markdown) for HEAD compared with a previous tag.

    python3 scripts/release_notes.py            # first release: coverage summary
    python3 scripts/release_notes.py v1.2       # changes since v1.2

Data changes come from web/data.json at each ref; the commit list from git log.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def data_at(ref):
    """-> parsed web/data.json at a git ref (None = working tree), or {} if it isn't there."""
    try:
        return json.loads(git("show", f"{ref}:web/data.json") if ref else (ROOT / "web/data.json").read_text())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}


def summary(m):
    """-> {edges: {id: status}, setups: set, utilities: set} for one market.

    An edge id can appear in several setups; it counts once, and as verified only if every copy is."""
    edges = {}
    for p in [m["base"], *m["archetypes"].values()]:
        for e in p.get("edges", []):
            edges[e["id"]] = "verified" if edges.get(e["id"], "verified") == "verified" == e["status"] else "needs_verification"
    return {"edges": edges, "setups": set(m["archetypes"]), "utilities": set(m["utilities"])}


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else many or one + 's'}"


def coverage(new):
    lines = []
    for mid, m in sorted(new.get("markets", {}).items(), key=lambda kv: kv[1]["name"]):
        s = summary(m)
        verified = sum(v == "verified" for v in s["edges"].values())
        lines.append(f"- {m['name']}: {plural(len(s['setups']), 'customer setup')}, {plural(len(s['utilities']), 'utility', 'utilities')}, "
                     f"{plural(len(s['edges']), 'relationship')} ({verified} checked against a primary source).")
    return lines


def data_changes(old, new):
    lines, om, nm = [], old.get("markets", {}), new.get("markets", {})
    for mid in sorted(set(om) | set(nm), key=lambda k: (nm.get(k) or om[k])["name"]):
        name = (nm.get(mid) or om[mid])["name"]
        if mid not in om:
            lines.append(f"- {name}: added.")
            continue
        if mid not in nm:
            lines.append(f"- {name}: removed.")
            continue
        a, b = summary(om[mid]), summary(nm[mid])
        added, removed = b["edges"].keys() - a["edges"].keys(), a["edges"].keys() - b["edges"].keys()
        kept = a["edges"].keys() & b["edges"].keys()
        newly = sum(a["edges"][i] != "verified" and b["edges"][i] == "verified" for i in kept)
        unver = sum(a["edges"][i] == "verified" and b["edges"][i] != "verified" for i in kept)
        bits = [f"{n} {what}" for n, what in [
            (len(added), "relationships added"), (len(removed), "relationships removed"),
            (newly, "newly checked against a primary source"), (unver, "moved back to needs verification")] if n]
        bits += [f"setup added: {s}" for s in sorted(b["setups"] - a["setups"])]
        bits += [f"setup removed: {s}" for s in sorted(a["setups"] - b["setups"])]
        bits += [f"utility added: {u}" for u in sorted(b["utilities"] - a["utilities"])]
        bits += [f"utility removed: {u}" for u in sorted(a["utilities"] - b["utilities"])]
        if om[mid]["name"] != nm[mid]["name"]:
            bits.append(f"renamed from {om[mid]['name']}")
        if bits:
            lines.append(f"- {name}: " + "; ".join(bits) + ".")
    return lines


def main(prev=None):
    new = data_at(None)
    if not prev:
        print("First release.\n\n## Coverage\n")
        print("\n".join(coverage(new)))
        return
    out = ["## Data", *(data_changes(data_at(prev), new) or ["No data changes."])]
    commits = [c for c in git("log", f"{prev}..HEAD", "--no-merges", "--format=%s").splitlines() if c.strip()]
    out += ["", "## Commits", *(f"- {c}" for c in commits)]
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
