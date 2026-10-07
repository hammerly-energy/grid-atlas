import pytest
from conftest import DATA, graphs

GRAPHS = list(graphs())
IDS = [f"{g[1]}:{g[2]}" for g in GRAPHS]

@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=IDS)
def test_edges_resolve(cc, mid, arch, nodes, edges):
    bad = [e["id"] for e in edges if e["from"] not in nodes or e["to"] not in nodes]
    assert not bad, f"{mid}:{arch} dangling edges {bad}"

@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=IDS)
def test_edge_ids_unique(cc, mid, arch, nodes, edges):
    ids = [e["id"] for e in edges]
    assert len(ids) == len(set(ids))

@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=IDS)
def test_consumer_nodes_are_country_classes(cc, mid, arch, nodes, edges):
    classes = set(DATA[cc]["profile"]["consumer_classes"])
    assert {n["id"] for n in nodes.values() if n["kind"] == "consumer"} <= classes

def test_utilities_reference_real_archetypes_and_slots():
    for cc, c in DATA.items():
        for mid, m in c["markets"].items():
            slots = {n["slot"] for layer in [m["base"], *m["archetypes"].values()]
                     for n in layer.get("nodes", []) if "slot" in n}
            for name, u in m["utilities"].items():
                assert set(u["archetypes"]) <= set(m["archetypes"]), f"{mid}/{name}"
                assert set(u.get("fills", {})) <= slots, f"{mid}/{name} fills unknown slot"

def test_every_ownership_claim_has_a_source():
    """Schema enforces this too; the test makes the rule visible and covers utility fills."""
    missing = []
    for cc, mid, arch, nodes, edges in GRAPHS:
        for n in nodes.values():
            if n.get("holds_assets") and not n.get("source"):
                missing.append(f"{mid}:{n['id']} holds_assets")
            if "owner" in n and not n["owner"].get("source", {}).get("url"):
                missing.append(f"{mid}:{n['id']} owner")
    for c in DATA.values():
        for mid, m in c["markets"].items():
            for name, u in m["utilities"].items():
                for slot, f in u.get("fills", {}).items():
                    if isinstance(f, dict) and "owner" in f and not f["owner"]["source"].get("url"):
                        missing.append(f"{mid}/{name}:{slot}")
    assert not missing, missing
