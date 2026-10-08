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


# ---- completeness: every class x bill component has at least one line item, each with one path ending at a setter ----
# (market, archetype, class) -> reason. Each entry is a strict xfail; delete it once fixed.
# (market, archetype, class) -> reason. Each entry is a strict xfail; delete it once fixed.
KNOWN_GAPS = {(mid, arch, cls): "thin slice: only the residential class is wired so far"
              for mid, arch in [("gb", "domestic_default_capped")]
              for cls in ("small_commercial", "large_ci", "large_load")}


def _bill_cases():
    for cc, mid, arch, nodes, edges in GRAPHS:
        prof, m = DATA[cc]["profile"], MARKETS[mid][1]
        classes = [n["id"] for n in nodes.values() if n["kind"] == "consumer"]   # a class a setup cannot serve
        for cls in prof["consumer_classes"]:                                      # (residential on Direct Access) is
            if cls not in classes:                                                # covered by the test below instead
                continue
            for comp in build.bill_components(prof, m):
                reason = KNOWN_GAPS.get((mid, arch, cls))
                marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
                yield pytest.param(mid, arch, cls, comp, edges, marks=marks, id=f"{mid}:{arch}:{cls}:{comp}")


@pytest.mark.parametrize("mid,arch,cls,comp,edges", list(_bill_cases()))
def test_complete_bill_path(mid, arch, cls, comp, edges):
    items, problems = build.line_items(edges, cls, comp)
    assert items and not problems, f"{cls}/{comp} in {mid}:{arch}: {problems or 'no path to a setter'}"


# ---- line items: one bill line, several setters (approved 2026-10-08) ----
def _e(i, frm, to, mode="sets", sub=None, comp="ancillary_uplift"):
    return {"id": i, "from": frm, "to": to, "type": "sets_rate", "mode": mode, "rate_component": comp} | ({"subcomponent": sub} if sub else {})


def test_line_items_share_unlabelled_hops():
    edges = [_e("rep_res", "rep", "residential", "passes_through"),
             _e("iso_rep", "iso", "rep", "market", "Ancillary services"),
             _e("puc_rep", "puc", "rep", "approves", "Securitization"),
             _e("puc_iso_fee", "puc", "iso", "approves", "Administration fee")]
    a = build.answer(edges, "residential", "ancillary_uplift")
    got = {i["subcomponent"]: (i["setter"], i["path"]) for i in a["items"]}
    assert got == {"Ancillary services": ("iso", ["rep_res", "iso_rep"]), "Securitization": ("puc", ["rep_res", "puc_rep"])}
    assert build.who_sets(edges, "residential", "ancillary_uplift") is None     # two setters: no single answer


def test_line_item_label_without_its_own_path_is_a_limit_on_the_default_item():
    edges = [_e("rep_res", "rep", "residential", "passes_through"), _e("iso_rep", "iso", "rep", "market"),
             _e("puc_iso_fee", "puc", "iso", "approves", "Administration fee")]
    items, problems = build.line_items(edges, "residential", "ancillary_uplift")
    assert not problems and len(items) == 1 and items[0]["limits"] == ["puc_iso_fee"]


def test_two_lines_for_one_line_item_are_an_error():
    edges = [_e("rep_res", "rep", "residential", "passes_through"),
             _e("a", "iso", "rep", "market", "Ancillary services"), _e("b", "puc", "rep", "sets", "Ancillary services")]
    items, problems = build.line_items(edges, "residential", "ancillary_uplift")
    assert problems and build.answer(edges, "residential", "ancillary_uplift") is None


def test_line_item_that_stops_short_of_a_setter_is_an_error():
    edges = [_e("rep_res", "rep", "residential", "passes_through"), _e("iso_rep", "iso", "rep", "market", "Ancillary services"),
             _e("x_rep", "x", "rep", "passes_through", "Securitization")]
    items, problems = build.line_items(edges, "residential", "ancillary_uplift")
    assert [i["subcomponent"] for i in items] == ["Ancillary services"] and problems


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


RELIABILITY_RE = {"ercot": "texas_re", "caiso": "wecc", "pjm": "rf"}


@pytest.mark.parametrize("mid,re_id", RELIABILITY_RE.items())
def test_every_us_iso_sits_under_nerc_and_its_regional_entity(mid, re_id):
    """FPA s.215: FERC approves NERC standards; the regional entity enforces them on the ISO, in every archetype."""
    for arch, nodes, edges in all_graphs(mid):
        rel = {(e["from"], e["to"]) for e in edges if e["type"] == "regulates" and e.get("domain") == "reliability"}
        assert {("ferc", "nerc"), ("nerc", re_id), (re_id, mid)} <= rel, f"{mid}:{arch}"


def test_dominion_virginia_is_in_serc():
    _, edges = g("pjm", "limited_choice")
    assert any(e["from"] == "serc" and e["to"] == "viu" and e.get("domain") == "reliability" for e in edges)


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


def test_ercot_coop_board_sets_retail_rates_puct_sets_transmission():
    """PURA 41.004: the PUCT's jurisdiction over a co-op is wholesale transmission, certification and a few other items."""
    nodes, edges = g("ercot", "coop")
    for comp in ("generation", "distribution", "riders_public_purpose"):
        assert build.who_sets(edges, "residential", comp)["setter"] == "coop_board", comp
    assert build.who_sets(edges, "residential", "transmission")["setter"] == "puct"
    assert nodes["coop"]["kind"] == "coop"
    for name in ("Pedernales Electric Cooperative", "CoServ"):
        u = MARKETS["ercot"][1]["utilities"][name]
        assert u["archetypes"] == ["coop"] and u["fills"]["coop"]["owner"]["type"] == "cooperative", name


# ---- PJM ----
def test_virginia_coop_rates_approved_by_the_scc_not_its_board():
    """Va. Code 56-231.34 and 56-585.3: co-op rates stay under the SCC; the board only governs (and may move
    distribution rates up to 5% in three years). Contrast with ERCOT, where the co-op board sets rates."""
    _, edges = g("pjm", "coop")
    for comp in ("distribution", "riders_public_purpose"):
        a = build.who_sets(edges, "residential", comp)
        assert a["setter"] == "state_puc" and a["mode"] == "approves", comp
    assert not [e for e in edges if e["type"] == "sets_rate" and e["from"] == "coop_board"]
    for name in ("NOVEC", "Rappahannock Electric Cooperative"):
        u = MARKETS["pjm"][1]["utilities"][name]
        assert u["area"] == "VA" and u["archetypes"] == ["coop"], name

def test_dominion_virginia_is_vertically_integrated():
    nodes, edges = g("pjm", "limited_choice")
    assert {"generation", "transmission", "distribution"} <= set(nodes["viu"]["holds_assets"])
    assert build.who_sets(edges, "residential", "generation")["setter"] == "state_puc"   # no supplier choice
    assert not any(n["kind"] == "retail_provider" for n in nodes.values())


def test_pjm_has_capacity_auction():
    nodes, edges = g("pjm", "restructured_choice")
    assert "rpm" in nodes and nodes["rpm"]["kind"] == "market"
    assert any(e["type"] == "operates" and e["from"] == "pjm" and e["to"] == "rpm" for e in edges)


def test_every_archetype_serves_at_least_one_class_and_names_the_ones_it_cannot():
    """Direct Access is closed to residential customers, so caiso:iou_direct_access has no residential box.
    Every other setup here serves all four classes."""
    for cc, mid, arch, nodes, edges in GRAPHS:
        got = {n["id"] for n in nodes.values() if n["kind"] == "consumer"}
        want = set(DATA[cc]["profile"]["consumer_classes"])
        assert got, f"{mid}:{arch}: no consumer class"
        if mid in ("pjm", "caiso"):
            expected = want - {"residential"} if (mid, arch) == ("caiso", "iou_direct_access") else \
                       {"residential", "small_commercial"} if (mid, arch) == ("pjm", "municipal_aggregation") else want
            assert got == expected, f"{mid}:{arch}"


def test_comed_default_supply_is_procured_by_the_illinois_power_agency():
    """The IPA plans and runs ComEd's default procurement and the ICC approves it; ComEd itself buys RPM capacity."""
    nodes, edges = g("pjm", "default_service_ipa")
    assert nodes["ipa"]["kind"] == "policy_maker"
    assert any(e["type"] == "plans_procures" and e["from"] == "ipa" for e in edges)
    assert any(e["type"] == "regulates" and e["from"] == "state_puc" and e["to"] == "ipa" for e in edges)
    items = {it["subcomponent"]: it["setter"] for it in build.answer(edges, "residential", "generation")["items"]}
    assert set(items) == {"Energy blocks bought by the Illinois Power Agency", "Energy bought in PJM's markets"}
    assert items["Energy blocks bought by the Illinois Power Agency"] == "default_supplier"
    assert build.who_sets(edges, "residential", "capacity")["setter"] == "rpm"     # ComEd pays RPM directly
    assert MARKETS["pjm"][1]["utilities"]["ComEd"]["archetypes"][0] == "default_service_ipa"


def test_pjm_capacity_price_comes_from_rpm_and_ferc_only_approves_it():
    """RPM sets the capacity price; FERC approves its rules rather than setting the price."""
    for arch in ("default_service_ipa", "restructured_choice", "coop"):
        _, edges = g("pjm", arch)
        caps = [it for cls in ("residential", "large_ci") if (a := build.answer(edges, cls, "capacity")) for it in a["items"]]
        assert caps, arch
        assert all(it["setter"] in {"rpm", "default_supplier", "wholesale_supplier"} for it in caps), arch
        assert any(e.get("mode") == "approves" and e["from"] == "ferc" and e["to"] == "rpm" for e in edges), arch
    _, edges = g("pjm", "restructured_choice")
    assert build.who_sets(edges, "large_ci", "capacity")["setter"] == "rpm"        # hourly service: the auction price


def test_large_customers_on_pjm_default_service_pay_hourly_market_prices():
    """Above 100 kW, default service is spot-priced: PJM's energy price reaches the customer, not an auction price."""
    for arch in ("restructured_choice", "default_service_ipa"):
        _, edges = g("pjm", arch)
        assert build.who_sets(edges, "large_ci", "generation")["setter"] == "pjm", arch
        res = {it["setter"] for it in build.answer(edges, "residential", "generation")["items"]}
        assert "default_supplier" in res, arch      # households get the procured price, not the hourly one


def test_a_pjm_competitive_supplier_sets_supply_and_the_wires_stay_regulated():
    nodes, edges = g("pjm", "competitive_supplier")
    assert nodes["supplier"]["kind"] == "retail_provider"
    for comp in ("generation", "capacity", "ancillary_uplift"):
        assert build.who_sets(edges, "residential", comp)["setter"] == "supplier", comp
    assert build.who_sets(edges, "residential", "distribution")["setter"] == "state_puc"
    assert build.who_sets(edges, "residential", "transmission")["setter"] == "ferc"


def test_pjm_municipal_aggregation_covers_only_households_and_small_business():
    """20 ILCS 3855/1-92 aggregates residential and small commercial load; its supplier sets the price and the
    municipality approves the contract."""
    nodes, edges = g("pjm", "municipal_aggregation")
    assert nodes["aggregator"]["kind"] == "cca"
    a = build.who_sets(edges, "residential", "generation")
    assert a["setter"] == "agg_supplier" and "agg_sup_gen_ok" in a["limits"]
    assert {n["id"] for n in nodes.values() if n["kind"] == "consumer"} == {"residential", "small_commercial"}


def test_west_virginia_utility_is_vertically_integrated_with_no_choice():
    nodes, edges = g("pjm", "vertically_integrated")
    assert {"generation", "transmission", "distribution"} <= set(nodes["viu"]["holds_assets"])
    assert not [n for n in nodes.values() if n["kind"] in {"retail_provider", "cca", "lse"}]
    for cls in DATA["US"]["profile"]["consumer_classes"]:
        assert build.who_sets(edges, cls, "generation")["setter"] == "state_puc", cls
    assert MARKETS["pjm"][1]["utilities"]["Mon Power"]["area"] == "WV"


def test_virginia_coop_wholesale_supply_is_a_ferc_rate_the_scc_does_not_set():
    """ODEC sells REC its wholesale power under a FERC-accepted formula rate; the SCC's authority is the retail side."""
    nodes, edges = g("pjm", "coop")
    assert nodes["wholesale_supplier"]["kind"] == "lse"
    for comp in ("generation", "capacity"):
        a = build.who_sets(edges, "residential", comp)
        assert a["setter"] == "wholesale_supplier" and any(edges[i]["from"] == "ferc" for i, e in enumerate(edges) if e["id"] in a["limits"]), comp
    assert not [e for e in edges if e["type"] == "sets_rate" and e["from"] == "state_puc"
                and e.get("rate_component") in {"generation", "capacity"}]
    assert MARKETS["pjm"][1]["utilities"]["Rappahannock Electric Cooperative"]["fills"]["wholesale_supplier"]["name"] == "ODEC"


# ---- CAISO ----
def test_caiso_has_no_central_capacity_auction():
    for arch, nodes, edges in all_graphs("caiso"):
        assert all("capacity" not in n["id"] for n in by_kind(nodes, "market")), arch
    _, edges = g("caiso", "iou_bundled")
    assert any(e["type"] == "plans_procures" and e["from"] == "cpuc" for e in edges), "CPUC sets RA obligations"


def test_caiso_resource_adequacy_is_a_line_item_inside_the_generation_rate():
    """CAISO runs no capacity auction: RA capacity is bought by each LSE and recovered inside the generation rate."""
    _, edges = g("caiso", "iou_bundled")
    items = {it["subcomponent"]: it["setter"] for it in build.answer(edges, "residential", "generation")["items"]}
    assert items == {"Energy procurement": "cpuc", "Resource adequacy": "cpuc"}
    assert "capacity" not in build.bill_components(DATA["US"]["profile"], MARKETS["caiso"][1])


def test_caiso_direct_access_is_closed_to_households_and_capped():
    nodes, edges = g("caiso", "iou_direct_access")
    assert "residential" not in nodes
    assert nodes["esp"]["kind"] == "retail_provider"
    for cls in ("small_commercial", "large_ci", "large_load"):
        assert build.who_sets(edges, cls, "generation")["setter"] == "esp", cls
    assert any(e["type"] == "regulates" and e.get("domain") == "licensing" and e["from"] == "cpuc" for e in edges)


def test_cca_and_direct_access_customers_pay_the_pcia_exit_fee():
    for arch, cls in (("iou_cca", "residential"), ("iou_direct_access", "large_ci")):
        _, edges = g("caiso", arch)
        items = {it["subcomponent"]: it["setter"] for it in build.answer(edges, cls, "riders_public_purpose")["items"]}
        assert items.get("Exit fee (PCIA)") == "cpuc", arch
    _, edges = g("caiso", "iou_bundled")           # a bundled customer pays no exit fee
    assert not [e for e in edges if e.get("subcomponent") == "Exit fee (PCIA)"]


def test_a_city_utility_inside_caiso_keeps_retail_rates_but_ferc_approves_transmission():
    """Anaheim and Riverside turned their transmission over to CAISO as participating transmission owners."""
    nodes, edges = g("caiso", "muni_in_caiso")
    assert nodes["pou"]["kind"] == "muni"
    assert build.who_sets(edges, "residential", "transmission")["setter"] == "ferc"
    for comp in ("generation", "distribution", "riders_public_purpose"):
        assert build.who_sets(edges, "residential", comp)["setter"] == "governing_body", comp
    assert any(e["type"] == "operates" and e["from"] == "caiso" and e["to"] == "pou" for e in edges)
    for name in ("Anaheim Public Utilities", "Riverside Public Utilities"):
        assert MARKETS["caiso"][1]["utilities"][name]["archetypes"] == ["muni_in_caiso"], name


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
    """NERC: contiguous US, the Canadian provinces in a regional entity, and Baja California (in WECC); not all of Mexico,
    not the territories, not Alaska or Hawaii."""
    full, _ = domain("ercot", "nerc")
    assert {"tx", "ca", "pa", "ca_on", "ca_qc", "ca_bc", "mx_bcn"} <= full
    assert not full & {"mexico", "canada", "ak", "hi"}


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
    for u in ("oncor", "centerpoint", "cps", "pec", "coserv"):
        assert inside(u, "ercot"), u
    for u in ("comed", "dominion_va", "pseg", "peco", "novec", "rec"):
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
