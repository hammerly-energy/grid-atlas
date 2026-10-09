# CLAUDE.md — grid-atlas

Working name: `grid-atlas`. Repo lives at `~/Documents/GitHub/grid-atlas`, GitHub org `hammerly-energy`.

## Purpose

An interactive, side-by-side map of **who does what** in each electricity market: institutions and their roles, money and market flows, who owns which part of the grid, planning and policy, and the consumer classes at the end of it all. Starts with US ISO/RTO regions, then Great Britain, with other countries possible later.

The goal is learning: making the differences between markets (ERCOT vs PJM vs CAISO, then all 7 ISOs, then GB) visible and checkable. The repo is also a portfolio piece alongside `distribution-viz` and the market-clearing engine, so the data must be sourced and the claims must be tested.

The questions the tool must answer for any market and consumer class:
1. **"Who sets my rate, for each part of the bill?"** (including who only caps, approves, levies or passes it through)
2. **"Who regulates what?"**
3. **"Who owns which part of the grid?"** (and who merely operates it)

## Scope decisions (settled — do not reopen without asking)

| Decision | Choice |
|---|---|
| Form | Repo first, web-hosted later (GitHub Pages from `web/`) |
| Markets v1 | ERCOT, PJM, CAISO. Other 4 ISOs (MISO, SPP, NYISO, ISO-NE) are a separate milestone |
| Countries | US first; **Great Britain** is its own milestone (approved 2026-10-07, see `docs/countries-proposal.md`). NI is not GB: a future separate `sem` market |
| Main interaction | Side-by-side compare, same template per market, **including across countries** (e.g. PJM vs GB) |
| Detail level | **All variants**, selectable via chained dropdowns: Market → Utility (one list, labelled `Name [area] (IOU/POU/…)`, first utility in the YAML is the default) → Supply option, shown only when that utility offers more than one archetype (Christian, 2026-10-08). Country is the first link in each column's chain |
| Priority layer | Institutions + roles first; then money/market flows; then ownership; then planning/policy |
| Consumers | Must include consumer classes and who sets each class's rate |

Out of scope for v1: physical power-flow simulation, real-time prices, interactive map drill-down, scenario walkthroughs. In scope: a static locator map in the detail panel showing each body's domain (approved 2026-10-07, `/mnt/project-files/grid-atlas/domain-map-plan.md`). The market-clearing engine may later feed the wholesale lane; not now.

## Stack

- Data: YAML per market in `data/countries/<cc>/<market>.yaml`, plus one country profile `data/countries/<cc>/_country.yaml`, all validated against `data/schema.json` (schema v2)
- Build: `scripts/build.py` (Python, PyYAML + jsonschema) compiles YAML → `web/data.json` **and** `web/data.js` (`window.GRID_ATLAS = …;`)
- Tests: pytest in `validate/`
- Front end: single `web/index.html`, vanilla JS + SVG, no framework, no build step, no external runtime dependencies (must work from `file://` and GitHub Pages). It loads data with `<script src="data.js">`, **not** `fetch('data.json')`, because fetch fails from `file://` in Chrome, Firefox and Safari

```
python3 -m pip install -r requirements.txt
python3 scripts/build.py
python3 -m pytest -q -rx
open web/index.html
```

## Repo layout

```
grid-atlas/
├── data/
│   ├── schema.json                 # schema v2: market files + $defs/country_profile
│   └── countries/
│       ├── us/  _country.yaml  ercot.yaml  pjm.yaml  caiso.yaml
│       └── gb/  _country.yaml  gb.yaml
│   └── maps/  north_america.json  europe.json   # generated: one locator map per region, shapes with sources
├── scripts/build.py
├── scripts/maps/make_maps.mjs      # node + mapshaper; only rerun when shapes change
├── scripts/maps/sources.json       # every shape input: URL, sha256, credit, licence
├── scripts/maps/eia861_counties.py # EIA-861 → derived/county_rto.csv (ISO footprints as counties)
├── scripts/maps/hifld_utilities.py # HIFLD archive (GeoParquet) → derived/hifld_utilities.geojson (utility territories outside CA)
├── validate/
│   ├── conftest.py
│   ├── test_schema.py      # cross-file integrity: ids resolve, slots, ownership sources
│   ├── test_claims.py      # market facts as assertions
│   ├── test_layout.py      # every line clickable, none through a box (Playwright)
│   └── test_bill_panel.py  # Bill lens: a row per line item, limits and pass-throughs, aligned compare rows (Playwright)
├── web/
│   ├── index.html
│   ├── data.json           # generated — never hand-edit
│   └── data.js             # generated — never hand-edit
├── docs/
│   ├── countries-proposal.md   # approved schema v2 + GB design
│   └── research/               # policy, power systems, UX, software reviews with sources
├── CLAUDE.md
└── README.md
```

## Visual template — five lanes, same in every market

Lane **ids** are fixed; **display names** are country-neutral; each column gets a country-specific subtitle from `_country.yaml`.

```
POLICY & REGULATION        US: FERC · NERC / regional entity · state PUC · legislature
                           GB: DESNZ · Ofgem · HM Treasury · Parliament
     │ regulates / approves / caps / levies
SYSTEM & MARKET OPERATION  US: ISO/RTO (energy, capacity, ancillary, planning)
                           GB: NESO (balancing, planning) · Elexon (settlement) · LCCC / ESC (levies)
     │ dispatches / settles / operates
WHOLESALE & TRANSMISSION   generators · storage · transmission owners · LSEs · interconnectors
     │ sells to / delivers over wires
DISTRIBUTION & RETAIL      wires utility / DNO · retail provider / supplier / CCA / muni / co-op
     │ sets rate / passes through
CONSUMERS                  residential · small commercial · large C&I · large load
```

Lanes are fixed top-to-bottom. Differences between markets must show up as **missing, extra, or rewired nodes and edges**, never as a different layout. A node whose `kind` exists in only one of the columns on screen gets a visible "unique to this market" marker (match on `kind`, plus `slot`, across countries; on `id` within a country). Same kind, different scope (NESO vs PJM) gets a "≈ differs" marker.

One global **lens** switch: Roles · Bill · Ownership. Only one colour meaning is active at a time, except the Bill lens, which draws the price path (who sets it, accent colour) and the money path (who gets paid, blue) in two colours (Christian, 2026-10-09). Price-setting `mode` is drawn with arrowheads and dash styles, not new colours. The GB price cap is a bracket around the whole bill bar.

## Data model (schema v2)

Principle: **global enums for meaning, per-country profile for words.** UI, tests and cross-country compare key off global values (`kind`, `lane`, `rate_component`, `mode`); labels such as "DNO", "Supplier", "TNUoS" live in `_country.yaml`.

### Three layers per market

1. **`base`** — nodes/edges shared by every variant in the market.
2. **`archetypes`** — structures that change the *shape* of the diagram. Each archetype adds nodes and edges on top of `base` (and may `removes` base ids).
3. **`utilities`** — named labels (PECO, SCE, Oncor, UKPN London) mapped to an `area` (US state; GB DNO licence area) and to the archetypes available there. `fills` binds a `slot` node to a name, owner and optional `domain_area` (one DNO node relabelled per area, its map showing that licence area; the right one of GB's 3 TOs). Added 2026-10-07 with Christian's approval.

Key rule: **the shape depends on the archetype, not the utility.** PECO and PPL draw the same picture with different names. Adding a utility should take minutes; adding an archetype is research. In the US the archetype mostly follows *where you live*; in GB it follows *tariff type and connection point*.

### Market file top level

`schema_version: 2`, `country` (ISO 3166-1 alpha-2), `market` (repo-unique id), `name`, `coverage_note`, optional `bill_components` (overrides the country profile, e.g. ERCOT has no capacity), `base`, `archetypes`, `utilities`.

### Node fields

`id`, `name`, `lane`, `kind`, `description` (1–2 sentences), `jurisdiction` (supranational | national | subnational | local | private; the profile labels them, e.g. US Federal/State, GB GB-wide/Devolved), optional `slot`, `holds_assets`, `owner`, `source`, `status`, `domain_area`.

`domain_area: {full, partial, partial_label, note, source, status}` is where the body's authority applies, drawn as a locator map. `full`/`partial` are area or group ids from the region map that lists the country (`data/maps/<region>.json`; one map per region so cross-border bodies such as NERC, ENTSO-E or a two-country TSO share a frame) (`test_domain_area_ids_exist_in_map`); `partial` is drawn hatched and needs `partial_label` (e.g. FERC over ERCOT: reliability only); `note` is the one-line caption (≤120 chars). Shapes come from public sources only (Census, EIA Energy Atlas, Natural Earth, ONS, NESO), each layer with `credit`, `source` and `licence`; every input is pinned by sha256 in `scripts/maps/sources.json`; each map stays under 100 KB. The page frames each map on the country's home area plus the body's areas. ISO/RTO footprints are county-level approximations from EIA-861 (a county joins an ISO when that ISO's utilities hold ≥30% of its estimated customers); GB is the 14 NESO DNO areas and Northern Ireland is the UK outline minus them. Raw inputs are git-ignored in `scripts/maps/raw/`; copies live in `/mnt/project-files/grid-atlas/map-inputs/`.

`kind`: regulator · policy_maker · legislature · reliability_body · iso · system_operator · settlement_body · scheme_administrator · market · generator · storage · transmission_owner · interconnector · lse · wires_utility · retail_provider · cca · muni · coop · holding_group · consumer.
- `iso` = operator that also runs the energy market (ERCOT, PJM, CAISO). `system_operator` = operates and balances but runs no energy market (NESO). Never tag NESO `iso`.
- `market` = a market or mechanism (PJM RPM, GB Capacity Market, Balancing Mechanism, WEIM/EDAM), separate from the body that runs it.

### Ownership

- `holds_assets: [generation | storage | transmission | distribution | interconnector | metering | substation | distributed_resource]` — physical grid assets this entity owns. Empty = owns none (ISOs, NESO).
  - `substation`: record it separately where the owner differs from the wires owner (generator step-up, large-load or customer-owned substations).
  - `distributed_resource`: behind-the-meter rooftop solar, batteries and EV chargers; usually held by consumer nodes or third-party owners, not the utility.
- `owner: {name, type, parent, node, as_of, source}` — who owns the entity's equity. `type` ∈ public · state_owned · investor_owned · municipal · cooperative · mutual · private_equity · infrastructure_fund · sovereign_wealth · consortium · nonprofit · member_owned. **`source` required**: ownership changes hands and goes stale first. `owner.node` makes build emit an `owns` edge from a `holding_group`.
- Operator ≠ owner: NESO/ISOs `operates` transmission that TOs own.

### Edge fields

| Field | Notes |
|---|---|
| `id`, `from`, `to` | node ids; must resolve |
| `type` | `regulates` · `pays` · `sets_rate` · `dispatches` · `plans_procures` · `delivers` · `owns` · `operates` · `settles` |
| `label` | short verb phrase shown on hover |
| `mode` | `sets_rate`/`pays` only: `sets` (default) · `approves` (revenue/formula, e.g. Ofgem RIIO, FERC) · `caps` (ceiling; may omit component = whole bill) · `levies` (policy levies, taxes) · `passes_through` (supplier, EDC billing someone else's charge) · `market` (price formed by trading) |
| `domain` | `regulates` only: rates · market_rules · reliability · licensing · governance · policy_standard |
| `mechanism` | `dispatches` only: central_sced (US ISOs) · balancing_redispatch · ancillary_contract (GB: generators self-dispatch) |
| `asset` | `owns` (required) and `operates` (required, except when the target is a `market` node, e.g. PJM → RPM) |
| `applies_to` | consumer classes, if class-specific |
| `rate_component` | `generation` · `transmission` · `distribution` · `capacity` · `ancillary_uplift` · `riders_public_purpose` · `exit_fee` · `balancing` · `policy_levy` · `tax` · `supplier_margin` · `metering`. Line items in `subcomponent` (TNUoS, DUoS, CfD, RO, PCIA). Never add a synonym (e.g. no `wholesale_energy`; GB relabels `generation`) |
| `subcomponent` | a bill line can hold several line items with different setters (approved 2026-10-08). Edges with the same `subcomponent` form one item; an edge without one is a hop shared by every item (e.g. the REP that bills everything) |
| `valid_from` / `valid_to` | time-bounded facts (e.g. GB 0% domestic VAT to 2027-03-31) |
| `source` | `{title, url, accessed}` — **required** on every edge |
| `status` | `verified` · `needs_verification` |

Each edge type gets its own color and can be toggled on/off in the UI.

### Consumer classes

`residential`, `small_commercial`, `large_ci`, `large_load` (data centers / very large or transmission-connected). Every class in every archetype must have at least one complete `sets_rate` path, ending at a setter (`sets`, `approves`, `levies`, `market`), for every bill component that applies, and every line item (`subcomponent`) must have exactly one. `build.py` precomputes these as `answers["market|archetype|class|component"] = {items: [{subcomponent, path, setter, mode, limits}], whole_bill_caps}`.

## Archetypes (all `needs_verification` until researched)

**ERCOT (3)**
1. `competitive_area` — customer picks a REP; REP sets energy price; TDSP (e.g. Oncor, CenterPoint) wires rates set by PUCT
2. `noie` — non-opt-in entity: munis (Austin Energy, CPS Energy) and co-ops that haven't opted in; city council/board sets every retail rate, transmission included; the PUCT sets only their wholesale transmission rate. Some have opted in (Nueces EC, Lubbock P&L) and belong in `competitive_area`
3. `coop` — member-owned; board elected by members sets retail rates; PUCT keeps only wholesale transmission rates, certification and a few other items (PURA 41.004). Utilities: Pedernales EC, CoServ

Reliability: FERC → NERC → Texas RE → ERCOT applies even though FERC has no rate or market-rule jurisdiction. PUCT oversees ERCOT.

**PJM (7)** — PJM covers all or parts of 13 states + DC
1. `restructured_choice` — default service in PA, NJ, MD, DE, DC, OH: supply won in a PUC-approved auction or RFP (PA default service, MD SOS, NJ BGS, OH SSO). Residential and small commercial get a fixed auction price; above a size threshold (PECO 100 kW, NJ BGS-CIEP about 500 kW) default service is hourly at PJM's real-time price, with capacity at the RPM clearing price
2. `default_service_ipa` — **only ComEd's zone of IL** (Ameren Illinois is in MISO): the Illinois Power Agency plans and runs the procurement, the ICC approves it, and the generation line has two line items (procured energy blocks, PJM market energy). ComEd buys RPM capacity itself
3. `competitive_supplier` — the customer picked a licensed supplier (PA EGS, NJ TPS, IL ARES, OH CRES); the supplier sets supply, the PUC keeps the wires
4. `municipal_aggregation` — opt-out municipal aggregation (IL, OH, NJ); residential and small commercial only (20 ILCS 3855/1-92)
5. `vertically_integrated` — WV and the PJM part of KY (not LG&E/KU, which are outside PJM); utility owns generation + wires, PSC sets bundled rates
6. `limited_choice` — vertically integrated with limited retail choice: VA (>5 MW), MI (10% cap)
7. `coop` — Virginia co-ops (Rappahannock EC; NOVEC is out until its supply is researched, as it left ODEC) stay under the SCC, which approves their distribution rates and riders; the board governs and may move distribution rates up to 5% in three years (Va. Code 56-231.34, 56-585.3). Their wholesale supply comes from a G&T co-op (ODEC for REC) under a FERC-accepted formula rate the SCC does not regulate. Munis, and Maryland (SMECO) and Delaware co-ops, are not modelled yet

**CAISO (6)** — no central capacity market: resource adequacy is an LSE obligation set by the CPUC and munis, recovered inside the generation rate as its own line item
1. `iou_bundled` — PG&E / SCE / SDG&E do generation + wires; CPUC sets rates; generation holds two line items (energy procurement, resource adequacy)
2. `iou_cca` — CCA board sets generation rate; CPUC sets delivery and the PCIA exit fee; IOU bills
3. `iou_direct_access` — capped program (about 28,800 GWh after SB 237), non-residential only, so this setup has no residential class; ESP sets the generation price
4. `muni_in_caiso` — munis inside CAISO's BA: Anaheim and Riverside turned their transmission over to CAISO as participating transmission owners, so FERC reviews their transmission revenue requirement for CAISO's Transmission Access Charge, while the council sets every retail rate, transmission included. Metered Subsystems are not modelled yet
5. `muni_own_ba` — LADWP, BANC (SMUD is a member and its operator; **SMUD is not itself a BA**), IID, TID: own balancing authorities, but they trade in CAISO's real-time market (WEIM). EDAM went live 1 May 2026

PCIA note: the exit fee is entered as a `subcomponent` line item of `riders_public_purpose` (the non-bypassable charges the IOU bills) rather than as the `exit_fee` component, because a market-level component would read as a missing bill line for bundled and muni customers. Decided 2026-10-09 (Christian): keep it as a line item.

**GB (4)** — research and sources in `docs/research/policy.md`
1. `domestic_default_capped` — SVT/deemed tariff under Ofgem's default tariff cap (`caps` edge on the whole bill); supplier sets the actual price
2. `supplier_contract` — domestic fixed and all non-domestic; no cap; CCL and full RO for non-domestic
3. `transmission_connected` — no DNO/DUoS; NESO bills TNUoS directly; may be its own BSC party
4. `idno_network` — extra wires node (IDNO) inside a DNO area; IDNO charges capped relative to the host DNO

Variants, not archetypes: Scotland vs England & Wales (different TO, ROS, AAHEDC), prepayment, Supplier of Last Resort, EII/BICS exemptions. Deferred: private wire / licence-exempt supply.

Coverage (what each market excludes, e.g. parts of Texas outside ERCOT, Northern Ireland outside GB) is shown by the domain map, not as a text line. `coverage_note` stays in the data for tests and the map caption.

## Claims as tests

Market facts used in the diagram are written as pytest assertions in `validate/test_claims.py`, the same pattern as `distribution-viz/validate/benchmarks.py`. Wrong data should fail a test, not silently draw a wrong diagram. Examples:

- every consumer class in every archetype has a complete `sets_rate` path for each applicable bill component
- only regulators `caps`; only policy makers/regulators/levy counterparties `levies`; `passes_through` only from the retail lane
- ISOs and NESO hold no assets and have no `owns` edges
- every ownership claim and every edge has a `source.url`
- ERCOT has no capacity component or capacity market node; FERC has no `regulates` edge with `domain` rates/market_rules into ERCOT, but the reliability path FERC → NERC → Texas RE → ERCOT exists
- PJM has an RPM `market` node operated by PJM
- CAISO has no central capacity auction; CPUC `plans_procures` RA; CAISO `iou_cca` has a CCA setting `generation` for `residential`; SMUD is not a BA
- GB: no `iso`, no `reliability_body`, no `central_sced`; NESO is publicly owned and owns nothing; only Ofgem `caps`, and only in `domestic_default_capped`; Elexon `settles`; no generator pays BSUoS; levies and taxes reach residential; 14 DNO areas
- LG&E/KU and Ameren Illinois never map to PJM; El Paso Electric, SPS and Entergy Texas never map to ERCOT
- a test lists all `needs_verification` edges and empty markets — allowed to exist, but it reports the count so it trends to zero

Do **not** assert volatile or undecided facts (GB unit bidding, TNUoS redesign, settlement period length, capacity clearing prices).

Use `xfail(strict=True)` with a reason for known gaps rather than deleting a test. Claims for markets not yet entered are strict xfails tagged with their milestone; when the data lands they XPASS → fail, and you delete the marker.

## Terminology (use consistently in data, UI, and commits)

The glossary lives in each `_country.yaml` (with `equivalent:` cross-country links) and drives UI tooltips. Core terms:

| Term | Meaning |
|---|---|
| ISO / RTO | Independent System Operator / Regional Transmission Organization; operates the grid and wholesale markets; owns no wires |
| BA | Balancing authority |
| FERC | Federal Energy Regulatory Commission; wholesale + interstate transmission |
| NERC / RE | Reliability standards body / regional entity (Texas RE, WECC, RF, SERC…) |
| PUC / PUCT / CPUC | State utility commission (Texas / California) |
| IOU | Investor-owned utility |
| Muni / co-op | City-owned / member-owned utility |
| NOIE | ERCOT non-opt-in entity (muni or co-op outside retail competition) |
| LSE | Load-serving entity; buys wholesale power for end customers |
| REP | Retail electric provider (ERCOT term) |
| TDSP / EDC | Wires-only utility (ERCOT term / PA term) |
| CCA | Community Choice Aggregation; city/county buys power for residents by default, IOU keeps wires + billing |
| PCIA | Power Charge Indifference Adjustment; CA exit fee paid by CCA/DA customers |
| DA / ESP | Direct Access / Electric Service Provider (CA) |
| RA | Resource adequacy (CA's capacity obligation program) |
| Default service | Supply for customers who don't pick a retailer in restructured states |
| Restructured vs vertically integrated | Generation separated from wires with retail choice vs one utility doing both |
| NESO | GB National Energy System Operator; publicly owned, balances and plans, owns no assets, runs no energy market |
| Ofgem / DESNZ | GB regulator / GB energy ministry |
| Elexon | GB balancing and imbalance settlement (BSC) |
| LCCC / ESC | GB CfD counterparty / Capacity Market settlement body |
| DNO / IDNO | GB distribution network operator (14 licence areas) / independent DNO on embedded networks |
| Supplier | GB licensed retailer (≈ REP/LSE) |
| TNUoS / BSUoS / DUoS | GB transmission / balancing / distribution use-of-system charges |
| Price cap | Ofgem's ceiling on domestic default tariffs (not a set rate) |

Define a term in the UI tooltip the first time it appears in a market column.

## UI copy (all on-screen text)

- Facts only: who, what, which mechanism, which source. No narrative or scene-setting lines (e.g. "Where the electricity goes..."), no marketing tone, no rhetorical questions in body text.
- Every abbreviation shown in a label has a glossary entry in that country's `_country.yaml`. `test_ui_abbreviations_are_defined` enforces this.
- Spell out a term rather than abbreviate it when it appears only once (e.g. "large commercial & industrial", not "large C&I").
- Glossary meanings: at most 200 characters, starting with the expansion. `test_glossary_meanings_are_short` enforces this.
- Use labels, not sentences: "Diagram not built yet", not "The diagram will arrive soon".

## Milestones (~49 hours to GB)

1. **Scaffold + schema v2 + validator (~4.5 h).** Done when: `pytest` passes on empty market files and `scripts/build.py` writes `web/data.json` + `web/data.js`. **Done 2026-10-07.**
2. **US profile + ERCOT data + local render (~4.5 h).** Done when: `web/index.html` opened locally shows all 3 ERCOT archetypes via dropdowns and the ERCOT claim tests pass (strict xfails removed).
3. **PJM + CAISO + side-by-side compare (~11.5 h).** Done when: 2-up and 3-up columns render, dropdowns chain State → Utility → Supply, unique nodes are flagged by `kind`.
4. **"Who sets my rate?" panel (~2.5 h).** Done when: picking market + archetype + consumer class highlights the full `sets_rate` path for each bill component, with caps/approves limits shown.
5. **GitHub Pages (~1 h).** Done when: the public URL renders the same as local.
6. **Great Britain (~16.5–18.5 h).** GB profile, `gb.yaml` with 4 archetypes, 14 DNO areas + 5 owner groups + 3 TO fills (all sourced), GB claim tests, ownership lens, cross-country compare, layout hardening (lane-skipping edges, dense lanes, mobile).
7. **MISO, SPP, NYISO, ISO-NE (~8 h).** Schema should not change; if it must, stop and discuss first.

## Working conventions

- Research before data entry. Every fact gets a primary source (ISO, FERC, PUC, utility tariff, EIA; Ofgem, DESNZ/gov.uk, legislation.gov.uk, NESO, Elexon, LCCC) where possible; secondary sources mark the edge `needs_verification`. `docs/research/` holds the sourced research; [NV] items there stay `needs_verification`.
- **Source-backed verification of every line (Christian, 2026-10-08; replaces the human expert check, which is unlikely to happen).** A line (edge) is marked `status: verified`, and drawn solid, only when two independent Claude power markets reviewers each confirm it against a primary source (statute, regulation, tariff, regulatory order, or the official publication of the ISO, regulator or body itself): the relationship exists, `type`, `mode`, `domain`, `rate_component` and line item are right, and the cited `source` supports it. Lines with only secondary sources (press releases, news, third-party summaries), or where any reviewer rejects or is unsure, stay `needs_verification` and are drawn dashed. Changing a verified line's meaning or source resets it to `needs_verification` until it is reviewed again. Verdicts live in `docs/research/line-review.json` (summary and source fixes in `line-review.md`); `test_verified_lines_cite_a_primary_source` enforces the source rule.
- **Review gate before every PR (Christian, 2026-10-08).** Each step gets two reviews before its PR opens or is updated: a power markets review (every new or changed node and line: does it exist, are `type`, `mode`, `domain`, `rate_component` and line items right, does the source support it) and a UI/UX review (the rendered page at desktop and phone widths against the UI copy and layout rules here). Confirmed findings are fixed in the same PR; the PR description says what each review found and fixed. New or changed lines go through the source-backed verification above before they are marked `verified`.
- **Every line shows its source.** `source` is required on every edge (schema), shown on hover, in the line's detail panel, and under "Lines" in each connected box's panel. `test_every_line_shows_its_source` enforces this.
- Never invent a node or edge to make a diagram look complete. Leave it out and log the gap in the PR/commit.
- Schema v2 is settled. Further schema changes: stop and discuss first.
- Quote YAML flow-map values that contain commas; `additionalProperties: false` will catch it, but only if you run the build.
- `web/data.json` and `web/data.js` are generated; edit YAML, then run `python3 scripts/build.py`.
- Keep the front end a single dependency-free file.
- Run `pytest` before every commit. `validate/test_layout.py` opens the page in headless Chromium and fails if any relationship line in any view is hidden under other lines or runs through a box it doesn't connect. It is skipped without Playwright (`pip install -r requirements-dev.txt && python3 -m playwright install chromium`); GitHub CI (`.github/workflows/test.yml`) always runs it.
- Commit per milestone step with a message stating what now works and how to check it.

## Working with Christian

- Lead with the command, path, or snippet; prose after.
- Number multi-step tasks; one bounded action per step.
- Restate progress every turn ("step 2 of 6 done: X. Next: Y").
- Give time estimates in concrete units.
- Errors: state cause and fix, no hedging.
- Include a diagram when introducing a new concept.
- Finish the current issue before raising another; raise the second once, at the end.
- End with one concrete next action doable in under two minutes.
- Ask before destructive actions.
