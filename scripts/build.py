"""Compile data/countries/<cc>/{_country,<market>}.yaml -> web/data.json + web/data.js.

data.js exists because fetch('data.json') fails from file:// in Chrome and Firefox.
"""
import json, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "data/schema.json").read_text())
MARKET_V = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
COUNTRY_V = Draft202012Validator({"$ref": "#/$defs/country_profile", "$defs": SCHEMA["$defs"]},
                                 format_checker=FormatChecker())
SETTER_MODES = {"sets", "approves", "levies", "market"}   # a path must end at one of these


def load(root=ROOT):
    """-> {cc: {"profile": {...}, "markets": {market_id: {...}}}}; raises on schema errors."""
    out, errors = {}, []
    for cdir in sorted((root / "data/countries").iterdir()):
        prof = yaml.safe_load((cdir / "_country.yaml").read_text())
        errors += [f"{cdir.name}/_country.yaml: {e.json_path}: {e.message}" for e in COUNTRY_V.iter_errors(prof)]
        markets = {}
        for f in sorted(cdir.glob("[!_]*.yaml")):
            m = yaml.safe_load(f.read_text())
            errors += [f"{cdir.name}/{f.name}: {e.json_path}: {e.message}" for e in MARKET_V.iter_errors(m)]
            if m.get("country") != prof.get("country") or cdir.name != str(prof.get("country", "")).lower():
                errors.append(f"{f}: country mismatch with folder/profile")
            markets[m["market"]] = m
        out[prof["country"]] = {"profile": prof, "markets": markets}
    if errors:
        raise SystemExit("schema errors:\n  " + "\n  ".join(errors))
    return out


def resolve(market, archetype):
    """base + archetype - removes, plus owns edges derived from owner.node. -> (nodes_by_id, edges)."""
    arch = market["archetypes"][archetype]
    drop = set(arch.get("removes", []))
    nodes = {n["id"]: n for n in market["base"].get("nodes", []) + arch.get("nodes", []) if n["id"] not in drop}
    edges = [e for e in market["base"].get("edges", []) + arch.get("edges", []) if e["id"] not in drop]
    for n in nodes.values():
        o = n.get("owner", {})
        if o.get("node"):
            edges.append({"id": f"owns_{o['node']}_{n['id']}", "from": o["node"], "to": n["id"], "type": "owns",
                          "asset": (n.get("holds_assets") or ["generation"])[0], "label": "owns",
                          "source": o["source"], "status": "needs_verification", "derived": True})
    return nodes, edges


def bill_components(profile, market):
    """A market may override its country's bill components (ERCOT has no capacity)."""
    return market.get("bill_components") or profile["bill_components"]


def _applies(e, cls):
    return not e.get("applies_to") or cls in e["applies_to"]


def who_sets(edges, cls, comp):
    """Walk back from consumer `cls` through passes_through edges. -> {"path": [edge ids], "setter", "mode", "limits": [caps/approves edge ids]} or None."""
    def into(node):
        return [e for e in edges if e["type"] == "sets_rate" and e["to"] == node and _applies(e, cls)
                and e.get("rate_component") == comp and e.get("mode", "sets") != "caps"]
    path, node, seen = [], cls, set()
    while node not in seen:
        seen.add(node)
        cands = into(node)
        if len(cands) != 1:
            return None                      # gap or ambiguity: tests report it
        e = cands[0]; path.append(e["id"])
        if e.get("mode", "sets") in SETTER_MODES:
            on_path = {x["from"] for x in edges if x["id"] in path}
            limits = [c["id"] for c in edges if c.get("mode") in ("caps", "approves") and c["id"] not in path
                      and c["to"] in on_path and _applies(c, cls) and c.get("rate_component") in (None, comp)]
            return {"path": path, "setter": e["from"], "mode": e.get("mode", "sets"), "limits": limits}
        node = e["from"]
    return None                              # cycle


def compile_all(data):
    out = {"schema_version": 2, "countries": {}, "markets": {}, "answers": {}}
    for cc, c in data.items():
        p = c["profile"]
        out["countries"][cc] = {k: p[k] for k in ("name", "currency", "lanes", "chain", "glossary", "bill_components", "consumer_classes")} | \
            {k: p.get(k, {}) for k in ("kind_labels", "jurisdiction_labels", "component_labels")}
        for mid, m in c["markets"].items():
            out["markets"][mid] = m                            # layered form; JS composes base+archetype
            for arch in m["archetypes"]:
                _, edges = resolve(m, arch)
                for cls in p["consumer_classes"]:
                    for comp in bill_components(p, m):
                        a = who_sets(edges, cls, comp)
                        if a:   # key: market|archetype|class|component -> cross-country compare is a lookup
                            out["answers"][f"{mid}|{arch}|{cls}|{comp}"] = a
    return out


def main():
    compiled = compile_all(load())
    js = json.dumps(compiled, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    (ROOT / "web/data.json").write_text(js)
    (ROOT / "web/data.js").write_text("window.GRID_ATLAS=" + js + ";\n")
    print(f"wrote web/data.json + web/data.js ({len(js)/1024:.1f} KB), {len(compiled['markets'])} markets, {len(compiled['answers'])} answers")


if __name__ == "__main__":
    sys.exit(main())
