"""Regional facts as assertions. Wrong data fails a test instead of drawing a wrong diagram.

Claims about markets whose data isn't entered yet are marked xfail(strict=True) with the
milestone that will satisfy them. When the data lands the test passes, strict xfail turns
that into a failure, and whoever entered the data deletes the marker. Gaps trend to zero.
"""
import pytest
import build
from conftest import DATA, graphs

GRAPHS = list(graphs())
MARKETS = {mid: (cc, m) for cc, c in DATA.items() for mid, m in c["markets"].items()}

M2 = pytest.mark.xfail(reason="milestone 2: ERCOT data not entered", strict=True)
M3 = pytest.mark.xfail(reason="milestone 3: PJM/CAISO data not entered", strict=True)
MGB = pytest.mark.xfail(reason="GB milestone: gb.yaml not entered", strict=True)


def g(mid, arch):
    """Resolved (nodes, edges) for one archetype; fails if it doesn't exist yet."""
    m = MARKETS[mid][1]
    assert arch in m["archetypes"], f"{mid}:{arch} not entered"
    return build.resolve(m, arch)


def all_graphs(mid):
    found = [(a, n, e) for _, m, a, n, e in GRAPHS if m == mid]
    assert found, f"{mid}: no archetypes entered"
    return found


def by_kind(nodes, kind):
    return [n for n in nodes.values() if n["kind"] == kind]


# ---- completeness: every class x bill component has a path ending at a setter ----
# (market, archetype, class) -> reason. Each entry is a strict xfail; delete it once fixed.
KNOWN_GAPS = {}


def _bill_cases():
    for cc, mid, arch, nodes, edges in GRAPHS:
        prof, m = DATA[cc]["profile"], MARKETS[mid][1]
        for cls in prof["consumer_classes"]:
            for comp in build.bill_components(prof, m):
                reason = KNOWN_GAPS.get((mid, arch, cls))
                marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
                yield pytest.param(mid, arch, cls, comp, edges, marks=marks, id=f"{mid}:{arch}:{cls}:{comp}")


@pytest.mark.parametrize("mid,arch,cls,comp,edges", list(_bill_cases()))
def test_complete_bill_path(mid, arch, cls, comp, edges):
    assert build.who_sets(edges, cls, comp), f"no unique path to a setter for {cls}/{comp} in {mid}:{arch}"


# ---- mode and ownership invariants (all countries) ----
@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=[f"{x[1]}:{x[2]}" for x in GRAPHS])
def test_mode_and_ownership_rules(cc, mid, arch, nodes, edges):
    for e in edges:
        src, dst = nodes[e["from"]], nodes[e["to"]]
        if e.get("mode") == "caps":
            assert src["kind"] == "regulator", f"{e['id']}: only regulators cap prices"
        if e.get("mode") == "levies":
            assert src["kind"] in {"regulator", "policy_maker", "legislature", "scheme_administrator"}, e["id"]
        if e.get("mode") == "passes_through":
            assert src["lane"] == "retail", f"{e['id']}: pass-through is a retail-billing act"
        if e["type"] == "owns":
            assert dst.get("holds_assets"), f"{e['id']}: owns must target an asset-holding node"
            assert e["asset"] in dst["holds_assets"], e["id"]


@pytest.mark.parametrize("cc,mid,arch,nodes,edges", GRAPHS, ids=[f"{x[1]}:{x[2]}" for x in GRAPHS])
def test_operators_own_no_assets(cc, mid, arch, nodes, edges):
    """ISOs and NESO operate the grid; transmission owners own it."""
    for n in by_kind(nodes, "iso") + by_kind(nodes, "system_operator"):
        assert not n.get("holds_assets"), n["id"]
        assert not [e for e in edges if e["type"] == "owns" and e["from"] == n["id"]], n["id"]


def test_every_edge_has_a_source_url():
    missing = [f"{mid}:{e['id']}" for _, mid, _, _, edges in GRAPHS for e in edges if not e["source"].get("url")]
    assert not missing, missing


def test_report_needs_verification():
    n = sum(e.get("status") == "needs_verification" for *_, edges in GRAPHS for e in edges)
    empty = [mid for mid, (_, m) in MARKETS.items() if not m["archetypes"]]
    print(f"needs_verification edges: {n}; markets with no archetypes yet: {empty}")   # never fails


# ---- coverage claims (hold even on empty data) ----
@pytest.mark.parametrize("mid,utility", [
    ("pjm", "LG&E"), ("pjm", "KU"), ("pjm", "Ameren Illinois"),           # MISO / not PJM
    ("ercot", "El Paso Electric"), ("ercot", "SPS"), ("ercot", "Entergy Texas"),  # Texas, not ERCOT
])
def test_utility_not_in_market(mid, utility):
    assert utility not in MARKETS[mid][1]["utilities"]


def test_gb_market_excludes_northern_ireland():
    assert "Northern Ireland" in MARKETS["gb"][1]["coverage_note"]
    assert not [u for u in MARKETS["gb"][1]["utilities"].values() if u["area"] in {"NI", "Northern Ireland"}]


# ---- ERCOT ----
@M2
def test_ercot_has_no_capacity_market():
    for arch, nodes, edges in all_graphs("ercot"):
        assert not [e for e in edges if e.get("rate_component") == "capacity"], arch
        assert not by_kind(nodes, "market") or all("capacity" not in n["id"] for n in by_kind(nodes, "market"))


@M2
def test_ercot_ferc_does_not_regulate_rates_or_market_rules():
    """ERCOT is intrastate: FERC has no rate/market-rule jurisdiction, but reliability runs FERC -> NERC -> Texas RE."""
    nodes, edges = g("ercot", "competitive_area")
    assert not [e for e in edges if e["type"] == "regulates" and e["from"] == "ferc"
                and e.get("domain") in {"rates", "market_rules"}]
    rel = {(e["from"], e["to"]) for e in edges if e["type"] == "regulates" and e.get("domain") == "reliability"}
    assert {("ferc", "nerc"), ("nerc", "texas_re"), ("texas_re", "ercot")} <= rel


@M2
def test_puct_oversees_ercot():
    _, edges = g("ercot", "competitive_area")
    assert any(e["type"] == "regulates" and e["from"] == "puct" and e["to"] == "ercot" for e in edges)


@M2
def test_ercot_noie_transmission_rate_still_set_by_puct():
    _, edges = g("ercot", "noie")
    assert any(e["type"] == "sets_rate" and e["from"] == "puct" and e.get("rate_component") == "transmission"
               for e in edges)


# ---- PJM ----
@M3
def test_pjm_has_capacity_auction():
    nodes, edges = g("pjm", "restructured_choice")
    assert "rpm" in nodes and nodes["rpm"]["kind"] == "market"
    assert any(e["type"] == "operates" and e["from"] == "pjm" and e["to"] == "rpm" for e in edges)


# ---- CAISO ----
@M3
def test_caiso_has_no_central_capacity_auction():
    for arch, nodes, edges in all_graphs("caiso"):
        assert all("capacity" not in n["id"] for n in by_kind(nodes, "market")), arch
    _, edges = g("caiso", "iou_bundled")
    assert any(e["type"] == "plans_procures" and e["from"] == "cpuc" for e in edges), "CPUC sets RA obligations"


@M3
def test_caiso_cca_sets_generation_rate():
    nodes, edges = g("caiso", "iou_cca")
    assert by_kind(nodes, "cca")
    ans = build.who_sets(edges, "residential", "generation")
    assert ans and nodes[ans["setter"]]["kind"] == "cca"


@M3
def test_smud_is_not_a_balancing_authority():
    nodes, _ = g("caiso", "muni_own_ba")
    ops = {n["id"] for n in nodes.values() if n["lane"] == "market_operator"}
    assert "smud" not in ops and "banc" in ops


# ---- GB ----
@MGB
def test_neso_is_public_and_owns_nothing():
    nodes, _ = g("gb", "domestic_default_capped")
    assert nodes["neso"]["kind"] == "system_operator"
    assert nodes["neso"]["owner"]["type"] in {"public", "state_owned"}
    assert not nodes["neso"].get("holds_assets")


@MGB
def test_gb_has_no_iso_and_no_central_dispatch():
    for arch, nodes, edges in all_graphs("gb"):
        assert not by_kind(nodes, "iso"), arch
        assert not by_kind(nodes, "reliability_body"), arch
        for e in edges:
            if e["type"] == "dispatches":
                assert e["from"] == "neso" and e.get("mechanism") in {"balancing_redispatch", "ancillary_contract"}, e["id"]


@MGB
def test_gb_price_cap_is_a_ceiling_on_default_tariffs_only():
    _, edges = g("gb", "domestic_default_capped")
    caps = [e for e in edges if e.get("mode") == "caps"]
    assert caps and all(e["from"] == "ofgem" for e in caps)
    _, edges = g("gb", "supplier_contract")
    assert not [e for e in edges if e.get("mode") == "caps"]


@MGB
def test_gb_transmission_connected_has_no_dno():
    nodes, _ = g("gb", "transmission_connected")
    assert not by_kind(nodes, "wires_utility")


@MGB
def test_gb_elexon_settles_and_bsuos_is_demand_only():
    nodes, edges = g("gb", "domestic_default_capped")
    assert any(e["type"] == "settles" and e["from"] == "elexon" for e in edges)
    assert not [e for e in edges if e["type"] == "pays" and e.get("rate_component") == "balancing"
                and nodes[e["from"]]["kind"] == "generator"]


@MGB
def test_gb_levies_and_taxes_reach_residential():
    _, edges = g("gb", "domestic_default_capped")
    for comp in ("policy_levy", "tax"):
        ans = build.who_sets(edges, "residential", comp)
        assert ans and ans["mode"] == "levies", comp


@MGB
def test_gb_has_14_dno_areas():
    areas = [u for u in MARKETS["gb"][1]["utilities"].values() if "dno" in u.get("fills", {})]
    assert len(areas) == 14
