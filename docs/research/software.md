# grid-atlas v2: multi-country plus ownership. Software viability review

Verdict: **viable, and cheaper to do now than later.** Milestone 1 has not started, so schema v2 can be the day-one schema and nothing needs migrating. The design stays YAML → `build.py` → static single-file front end. One CLAUDE.md assumption is wrong and must change regardless of GB: `index.html` cannot `fetch('data.json')` from `file://` (see section 3).

Everything below was executed in this sandbox. PyYAML 6.0.1 and jsonschema 4.26 are installed; **pytest is not**, so the tests were run through a 30-line stand-in (`v2check/_shim/`) that implements `parametrize`, `param` and `xfail(strict)`. The tests are written as ordinary pytest and need no change to run under real pytest.

| Artifact | Path |
|---|---|
| Draft schema | `reviews/schema_v2.json` (identical copy at `v2check/data/schema.json`) |
| Example data, validated | `v2check/data/countries/{gb,us}/{_country,gb,ercot}.yaml` |
| build.py (runs) | `v2check/scripts/build.py` → `v2check/web/data.json` and `data.js` (12 KB) |
| Tests (run: 26 pass, 14 expected xfail, 0 fail) | `v2check/validate/{conftest,test_schema,test_claims}.py` |

Mutation checks: each mutation was caught by the schema or a test.
- Having DESNZ cap the price fails `caps only from regulators`.
- Making NESO `kind: iso` fails `test_gb_has_no_iso`.
- Removing the source from NESO's owner is a schema error.
- Deleting the VAT pass-through edge fails both a dangling-edge test and the residential/tax bill-path test.

---

## 1. Schema v2: each change, why, and what breaks without it

Principle: **global enums for meaning, per-country profile for words.** The UI, tests and cross-country compare key off global values (`kind`, `lane`, `rate_component`, `mode`). Labels such as "DNO", "Supplier" and "TNUoS" live in `data/countries/<cc>/_country.yaml`.

| # | Change | Why | What breaks if omitted |
|---|---|---|---|
| 1 | Top-level `schema_version: 2`, `country` (ISO 3166-1 alpha-2), `market` (repo-unique id: `ercot`, `pjm`, `caiso`, `gb`) | A country can hold several markets (US) or one (GB). `market` replaces `region` as the id the UI and the `answers` keys use. | Nothing identifies which vocabulary or rules apply, and GB claim tests can't be scoped. |
| 2 | **Country profile** `_country.yaml` (`$defs/country_profile`): lane titles and subtitles, `kind_labels`, `jurisdiction_labels`, `component_labels`, `bill_components`, `consumer_classes`, `chain` (dropdown labels), `glossary` (term, meaning, `equivalent: {US: …}`) | Lanes stay fixed (the CLAUDE.md rule) while GB shows "SYSTEM OPERATOR & SETTLEMENT" instead of "ISO/RTO". The glossary moves out of CLAUDE.md into data so tooltips can be generated. `equivalent` powers compare tooltips such as DNO ≈ TDSP/EDC. | US words get hard-coded into the UI, and GB either looks wrong or forks the template. The completeness test has no list of which components a country's bill must contain. |
| 3 | `jurisdiction`: `supranational, national, subnational, local, private` (replaces `federal, state`) | Country-neutral. US labels these Federal and State; GB labels `subnational` as Devolved. | GB nodes need fake "federal" values, or the enum grows per country. |
| 4 | `kind` additions: `system_operator`, `settlement_body`, `scheme_administrator`, `policy_maker`, `holding_group`, `interconnector` | NESO is not an ISO: it owns no assets and runs no organised day-ahead market. Elexon settles imbalance. LCCC/EMR administer the levies. DESNZ and HMT set levies and taxes. | NESO gets tagged `iso`, which is factually wrong and makes compare imply GB has an ISO. |
| 5 | Edge types `owns`, `operates`, `settles` | These are **not price relationships**, so they need their own colour and toggle (CLAUDE.md: "each edge type gets its own colour"). `operates` versus `owns` is the owner/operator split: NESO `operates` the transmission system the TOs own. The same split applies to US ISOs versus TOs. | The ownership lens has nothing to draw, and Elexon gets forced into `dispatches` or `pays`. |
| 6 | **`mode` on `sets_rate`**: `sets` (default), `approves`, `caps`, `levies`, `passes_through`. Chosen **instead of** new edge types `caps_rate` or `levies`. | "Who sets my rate?" stays a walk over one edge type. A pass-through edge (supplier → household, DUoS) chains back to the real setter (DNO, sets) and its limits (Ofgem, approves the price control; Ofgem, caps). Because the default is `sets`, **existing US data is valid unchanged.** | With separate types, every query and test must union 3–4 types. Without `caps`, the GB price cap is drawn as Ofgem "setting" the rate, which is factually wrong. Without `passes_through`, the supplier looks like it sets VAT. |
| 7 | A `caps` edge may omit `rate_component` (meaning a cap on the whole bill) | The default tariff cap is one ceiling over all components. | You would need 7 duplicate cap edges per class. |
| 8 | `rate_component` adds `balancing, policy_levy, tax, supplier_margin, metering`. **No v1 value renamed.** Line items go in `subcomponent` (e.g. `CfD`, `RO`, `TNUoS`, `PCIA`), keyed into the glossary. | Keeps the enum small and global, so cross-country compare can align by component. The profile relabels `generation` as "Wholesale energy" for GB. Do not add `wholesale_energy` next to `generation`, because two names for one thing break compare. | Levies and VAT can't be expressed. The GB bill-path test can't exist. |
| 9 | Node `holds_assets: [transmission\|distribution\|generation\|…]` (which grid assets it owns) **separate from** `owner {name, type, parent, node?, as_of, source}` (who owns the entity's equity) | NESO is publicly owned (`owner.type: state_owned`) yet holds no assets. Those are two different claims. `owner.node` lets build emit an `owns` edge when a holding group is drawn. | "NESO has no owns edges" and "owns only to asset holders" can't be tested, and the ownership lens conflates the two claims. |
| 10 | `owner.source` is required. `source` is required on a node when `holds_assets` is non-empty (`if/then`). | Ownership changes hands (DNO groups are bought and sold) and is the claim most likely to go stale. `as_of` records the date. | Unsourced ownership claims enter a portfolio piece. |
| 11 | `owner_type` enum: `public, state_owned, investor_owned, municipal, cooperative, mutual, private_equity, infrastructure_fund, sovereign_wealth, consortium, nonprofit, member_owned` | The ownership-lens colour key. | Free text can't be coloured or compared. |
| 12 | **Slots**: a node has `slot: wires_utility`. A utility entry has `area` (replaces `state`) and `fills: {slot: {name, owner} \| node_id}`. | Formalises the CLAUDE.md rule "PECO and PPL draw the same picture". 14 DNO areas become **one DNO node** relabelled per area, each with its own sourced owner. `fills: {transmission_owner: shet}` binds the right one of the 3 TOs by geography. | Either 14 DNO nodes in one lane (layout breaks) or no per-area ownership at all. |
| 13 | `additionalProperties: false` everywhere | It caught two real errors in my example YAML: unquoted commas inside `{…}` flow maps silently split a description into extra keys. | Bad YAML builds a silently wrong diagram. |

Deliberately **not** in the schema (they're in pytest, because they cross files or depend on the country): ids resolve; lanes and components exist in the profile; `caps` only from regulators; no GB `iso`; bill-path completeness.

Open design question for the content experts: `market` belongs to exactly one country. A later Northern Ireland or SEM market spans GB and IE. Note that ISO's `GB` code covers all of the UK including NI, while market `gb` is Great Britain only. When that market is added, add an optional `also_covers: [IE]`. Don't add it now.

## 2. File layout

**Recommend `data/countries/<cc>/_country.yaml` + `data/countries/<cc>/<market>.yaml`.**

```
data/schema.json
data/countries/us/_country.yaml   ercot.yaml  pjm.yaml  caiso.yaml
data/countries/gb/_country.yaml   gb.yaml
```

- The profile needs a home, and the folder makes the country boundary obvious in PRs.
- The build checks that the folder name, the profile's `country` and each file's `country` all agree, so a flat layout with a `country` field gives no extra safety.

Migration note: none needed if milestone 1 starts on v2. If v1 had already been scaffolded:
- `git mv data/regions/*.yaml data/countries/us/`
- add `schema_version: 2`, `country: US`, `market: <id>`
- `state:` → `area:`
- `federal|state` → `national|subnational`

That is a sed-level change. The `mode` default keeps all edges valid.

## 3. build.py

The full file is `v2check/scripts/build.py` (104 lines, runs). Its shape:

```python
SETTER_MODES = {"sets", "approves", "levies"}
def load(root):            # per country: validate _country.yaml against $defs/country_profile and each market against root; collect ALL errors, then exit
def resolve(market, arch): # base + archetype - removes; derive owns edges from owner.node
def who_sets(edges, cls, comp):  # walk back from consumer via passes_through until mode in SETTER_MODES;
                                 # attach limits = caps/approves edges into nodes on the path; None if gap/ambiguous/cycle
def compile_all(data):     # {"countries": profiles, "markets": layered YAML,
                           #  "answers": {"gb|default_tariff|residential|distribution":
                           #      {"path":["s_d","duos"],"setter":"dno","mode":"sets","limits":["cap","p_ctrl_d"]}}}
# main(): write web/data.json AND web/data.js ("window.GRID_ATLAS=" + json + ";")
```

- **Cross-country compare** is a key lookup into `answers`, aligned by global `rate_component` and consumer class. The graph walk lives in tested Python, not in JS. The JS for milestone 4 ("Who sets my rate?") shrinks to highlighting edge ids.
- **Glossary**: copied per country into `countries[cc].glossary`. The UI shows each term on first appearance per column, as CLAUDE.md asks.
- **file:// claim: correct.** Chrome rejects `fetch()` of `file:` URLs ("URL scheme 'file' is not supported"). Firefox treats each `file://` page as a unique origin since v68, so a fetch of a sibling file fails. Safari blocks it unless the user enables "Disable Local File Restrictions". (Not browser-tested in this session; this is documented, long-standing behaviour.)
  - **Fix:** `index.html` loads `<script src="data.js"></script>` and reads `window.GRID_ATLAS`. A classic script tag works from `file://` everywhere and on GitHub Pages.
  - Keep `data.json` for tools and diffing.
  - Prefer this to inlining into `index.html`. Inlining makes `index.html` a generated file, which conflicts with "never hand-edit generated files" and with hand-editing the UI.
- **Size**: the example (2 small markets) is 12 KB minified.
  - Projection: 7 US ISOs plus GB at about 30–60 edges per archetype, about 30 archetypes in total, with sources on every edge, comes to roughly 200–350 KB uncompressed (about 40–60 KB gzipped on Pages). That is acceptable.
  - If it grows: intern sources into a `sources` table referenced by id. Sources are the bulk (about 40%), and YAML anchors already show the repetition.

## 4. Tests: the new invariants

All of these are in `v2check/validate/`:

- `test_every_ownership_claim_has_a_source`: nodes with `holds_assets` or `owner`, plus every `fills.*.owner`.
- `test_complete_bill_path[market:arch:class:component]`: parametrised over **the country profile's** `consumer_classes × bill_components`. For GB residential this covers wholesale, TNUoS, DUoS, BSUoS, policy levy, VAT and margin. Each path must end at `sets`, `approves` or `levies`.
- `test_mode_and_ownership_rules`, for all countries:
  - `caps` only from `kind: regulator`
  - `levies` only from regulator, policy_maker, legislature or scheme_administrator
  - `passes_through` only from the retail lane
  - `owns` only to nodes with non-empty `holds_assets`, and only for an `asset` they hold
- GB claims:
  - `test_neso_owns_nothing`: no `holds_assets`, no `owns` edges, owner public or state-owned
  - `test_gb_has_no_iso`
  - `test_gb_default_tariff_is_a_cap_not_a_set_rate`
  - `test_gb_levies_and_taxes_reach_residential`: setter is DESNZ or HMT with mode `levies`
  - `test_gb_elexon_settles`
- Structural: dangling edges, unique ids, utilities referencing real archetypes and slots, consumer nodes ⊂ country classes.

xfail pattern for known gaps. Use `strict=True`, so fixing a gap fails the run until someone deletes the entry. That makes gaps trend to zero visibly:

```python
KNOWN_GAPS = {("gb", "default_tariff", "small_commercial"): "non-domestic supply is not price-capped; research pending"}
marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
yield pytest.param(mid, arch, cls, comp, edges, marks=marks, id=f"{mid}:{arch}:{cls}:{comp}")

@pytest.mark.xfail(reason="14 DNO areas / 6 groups not yet entered (content task)", strict=True)
def test_gb_has_14_dno_areas(): assert len(DATA["GB"]["markets"]["gb"]["utilities"]) == 14
```

A `needs_verification` counter prints and never fails (currently 18).

## 5. index.html: one dependency-free file?

**Yes.** Estimated about 1,250 lines (about 50 KB) of hand-written HTML, CSS and JS:

| Feature | LOC |
|---|---|
| Lanes, node layout, SVG edges, hover tooltips, edge-type and mode styling (`caps` dashed, `passes_through` thin) | 380 |
| Data load (`window.GRID_ATLAS`), base+archetype composition, slot `fills` | 90 |
| Chained dropdowns driven by `profile.chain` (US 3-level, GB 2-level) | 90 |
| Country switch and vocabulary (lane titles, kind labels, glossary tooltips) | 80 |
| Ownership lens: recolour by `owner_type`, owner badge, `owns`/`operates` edges, legend, side list "DNO area → group" | 130 |
| "Who sets my rate?" panel from precomputed `answers` | 100 |
| Cross-country compare: 2–3 columns, per-component table aligned on global components, unique markers | 160 |
| CSS (themes, responsive stacking) | 220 |

Risks:

1. **"Unique to this region" across countries.** Matching by node `id` marks every GB node as unique, which is useless. Match on `kind` (plus `slot`) across countries, and on `id` within a country. Decide this in milestone 3, not later.
2. **Variable node counts per lane.** Allocate lane slot width from the maximum node count across visible columns. Wrap to a second row above about 6 nodes. GB's regulator lane (Ofgem, DESNZ, HMT, maybe Scottish and Welsh governments) is the densest.
3. **Lane-skipping edges.** For example DESNZ → supplier crosses two lanes and will run through nodes. Route skip edges as curves through a side gutter. Budget about 40 LOC; it is the most likely layout bug.
4. **14 DNO areas:** a non-issue *if* slots are used. Never draw 14 nodes. The lens shows ownership of the selected area, plus a compact 14-row table.
5. **3-up compare on a phone** doesn't fit. Stack the columns and keep the component table as the compare view.

## 6. Plan and effort, slotted into the milestones

Milestone 1 isn't started, so v2 is adopted from day one.

1. **Milestone 1: scaffold on v2** (country folders, `schema.json` v2, profile schema, `build.py` writing `data.js`, conftest, structural tests): **4.5 h** (was 2 h; +2.5 h for schema v2 and `who_sets`). Much of the code here can be lifted.
2. **Milestone 2: US profile + ERCOT + render**: **4.5 h** (+0.5 h for the profile; vocabulary-driven lanes).
3. **Milestone 3: PJM + CAISO + compare**: **11.5 h** (+0.5 h for the kind-based unique-marker rule).
4. **Milestone 4: "Who sets my rate?"**: **2.5 h** (−0.5 h, since the answers are precomputed).
5. **Milestone 5: GitHub Pages**: **1 h**.
6. **New milestone: GB**:
   - (a) GB profile and glossary: 1 h
   - (b) `gb.yaml` base and archetypes, entered from the experts' content: 4 h
   - (c) 14 DNO areas, 6 groups, 3-TO fills, all sourced: 2 h
   - (d) GB claim tests and gap list: 1.5 h
   - (e) ownership lens UI: 3 h
   - (f) cross-country compare (component table, country switch): 3 h
   - (g) layout hardening (skip-edge routing, dense lanes, mobile): 2 h
   - **Total: 16.5 h**
7. **Milestone 6: other 4 ISOs**: **8 h**, unchanged. The schema should not change because v2 already covers them.

Total: about 48.5 h (the original 21 h to v1, plus the 8 h already planned for milestone 6, plus 3 h net of v2 plumbing in milestones 1–4, plus 16.5 h for GB). The largest uncertainty is in step 6(b): how many GB archetypes the experts define (default tariff, fixed, prepayment, non-domestic). Each one adds about 1 h.
