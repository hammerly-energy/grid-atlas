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


def load_maps(root=ROOT):
    """-> {map_id: map}; data/maps/<map>.json is built by scripts/maps/make_maps.mjs. One map per region."""
    return {f.stem: json.loads(f.read_text()) for f in sorted((root / "data/maps").glob("*.json"))}


def map_for(maps, cc):
    """The region map that serves country `cc`."""
    found = [m for m in maps.values() if cc in m["countries"]]
    assert len(found) == 1, f"{cc}: {len(found)} maps serve this country"
    return found[0]


def map_area_ids(m):
    """Every id a domain_area may name: drawn areas plus groups of them."""
    return {a for l in m["layers"] for a in l["areas"]} | set(m.get("groups", {}))


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


def _walk(edges, cls, comp, sub):
    """Trace one line item back from consumer `cls`. Hops labelled `sub` win; unlabelled hops are shared by every item.
    -> (item or None, path, None or (problem, True if it is an ambiguity among lines labelled `sub`))."""
    path, node, seen = [], cls, set()
    while node not in seen:
        seen.add(node)
        into = [e for e in edges if e["type"] == "sets_rate" and e["to"] == node and _applies(e, cls)
                and e.get("rate_component") == comp and e.get("mode", "sets") != "caps"]
        cands = [e for e in into if e.get("subcomponent") == sub]
        if not cands and sub is not None:
            cands = [e for e in into if not e.get("subcomponent")]
        if len(cands) > 1:
            mine = cands[0].get("subcomponent") == sub      # ambiguity among this item's own lines, not shared ones
            return None, path, (f"{node}: {len(cands)} lines for {sub or 'the default item'}", mine)
        if not cands:
            split = sub is None and into          # only labelled items continue from here: not a dead end
            return None, path, None if not path or split else (f"{node}: dead end", False)
        e = cands[0]; path.append(e["id"])
        if e.get("mode", "sets") in SETTER_MODES:
            on_path = {x["from"] for x in edges if x["id"] in path}
            limits = [c["id"] for c in edges if c.get("mode") in ("caps", "approves") and c["id"] not in path
                      and c["to"] in on_path and _applies(c, cls) and c.get("rate_component") == comp]
            return {"subcomponent": sub, "path": path, "setter": e["from"], "mode": e.get("mode", "sets"), "limits": limits}, path, None
        node = e["from"]
    return None, path, (f"{node}: cycle", False)


def line_items(edges, cls, comp):
    """A bill line is one or more line items (edge `subcomponent`), each with exactly one path to one setter.
    -> (items, problems). An empty `problems` with at least one item means the line is complete."""
    subs = sorted({e["subcomponent"] for e in edges if e["type"] == "sets_rate" and e.get("subcomponent")
                   and e.get("rate_component") == comp and _applies(e, cls)})
    items, problems = [], []
    for sub in [None, *subs]:
        item, path, problem = _walk(edges, cls, comp, sub)
        owns = sub is None or any(x.get("subcomponent") == sub for x in edges if x["id"] in path)
        if problem and (owns or problem[1]):
            problems.append(problem[0])
        if item and owns:
            items.append(item)
    by_id, own = {e["id"]: e for e in edges}, {it["subcomponent"] for it in items}

    def belongs(c, it):   # a labelled limit goes to its own item, or to every item it touches when its label has no item
        sub = by_id[c].get("subcomponent")
        return sub in (None, it["subcomponent"]) or sub not in own
    for it in items:
        it["limits"] = [c for c in it["limits"] if belongs(c, it) and not any(c in o["path"] for o in items)]
    return items, problems


def whole_bill_caps(edges, cls, items):
    """A cap with no component is a ceiling on the whole bill (GB default tariff cap), not a limit on each line item."""
    on_path = {x["from"] for x in edges for it in items if x["id"] in it["path"]}
    return [c["id"] for c in edges if c.get("mode") == "caps" and not c.get("rate_component")
            and c["to"] in on_path and _applies(c, cls)]


def answer(edges, cls, comp):
    """-> {"items": [{subcomponent, path, setter, mode, limits}], "whole_bill_caps": [...]} or None if incomplete."""
    items, problems = line_items(edges, cls, comp)
    if not items or problems:
        return None                          # gap or ambiguity: tests report it
    return {"items": items, "whole_bill_caps": whole_bill_caps(edges, cls, items)}


def who_sets(edges, cls, comp):
    """The single line item of a bill line, for claims about lines that have one setter; None if 0 or several."""
    a = answer(edges, cls, comp)
    if not a or len(a["items"]) != 1:
        return None
    return a["items"][0] | {"whole_bill_caps": a["whole_bill_caps"]}


def compile_all(data, maps=None):
    out = {"schema_version": 2, "countries": {}, "markets": {}, "answers": {}, "maps": maps or {}}
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
                        a = answer(edges, cls, comp)
                        if a:   # key: market|archetype|class|component -> cross-country compare is a lookup
                            out["answers"][f"{mid}|{arch}|{cls}|{comp}"] = a
    return out


def main():
    compiled = compile_all(load(), load_maps())
    js = json.dumps(compiled, separators=(",", ":"), ensure_ascii=False)   # keep YAML order: the first utility listed is the default
    (ROOT / "web/data.json").write_text(js)
    (ROOT / "web/data.js").write_text("window.GRID_ATLAS=" + js + ";\n")
    print(f"wrote web/data.json + web/data.js ({len(js)/1024:.1f} KB), {len(compiled['markets'])} markets, {len(compiled['answers'])} answers")


if __name__ == "__main__":
    sys.exit(main())
