# grid-atlas: adding countries (GB first), plus ownership

Status: **approved 2026-10-07** ("Approve all"). Adopted as schema v2 in milestone 1.

```
docs/research/policy.md          GB institutions, bill components, archetypes, US fixes (every claim sourced + [V]/[K]/[NV])
docs/research/power_systems.md   dispatch, settlement, charging, reliability, test assertions
docs/research/ux.md              13 UX decisions with wireframes
docs/research/software.md        schema v2, build, tests, effort
```

## Headline

GB fits the five-lane template, but **not the current schema**. CLAUDE.md says to stop and discuss before schema changes, so this asks for sign-off on 8 additive changes (section 2). Because `grid-atlas` hasn't been scaffolded yet (it's not in `~/Documents/GitHub`), v2 can be the day-one schema: zero migration.

The core contrast the tool will show:

```
US (PJM)                                  GB
─────────────────────────────────         ──────────────────────────────────────────────
POLICY & REG   FERC · NERC/RF · PUC        DESNZ · Ofgem · HM Treasury · Parliament
SYSTEM & MKT   PJM  (one body: dispatch,   NESO (balancing, planning; owns no assets)
               market, capacity, settle)   Elexon (settlement) · LCCC/ESC (CfD, CM levies)
                                           EPEX/N2EX (exchanges; no central pool)
WHOLESALE & TX generators · TOs · LSEs      generators · NGET / SPT / SHET · OFTOs · interconnectors
DIST & RETAIL  EDC (wires) · supplier/     DNO (14 areas, 5 owner groups) · supplier
               default service
CONSUMERS      residential … large load    domestic … transmission-connected
Shape varies by WHERE you live             Shape varies by TARIFF and CONNECTION, not place
```

## 1. What changed or is in flux (data must carry these)

| Fact | Date | Source |
|---|---|---|
| NESO publicly owned (SoS shareholder), owns no assets | 1 Oct 2024 | gov.uk NESO designation |
| Elexon owned by the 13 largest BSC parties | 1 Oct 2024 | elexon.co.uk ownership change |
| Zonal pricing rejected; single national price stays | 10 Jul 2025 | gov.uk REMA summer update 2025 |
| RIIO-3 transmission from Apr 2026; ED3 distribution from Apr 2028 | 2025–28 | Ofgem RIIO-3 FDs, ED3 framework |
| Exchequer pays 75% of domestic RO; ECO off bills; WHD £150 | 1 Apr 2026 | gov.uk energy bill reductions statement |
| 0% VAT on GB domestic electricity (not NI) | 1 Oct 2026 – 31 Mar 2027 | SI 2026/987 |
| Price cap £1,723 (Oct–Dec 2026) | 26 Aug 2026 | Ofgem press release |
| Iberdrola owns ENWL → **5 groups** own the 14 DNO areas | 2025 | SP Energy Networks, CMA |
| BSUoS demand-only, fixed tariff | Apr 2023 | NESO (CMP308/361) |
| No CATO licensed yet; first tender ~2027 | 2026–27 | law-firm summary [NV] |

## 2. Schema v2: what needs your sign-off

All additive. Existing US data stays valid (new fields default sensibly).

1. **Country + market.** Top-level `schema_version: 2`, `country: GB|US`, `market: gb|ercot|pjm|caiso`. Layout `data/countries/<cc>/_country.yaml` + `<market>.yaml`.
2. **Country profile** (`_country.yaml`): lane subtitles, kind/component labels, dropdown chain labels, glossary with `equivalent: {US: …}`, bill components per class. Moves terminology out of CLAUDE.md into data.
3. **Jurisdiction** becomes `supranational | national | subnational | local | private` (US *displays* Federal/State; GB displays Devolved).
4. **New node kinds:** `system_operator` (NESO; never `iso`), `settlement_body` (Elexon), `scheme_administrator` (LCCC, ESC), `policy_maker` (DESNZ, HMT), `holding_group`, `interconnector`, `reliability_body` (NERC, Texas RE, WECC…), `market` (RPM, GB Capacity Market, Balancing Mechanism, WEIM/EDAM).
5. **New edge types** `owns`, `operates`, `settles`, plus qualifiers: `regulates.domain` (rates, market_rules, reliability, licensing…) and `dispatches.mechanism` (central_sced, balancing_redispatch, ancillary_contract).
6. **`mode` on `sets_rate`**: `sets` (default) · `approves` (Ofgem RIIO, FERC formula rates) · `caps` (GB price cap; may omit component = whole bill) · `levies` (CfD, CM, taxes) · `passes_through` (supplier, EDC) · `market` (price formed by trading, nobody sets it). Chosen over new edge types so "who sets my rate?" stays one walk.
7. **`rate_component` additions:** `balancing`, `policy_levy`, `tax`, `supplier_margin`, `metering`; line items in `subcomponent` (TNUoS, DUoS, CfD, RO, PCIA). No v1 value renamed; GB just labels `generation` "Wholesale energy".
8. **Ownership:** node `holds_assets: [transmission, distribution, …]` kept separate from `owner {name, type, parent, as_of, source}` (source required). NESO = state-owned, holds nothing. Plus `slot`/`fills` so one DNO node is relabelled per area (never 14 nodes), and `valid_from/valid_to` on edges for time-bounded facts like the VAT window.

One CLAUDE.md fix regardless of GB: `fetch('data.json')` fails from `file://` in Chrome/Firefox/Safari. **Fix:** `build.py` also writes `web/data.js` (`window.GRID_ATLAS = …;`) loaded by a `<script>` tag.

## 3. GB archetypes (4)

Dropdown chain for GB: **Nation → Distribution area (14 + IDNO) → Tariff type.** Scotland vs England & Wales is a label variant (different TO, ROS, AAHEDC), not a shape change.

| Archetype | Shape difference | Key edges |
|---|---|---|
| `domestic_default_capped` | Ofgem `caps` edge on the whole bill | Ofgem caps; supplier sets under cap; VAT 0% to Mar 2027 |
| `supplier_contract` (domestic fixed + all non-domestic) | No cap; CCL for non-domestic | Supplier sets; full RO for non-domestic |
| `transmission_connected` | No DNO / no DUoS; NESO bills TNUoS direct | May be its own BSC party |
| `idno_network` | Extra wires node between DNO and customer | IDNO charge capped relative to host DNO |

Variants, not archetypes: prepayment, Supplier of Last Resort, EII/BICS exemptions. Deferred: private wire / licence-exempt supply. Northern Ireland is **not GB**: future separate `sem` market (Utility Regulator, SONI, NIE Networks). Never label GB as "UK".

### Who sets each part of a GB domestic bill

| Component | Sets / approves | Collected via | Mode |
|---|---|---|---|
| Wholesale energy | Market (EPEX/N2EX, bilateral) | Supplier | market → supplier sets |
| TNUoS | Ofgem approves TO revenue; NESO sets tariffs | NESO → TOs | approves / sets |
| BSUoS | NESO (fixed tariff, demand only) | NESO | sets |
| DUoS | Ofgem approves (ED2); DNO sets tariffs (CDCM/EDCM) | DNO | approves / sets |
| Capacity Market | DESNZ rules; NESO runs auction; ESC levies | ESC | levies |
| CfD, Nuclear RAB | DESNZ; LCCC levies | LCCC | levies |
| RO (25% domestic), FiT, WHD | DESNZ; Ofgem administers | Supplier | levies |
| VAT | HM Treasury (0% to 31 Mar 2027) | Supplier → HMRC | levies (tax) |
| Supplier costs + margin | Supplier; allowance inside cap | Supplier | sets |
| Whole bill | **Ofgem cap (ceiling, default tariffs only)** | n/a | caps |

## 4. Engineering nuances the diagram must not get wrong

1. **No central dispatch in GB.** Generators self-dispatch (FPNs); NESO only redispatches via the Balancing Mechanism after gate closure. GB `dispatches` edges use `mechanism: balancing_redispatch`; US ISOs use `central_sced`.
2. **Operator ≠ owner.** NESO `operates` transmission owned by NGET/SPT/SHET; same split for US ISOs vs TOs.
3. **132 kV is transmission in Scotland, distribution in England & Wales.**
4. **Elexon is its own node** (imbalance + BM settlement); NESO funds BM costs and recovers them via BSUoS.
5. **Transmission charge basis** differs: GB site-day band (TCR), ERCOT 4CP, PJM 1CP. Optional `basis` field, deferred.
6. **Do not assert as tests:** unit-based bidding, TNUoS redesign, settlement period length, CM clearing prices. All undecided or volatile.

## 5. Corrections to the US scaffold in CLAUDE.md

| Region | Current text | Fix |
|---|---|---|
| ERCOT | "ERCOT wholesale is not FERC-rate-regulated (no `regulates` FERC→ERCOT)" | Keep for `domain: rates/market_rules`; **add** reliability path FERC→NERC→Texas RE→ERCOT and PUCT→ERCOT oversight |
| ERCOT | `muni_opted_out` | Rename `noie` (non-opt-in entity); PUCT still sets munis' transmission rates; Nueces EC and Lubbock P&L have opted in |
| PJM | restructured states list | Only ComEd's zone of IL is in PJM (Ameren is MISO); only part of KY (not LG&E/KU); PJM is 13 states + DC |
| PJM | `hybrid` = VA | Define as "vertically integrated with limited choice": VA (>5 MW) and MI (10% cap) |
| PJM | — | Missing archetype: opt-out municipal aggregation (OH, IL, NJ) |
| CAISO | `muni_own_grid` "outside CAISO's market", "SMUD own BA" | SMUD is not a BA (**BANC** is). LADWP, BANC, IID, TID trade in CAISO's WEIM; EDAM live 1 May 2026 |
| CAISO | `muni_in_caiso` | Split munis that own transmission under CAISO control (Anaheim, Riverside) from Metered Subsystems |
| CAISO | — | No capacity market: RA set by CPUC/munis (test: no central capacity auction node) |
| All | — | Load pays zonal/aggregate prices, not nodal LMP |

## 6. UX (summary of ux.md)

1. **Country is the first link in each column's dropdown chain**, so PJM vs GB side by side works. Single-market countries show the market as a locked chip ("GB: one national market, no regional ISOs").
2. **Lane ids unchanged; display names become neutral:** POLICY & REGULATION · SYSTEM & MARKET OPERATION · WHOLESALE & TRANSMISSION · DISTRIBUTION & RETAIL · CONSUMERS, with a local-terms subtitle per column.
3. **One lens switch: Roles · Bill · Ownership.** Only one colour meaning is active at a time (keeps it colour-blind safe). Ownership lens recolours nodes by owner type, shows licence holder vs ultimate owner, foreign-parent country chip, and dims "owns no assets" nodes (NESO, ISOs). A side table lists the 14 DNO areas and their 5 owner groups.
4. **Price-setting mode** drawn with arrowheads/dash styles, not new colours; pass-through nodes get a hollow ring ("collects"); the price cap is a bracket around the whole bill bar.
5. **"Unique to this region"** matches on node `kind` across countries (otherwise every GB node is unique), plus a "≈ differs" marker for same role, different scope (NESO vs PJM).
6. **Glossary tooltips** with "≈ equivalent" and "≠ difference" lines (DNO ≈ EDC/TDSP; supplier ≈ REP/LSE) and a generated crosswalk table.
7. **List view** (text twin of the diagram) for screen readers, print and phones; state in `location.hash` for shareable links.
8. Deferred: GB tile map, £-scaled bill bar, time slider, Germany / NEM / SEM.

## 7. Plan and effort

| # | Step | Hours |
|---|---|---|
| 1 | Milestone 1: scaffold on schema v2 (country folders, profile, `build.py` → `data.json` + `data.js`, tests). Lift from `v2check/`. | 4.5 |
| 2 | Milestone 2: US profile + ERCOT + render (with fixes from section 5) | 4.5 |
| 3 | Milestone 3: PJM + CAISO + compare (kind-based unique markers) | 11.5 |
| 4 | Milestone 4: "Who sets my rate?" (precomputed by build) | 2.5 |
| 5 | Milestone 5: GitHub Pages | 1 |
| 6 | **New milestone: GB** (profile, `gb.yaml`, 14 DNO areas, claim tests, ownership lens, cross-country compare, layout hardening) | 16.5–18.5 |
| 7 | Milestone 6: MISO, SPP, NYISO, ISO-NE (schema should not change again) | 8 |
| | **Total** | **~48.5–50.5 h** (was 29 h incl. milestone 6) |

## 8. Biggest open uncertainties ([NV] in policy.md)

- Which code manager holds which GB code after the 2026–27 appointments.
- SSEN Transmission ownership split (SSE 75% / OTPP 25%) and UKPN's consortium split.
- Nuclear RAB levy start date (~Dec 2025); BSUoS fixed-tariff period length; current Ofgem IDNO and AAHEDC URLs.
- Ofgem Review reforms need primary legislation; modelled as current law.
- California DA cap changes, Ohio HB 15 effect on default service, 2027 EDAM entry dates for LADWP/BANC.
- Grid Code BM thresholds (100 / 30 / 10 MW by TO area) cited to the Grid Code page, not the clause.
