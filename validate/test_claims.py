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
THIN_SLICE = "thin slice: only the residential class is wired so far"
KNOWN_GAPS = {(mid, arch, cls): THIN_SLICE
              for mid, arch in [("ercot", "competitive_area"), ("pjm", "restructured_choice"),
                                ("caiso", "iou_bundled"), ("caiso", "muni_own_ba"), ("ercot", "noie"), ("pjm", "limited_choice"),
                                ("gb", "domestic_default_capped")]
              for cls in ("small_commercial", "large_ci", "large_load")}


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
        if e["type"] == "operates":
            if dst["kind"] == "market":
                assert "asset" not in e, f"{e['id']}: a market is not an asset"
            else:
                assert e.get("asset"), f"{e['id']}: operates needs an asset unless it targets a market"
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
def test_ercot_has_no_capacity_market():
    for arch, nodes, edges in all_graphs("ercot"):
        assert not [e for e in edges if e.get("rate_component") == "capacity"], arch
        assert not by_kind(nodes, "market") or all("capacity" not in n["id"] for n in by_kind(nodes, "market"))


def test_ercot_ferc_does_not_regulate_rates_or_market_rules():
    """ERCOT is intrastate: FERC has no rate/market-rule jurisdiction, but reliability runs FERC -> NERC -> Texas RE."""
    nodes, edges = g("ercot", "competitive_area")
    assert not [e for e in edges if e["type"] == "regulates" and e["from"] == "ferc"
                and e.get("domain") in {"rates", "market_rules"}]
    rel = {(e["from"], e["to"]) for e in edges if e["type"] == "regulates" and e.get("domain") == "reliability"}
    assert {("ferc", "nerc"), ("nerc", "texas_re"), ("texas_re", "ercot")} <= rel


def test_puct_oversees_ercot():
    _, edges = g("ercot", "competitive_area")
    assert any(e["type"] == "regulates" and e["from"] == "puct" and e["to"] == "ercot" for e in edges)


def test_ercot_noie_transmission_rate_still_set_by_puct():
    _, edges = g("ercot", "noie")
    assert any(e["type"] == "sets_rate" and e["from"] == "puct" and e.get("rate_component") == "transmission"
               for e in edges)


def test_ercot_noie_retail_rates_set_by_its_governing_body():
    nodes, edges = g("ercot", "noie")
    for comp in ("generation", "distribution", "riders_public_purpose"):
        assert build.who_sets(edges, "residential", comp)["setter"] == "governing_body", comp
    assert MARKETS["ercot"][1]["utilities"]["CPS Energy"]["archetypes"] == ["noie"]


# ---- PJM ----
def test_dominion_virginia_is_vertically_integrated():
    nodes, edges = g("pjm", "limited_choice")
    assert {"generation", "transmission", "distribution"} <= set(nodes["viu"]["holds_assets"])
    assert build.who_sets(edges, "residential", "generation")["setter"] == "state_puc"   # no supplier choice
    assert not any(n["kind"] == "retail_provider" for n in nodes.values())


def test_pjm_has_capacity_auction():
    nodes, edges = g("pjm", "restructured_choice")
    assert "rpm" in nodes and nodes["rpm"]["kind"] == "market"
    assert any(e["type"] == "operates" and e["from"] == "pjm" and e["to"] == "rpm" for e in edges)


# ---- CAISO ----
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


def test_smud_is_not_a_balancing_authority():
    nodes, _ = g("caiso", "muni_own_ba")
    ops = {n["id"] for n in nodes.values() if n["lane"] == "market_operator"}
    assert "smud" not in ops and "banc" in ops
    fills = MARKETS["caiso"][1]["utilities"]
    assert fills["SMUD"]["fills"]["ba"]["name"] == "BANC"                 # SMUD operates BANC; BANC is the BA
    assert fills["LADWP"]["fills"]["ba"]["name"].startswith("LADWP")    # LADWP is its own BA


def test_pou_rates_are_set_by_their_own_board_not_the_cpuc():
    nodes, edges = g("caiso", "muni_own_ba")
    assert not any(e["type"] == "sets_rate" and e["from"] == "cpuc" for e in edges)    # CPUC: safety oversight only
    assert nodes["pou"]["kind"] == "muni"
    for comp in build.bill_components(DATA[MARKETS["caiso"][0]]["profile"], MARKETS["caiso"][1]):
        ans = build.who_sets(edges, "residential", comp)
        assert ans and ans["setter"] == "governing_body", comp


# ---- GB ----
def test_neso_is_public_and_owns_nothing():
    nodes, _ = g("gb", "domestic_default_capped")
    assert nodes["neso"]["kind"] == "system_operator"
    assert nodes["neso"]["owner"]["type"] in {"public", "state_owned"}
    assert not nodes["neso"].get("holds_assets")


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


def test_gb_elexon_settles_and_bsuos_is_demand_only():
    nodes, edges = g("gb", "domestic_default_capped")
    assert any(e["type"] == "settles" and e["from"] == "elexon" for e in edges)
    assert not [e for e in edges if e["type"] == "pays" and e.get("rate_component") == "balancing"
                and nodes[e["from"]]["kind"] == "generator"]


def test_gb_levies_and_taxes_reach_residential():
    _, edges = g("gb", "domestic_default_capped")
    for comp in ("policy_levy", "tax"):
        ans = build.who_sets(edges, "residential", comp)
        assert ans and ans["mode"] == "levies", comp


@MGB
def test_gb_has_14_dno_areas():
    areas = [u for u in MARKETS["gb"][1]["utilities"].values() if "dno" in u.get("fills", {})]
    assert len(areas) == 14


# ---- domain maps: where each body's authority applies ----
def domain(mid, node_id):
    """-> (full, partial) area ids, groups expanded; fails if the node has no domain_area."""
    m = build.map_for(build.load_maps(), MARKETS[mid][0])
    n = next(n for n in MARKETS[mid][1]["base"]["nodes"] if n["id"] == node_id)
    assert "domain_area" in n, f"{mid}:{node_id} has no domain_area"
    grow = lambda ids: {a for i in ids for a in m.get("groups", {}).get(i, [i])}
    return grow(n["domain_area"]["full"]), grow(n["domain_area"].get("partial", []))


def test_nerc_covers_contiguous_us_and_canada():
    full, _ = domain("ercot", "nerc")
    assert {"tx", "ca", "pa", "canada"} <= full and "mexico" not in full


def test_puct_domain_is_texas_only():
    assert domain("ercot", "puct")[0] == {"tx"}


def test_cpuc_domain_is_california_only():
    assert domain("caiso", "cpuc")[0] == {"ca"}


def test_texas_re_domain_is_the_ercot_region():
    assert domain("ercot", "texas_re")[0] == {"ercot"}


def test_ferc_covers_ercot_for_reliability_only():
    full, partial = domain("ercot", "ferc")
    assert "ercot" in partial and "ercot" not in full


def test_neso_domain_excludes_northern_ireland():
    full, partial = domain("gb", "neso")
    assert "ni" not in full | partial and len(full) == 14 and all(a.startswith("dno_") for a in full)


def county_rto():
    """FIPS -> set of ISO/RTO area ids, from scripts/maps/derived/county_rto.csv (EIA-861)."""
    out = {}
    for line in (build.ROOT / "scripts/maps/derived/county_rto.csv").read_text().splitlines()[1:]:
        fips, rto, _ = line.split(",")
        out.setdefault(fips, set()).add(rto)
    return out


def test_iso_footprints_match_known_counties():
    c = county_rto()
    assert "ercot" in c["48201"] and "ercot" in c["48453"]          # Harris (Houston), Travis (Austin)
    assert "ercot" not in c.get("48141", set())                     # El Paso: El Paso Electric, WECC
    assert "ercot" not in c.get("48375", set())                     # Potter (Amarillo): SPS, SPP
    assert "pjm" in c["42101"] and "pjm" in c["17031"]              # Philadelphia, Cook (ComEd)
    assert "pjm" not in c.get("21111", set())                       # Jefferson KY (Louisville): LG&E, outside PJM
    assert "pjm" not in c.get("17119", set())                       # Madison IL: Ameren Illinois, MISO
    assert "caiso" in c["06073"] and "caiso" in c["06075"]           # San Diego (SDG&E), San Francisco (PG&E)


def test_california_iou_territories_sit_north_to_south():
    # CEC polygons; make_maps.mjs already fails the build if two territories overlap
    m = build.load_maps()["north_america"]
    b = m["bbox"]                                        # [x0, y0, x1, y1], SVG y grows southward
    assert {"pge", "sce", "sdge"} <= set(b)
    assert b["pge"][1] < b["sce"][1] < b["sdge"][1]     # PG&E reaches furthest north, SDG&E least
    assert b["sdge"][3] >= b["sce"][3]                  # SDG&E reaches the Mexican border
    for u in ("pge", "sce", "sdge"):                     # all inside California
        assert all(lo >= hi for lo, hi in zip(b[u][:2], [c - 1 for c in b["ca"][:2]]))
        assert all(hi <= lo for hi, lo in zip(b[u][2:], [c + 1 for c in b["ca"][2:]]))


def test_iso_utility_territories_sit_inside_their_iso():
    # HIFLD territories; make_maps.mjs already fails the build if two investor-owned territories overlap
    b = build.load_maps()["north_america"]["bbox"]
    inside = lambda u, iso: all(abs(min(0, x)) <= 3 for x in
                                (b[u][0] - b[iso][0], b[u][1] - b[iso][1], b[iso][2] - b[u][2], b[iso][3] - b[u][3]))
    for u in ("oncor", "centerpoint", "cps"):
        assert inside(u, "ercot"), u
    for u in ("comed", "dominion_va", "pseg", "peco"):
        assert inside(u, "pjm"), u


def test_hm_treasury_covers_the_uk_and_desnz_only_gb():
    full, _ = domain("gb", "hm_treasury")
    assert "ni" in full
    assert "ni" not in domain("gb", "desnz")[0]


def test_each_gb_dno_fill_is_one_licence_area():
    for name, u in MARKETS["gb"][1]["utilities"].items():
        f = u.get("fills", {}).get("dno")
        if isinstance(f, dict) and "domain_area" in f:
            full = f["domain_area"]["full"]
            assert len(full) == 1 and full[0].startswith("dno_"), name
