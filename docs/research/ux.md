# grid-atlas: switching countries (UX and information design proposal)

Reviewer role: senior UX / information designer. Scope: adding countries (GB first; DE, AU-NEM and IE-SEM later) to the single-file `web/index.html` so that three questions can be answered at a glance:

1. **Who regulates what?**
2. **Who sets each part of the bill?** This now has to cover ceilings, approved revenue envelopes, levies and taxes, not only "sets rate".
3. **Who owns which part of the grid?** This covers the owner type, the ultimate parent and its country, and the difference between owner and operator.

The layout rule stays as it is: *differences show as missing, extra or rewired nodes, never as a different layout.*

> GB facts below that I have not checked against a primary source are marked `[verify]`. They are design examples, not data. Under the CLAUDE.md rule, each one becomes an edge or node with a `needs_verification` status.

---

## 0. Summary of decisions

| # | Decision | One-line rationale |
|---|---|---|
| D1 | **Country is the first link in each column's chain**: Country, then Market, then three country-labelled levels | Each column stays self-contained, so cross-country compare comes free |
| D2 | **Cross-country compare: yes** (for example PJM next to GB), with "unique" markers matched on a canonical `role` instead of node id | Contrast is the purpose of the tool. Without role-matching, every GB node would be flagged unique and the marker would mean nothing |
| D3 | The Market level is always shown. **When a country has one market it shows as a locked chip, not a dropdown** | Keeps the grid of controls the same and says so plainly: "GB: one national market, no regional ISOs" |
| D4 | The 3 chain slots keep their positions. **Their labels come from the data**: US is State, Wires utility, Supply option. GB is Nation, Distribution area, Tariff type | Same layout, local vocabulary |
| D5 | **Lane ids stay as they are. Display names become country-neutral, and each column gets a country-specific subtitle** | No data migration, and NESO, which runs no energy market, still fits lane 2 honestly |
| D6 | **One global "lens" switch: Roles · Bill · Ownership.** Exactly one colour meaning is active at a time | This is the only way to keep edge colours and ownership colours colour-blind safe at the same time |
| D7 | Ownership is shown as **node fill, a letter glyph and a parent-country chip in the Ownership lens**. There is no separate view and no geographic map in v1 | Keeps the same diagram, so the "who regulates" and "who owns" answers line up node for node |
| D8 | **Price-setting mode is an attribute of `sets_rate` edges** (`sets`, `caps`, `approves_revenue`, `levies`, `taxes`, `market`), encoded by line terminator and dash, not by new colours | Six edge colours is already the limit |
| D9 | **Pass-through is a property of the node on the path** (shown as a hollow ring and the word "collects"), not of the edge | A supplier that bills DUoS does not set it. The path makes that visible |
| D10 | **The GB price cap is drawn as a bracket around the whole bill bar**, not as a cap on one component | The cap limits the total unit rate and standing charge, not each line separately `[verify wording against Ofgem cap methodology]` |
| D11 | **Terms carry a canonical role key. Tooltips give an "≈ equivalent" line plus a "not the same because…" line, and a Crosswalk drawer is generated from the same keys** | Deals with false friends without a separate hand-built glossary |
| D12 | **Accessibility: a List view (text twin of the diagram)**, keyboard focus on nodes, redundant encodings, Okabe-Ito palette, tap-to-pin tooltips | One mechanism covers screen readers, phones and print |
| D13 | **Shareable state in `location.hash`** | Works from `file://` and lets a comparison be shared as a link |

**Schema warning.** CLAUDE.md says "Schema should not change; if it must, stop and discuss first." The country feature needs additive schema changes (section 8). This needs Christian's sign-off before any code is written.

---

## 1. Where the country switch lives

### Decision D1: per-column chain, Country first

```
┌─ grid-atlas ─────────────────────────────────────────────────────────────────┐
│ Compare: [ 1 ][●2 ][ 3 ]   Lens: (●Roles)( Bill )( Ownership )   [List view] │
│ Presets: PJM vs GB · ERCOT vs GB · CAISO vs GB · ERCOT/PJM/CAISO             │
├──────────────────────────────────────┬───────────────────────────────────────┤
│ Country  [ United States  ▾]         │ Country  [ Great Britain  ▾]          │
│ Market   [ PJM (ISO/RTO)  ▾]         │ Market   ⟦ GB national market 🔒ⓘ ⟧   │
│ State    [ Pennsylvania   ▾]         │ Nation   [ England         ▾]         │
│ Wires utility [ PECO      ▾]         │ Distribution area [ London (UKPN) ▾]  │
│ Supply option [ Default service ▾]   │ Tariff type [ Default (price-capped)▾]│
│ Consumer [ Residential ▾]            │ Consumer [ Domestic ▾]                │
├──────────────────────────────────────┴───────────────────────────────────────┤
│                       (five-lane diagram, see section 2)                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Each column has its own Country picker. It is not a global switch.** A global country switch would make PJM vs GB impossible. The control lives inside the column it controls.
- **Market level (D3).** The generic label is **"Market"**. US values are `PJM (ISO/RTO)`, `ERCOT (ISO)` and so on. For GB, the single value `GB national market` is drawn as a locked chip. Its ⓘ reads: *"Great Britain has one wholesale market and one system operator (NESO). There are no regional ISOs. NESO balances the system but does not run a day-ahead energy market."*
- **Coverage note**, following the Texas/ERCOT note: *"Northern Ireland is not in the GB market. It is part of the all-island Single Electricity Market (SEM)."* "GB" is used on purpose; the label never says "UK".
- **Chain labels per country (D4)** are stored in country data (`levels: [{key, label, help}]`):

| Slot | US | GB | DE (later) | AU-NEM (later) | IE-SEM (later) |
|---|---|---|---|---|---|
| Market | ISO/RTO | GB national market (locked) | DE-LU bidding zone (locked) | NEM | SEM (locked) |
| Level 1 | State | Nation | Federal state | NEM region | Jurisdiction (IE / NI) |
| Level 2 | Wires utility | Distribution area | Grid operator (DSO), searchable | Distribution network | Distribution system |
| Level 3 | Supply option | Tariff type | Supply contract | Offer type | Tariff type |

- **The GB Nation level filters distribution areas.** SP Manweb (Merseyside and North Wales) appears under both England and Wales `[verify]`. Choosing a distribution area automatically picks the transmission owner shown in the Wholesale lane: E&W areas give NGET, central and southern Scotland give SP Transmission, the north of Scotland gives SHE Transmission. **That is a rewired node, not a new layout.**
- **GB archetypes (Level 3), first cut:** `domestic_default_capped`, `domestic_fixed`, `non_domestic_contract`. Later: `idno_connected` and `prepayment` (the cap level differs, but the shape is probably the same; if the shape is the same, it is a label and not an archetype).
- **Rejected:** a global country switch at the top. It blocks cross-country compare.
- **Rejected:** a mixed tree dropdown (one picker containing "US › PJM › PA…"). It is deep, hard to use on mobile, and hides the separate levels.
- **Rejected:** hiding the Market row when there is only one market. Then GB's chain would be one row shorter than PJM's next to it, which breaks the alignment rule and hides a real difference.

### Decision D2: cross-country compare, with role-matched "unique" markers

Within one country, matching nodes by `id`/`kind` works. Across countries it fails: NESO ≠ PJM, so every node would be flagged "unique". Proposed fix:

- Every node gets a canonical **`role`** from a small controlled list (see section 8). Examples: `system_operator`, `wholesale_market_venue`, `imbalance_settlement`, `transmission_owner`, `distribution_operator`, `retail_supplier`, `default_supplier`, `energy_regulator`, `policy_ministry`, `levy_counterparty`.
- The "unique" marker becomes three-state:

| Marker | Meaning | Example (PJM vs GB) |
|---|---|---|
| `★ unique` | Role present only in this column | GB `levy_counterparty` (LCCC); PJM `state_puc` |
| `≈ differs` | Role in both columns, but `role_notes` say the scope differs | PJM ISO vs NESO: both `system_operator`, but only PJM runs the energy and capacity markets |
| (none) | Same role, same scope | generators, consumers |

- When the columns are from different countries, a thin banner shows: *"Comparing across countries. Names differ, so nodes are matched by role. Open Crosswalk ↗."*

---

## 2. Making the five lanes country-neutral

### Decision D5

Lane **ids** stay the same: `regulators`, `market_operator`, `wholesale`, `retail`, `consumers`. No YAML changes for the US files. Only the **display names** change. Each column also gets a **subtitle generated from the node kinds actually present**, using local names.

| Lane id | New display name | US subtitle (example: PJM) | GB subtitle |
|---|---|---|---|
| regulators | **POLICY & REGULATION** | FERC · NERC/RFC · PA PUC · legislature | DESNZ · Ofgem · Parliament · HM Treasury |
| market_operator | **SYSTEM & MARKET OPERATION** | PJM (energy, capacity, ancillary, planning) | NESO (balancing, planning) · Elexon (settlement) · power exchanges · LCCC / ESC (levy settlement) |
| wholesale | **WHOLESALE & TRANSMISSION** | generators · storage · TOs · LSEs | generators · storage · interconnectors · NGET / SPT / SHET · OFTOs |
| retail | **DISTRIBUTION & RETAIL** | wires utility · retail supplier | DNO (licence area) · supplier |
| consumers | **CONSUMERS** | residential · small comm. · large C&I · large load | domestic · microbusiness · large I&C · large load |

Why these names:
- "POLICY & REGULATION" is needed because DESNZ makes policy and is not a regulator. The old name would have filed it wrongly.
- "SYSTEM & MARKET OPERATION" fits NESO, Elexon, EPEX/N2EX and the levy counterparties without claiming that one body does everything. In the US this lane still holds only the ISO.
- "WHOLESALE & TRANSMISSION" makes the TO's place explicit. This matters more in GB, where TOs and the SO are legally separate.
- "DISTRIBUTION & RETAIL" names both halves of the existing lane. The old "RETAIL" made US wires utilities look like retailers.

Placement rules for GB nodes that could fit two lanes:
- **Suppliers go in the Retail lane**, with `pays` edges up to the Wholesale lane. This is the same place as an ERCOT REP, so the PJM-vs-GB and ERCOT-vs-GB comparisons line up.
- **LCCC and ESC go in lane 2**, not lane 1. They settle money; they do not regulate. Their policy parent (DESNZ) sits in lane 1 with a `regulates`/`plans_procures` edge down.
- **NESO goes in lane 2 with an "owns no assets" note**, which the Ownership lens makes visible (section 3).

### Diagram, PJM vs GB, Roles lens

```
              PJM · PA · PECO · Default service · Residential │ GB · England · London (UKPN) · Default capped · Domestic
POLICY &     ┌─────┐ ┌──────┐ ┌───────┐ ┌───────────┐       │ ┌──────┐★┌──────┐ ┌──────────┐ ┌────────────┐★
REGULATION   │FERC │ │NERC/ │ │PA PUC │ │Legislature│       │ │DESNZ │ │Ofgem │ │Parliament│ │HM Treasury │
             └──┬──┘ │RFC   │ └───┬───┘ └───────────┘       │ └──┬───┘ └──┬───┘ └──────────┘ └─────┬──────┘
                │    └──────┘     │                         │    │ policy  │ licences, RIIO, cap    │ VAT
SYSTEM &     ┌──┴─────────────────┴──────┐                  │ ┌──┴────┐≈ ┌───────┐★┌─────────┐ ┌────────────┐★
MARKET OPS   │ PJM Interconnection     ≈ │                  │ │ NESO  │  │Elexon │ │EPEX/N2EX│ │ LCCC · ESC │
             │ energy·capacity·AS·plan   │                  │ │balance│  │settles│ │exchanges│ │ CfD · CM   │
             └───────────┬───────────────┘                  │ └──┬────┘  └───┬───┘ └────┬────┘ └─────┬──────┘
WHOLESALE &  ┌──────────┐ ┌──────┐ ┌──────┐ ┌─────┐         │ ┌──────────┐ ┌──────┐ ┌────────┐★┌───────┐
TRANSMISSION │generators│ │stor. │ │ TOs  │ │LSEs │         │ │generators│ │stor. │ │ NGET   │ │interc.│
             └──────────┘ └──────┘ └──────┘ └─────┘         │ └──────────┘ └──────┘ └────────┘ └───────┘
DISTRIBUTION ┌────────────────┐ ┌───────────────────┐       │ ┌────────────────┐  ┌───────────────────┐
& RETAIL     │ PECO (wires)   │ │ default service ★ │       │ │ UKPN (DNO)     │  │ supplier          │
             └────────┬───────┘ └─────────┬─────────┘       │ └────────┬───────┘  └─────────┬─────────┘
CONSUMERS    ┌────────┴───────────────────┴────────┐        │ ┌────────┴────────────────────┴────────┐
             │ Residential                         │        │ │ Domestic                             │
             └─────────────────────────────────────┘        │ └──────────────────────────────────────┘
 Legend (Roles lens): ── regulates  ── pays  ── sets rate  ── dispatches  ── plans/procures  ── delivers
                      ★ unique role in this column   ≈ same role, different scope
```

(Edge colours are not drawable in ASCII. Each edge type has its own colour plus a dash pattern; see section 6.)

---

## 3. Showing ownership without cluttering the role diagram

### Options considered

| Option | Verdict | Reason |
|---|---|---|
| A. Owner badges always on | Rejected | Adds 2 to 3 extra text items per node all the time. It clutters the Roles view and fights with "★/≈" markers |
| B. Separate "who owns the wires" view (different layout, for example a tree of parent companies) | Rejected | Breaks the one-layout rule and loses the link "this owner, in this role" |
| C. Geographic inset (map of the 14 GB licence areas) | Deferred to v2, as a tile cartogram | CLAUDE.md puts geographic drill-down out of scope. Real boundaries need geodata (file size, licensing). The dropdown chain already answers "which area am I in" |
| **D. Ownership lens: same diagram, nodes recoloured by owner type, with glyph and parent chips** | **Chosen** | Same positions, so each answer maps one-to-one onto the Roles view. One colour meaning at a time (D6) |

### Ownership lens encoding

- **Fill = owner type**, always paired with a **letter glyph** in the top-left corner so colour is never the only cue:

| Glyph | Owner type | Examples |
|---|---|---|
| **G** | Public / government-owned (department, public corporation, state-owned company) | NESO, LCCC, ESC, Ofgem, DESNZ `[verify NESO and Elexon ownership after the 2024 NESO transfer]` |
| **M** | Municipal / local government | Austin Energy, LADWP, (DE) Stadtwerke |
| **C** | Co-operative / mutual / member-owned | US co-ops |
| **L** | Investor-owned, listed parent | NGET and NGED (National Grid plc), SSEN (SSE plc), Iberdrola subsidiaries |
| **P** | Investor-owned, private / infrastructure fund | UKPN (CK group consortium) `[verify]`, Northern Powergrid (Berkshire Hathaway Energy) |
| **X** | Mixed / multiple owners (aggregate nodes) | "generators", "suppliers", OFTOs |

- **Foreign parent is separate from owner type.** "Foreign-owned" is not a type: an investor-owned DNO can have a Spanish, US or Hong Kong parent. Shown as a **two-letter ISO country chip** next to the node (`ES`, `US`, `HK`). Plain text, not flag emoji, which render inconsistently and are not accessible. The chip is shown only when the parent's country ≠ the column's country.
- **Owner vs operator.** In this lens each asset node shows two lines:

```
┌ L ─────────────────────────────┐
│ SP Manweb plc        operator  │   ← licensee: the company holding the Ofgem licence
│ ▸ Iberdrola S.A.  ES   owner   │   ← ultimate parent (with share if not 100%)
└────────────────────────────────┘
```

- **Nodes that own no grid assets are dimmed** and get the label **"owns no assets"**. This is the main lesson for GB: **NESO operates the system but owns no wires.** The US ISOs show the same thing, and a side-by-side view makes it obvious.
- **Edges in this lens** are drawn in neutral grey at 40% opacity. They keep their dash pattern, so the structure stays readable without competing with the fills.
- **Group summary strip** under the column, only in the Ownership lens and only for GB distribution (it answers "who owns the wires" for the whole country, not just the selected area):

```
Distribution: 14 licence areas · 6 DNO groups · fewer ultimate owners
 UKPN (3) P HK   NGED (4) L GB   NPg (2) P US   ENWL (1) L ES   SPEN (2) L ES   SSEN (2) L GB
 ↑ selected area's group is outlined          [verify all owners and counts; ENWL→Iberdrola 2024]
```

  Each group is a chip; tapping one selects its first area. This answers "who owns GB's wires" without a map, and it shows the operator-vs-owner point: 6 operating groups but fewer ultimate parents.

### Wireframe, GB column, Ownership lens

```
GB · England · London (UKPN) · Domestic                              Lens: Ownership
POLICY &      [G DESNZ]  [G Ofgem]  [  Parliament ]  [G HM Treasury]        (dimmed: owns no assets)
REGULATION
SYSTEM &      [G NESO  owns no assets]  [G? Elexon]  [P/L EPEX·N2EX]  [G LCCC·ESC]
MARKET OPS
WHOLESALE &   [X generators]  [X storage]  ┌ L NGET ───────────────┐  [X interconnectors]
TRANSMISSION                               │ ▸ National Grid plc   │
                                           └───────────────────────┘
DISTRIBUTION  ┌ P UKPN (London Power Networks) ┐   [X supplier: your choice]
& RETAIL      │ ▸ CK group consortium  HK      │
              └────────────────────────────────┘
CONSUMERS     [ Domestic ]
──────────────────────────────────────────────────────────────────────────
Owner type: G public  M municipal  C co-op  L listed investor  P private investor  X mixed
Chip "HK" = ultimate parent based outside GB.   "owns no assets" = operates or regulates only.
```

---

## 4. "Who sets the price" when setters cap, approve, levy or tax

### Decision D8: price-setting mode on `sets_rate` edges

US `sets_rate` edges are almost all "sets". GB needs more kinds. These are encoded with **line terminator and dash**; the colour stays the `sets_rate` colour:

| `rate_mode` | Meaning | Line | Terminator | Panel word | GB example |
|---|---|---|---|---|---|
| `sets` | Fixes the price | solid | filled arrow ▶ | **sets** | NESO sets BSUoS tariff `[verify]`; supplier sets a fixed tariff |
| `caps` | Sets a ceiling; someone else sets the actual price | solid | flat bar ⊤ ("lid") | **caps at** | Ofgem → default tariff |
| `approves_revenue` | Sets allowed revenue or methodology; another party calculates tariffs | long dash | hollow arrow ▷ | **approves revenue** | Ofgem RIIO-ED2 → UKPN; Ofgem RIIO-T → NGET |
| `levies` | Government scheme adds a charge, collected through suppliers | dotted | diamond ◆ | **levies** | DESNZ policy → LCCC CfD levy; ESC Capacity Market levy |
| `taxes` | Tax set by statute | dotted | diamond with bar ◆̄ | **taxes** | HM Treasury / Parliament → VAT (5% domestic) |
| `market` | No setter; price comes from a market | none | ≈ glyph on the component | **market-set** | GB wholesale energy (exchanges plus bilateral) |

- **Pass-through (D9)** is a node property along the path (`collects_only: true` for that component). The node gets a **hollow ring** and the panel says "*collected by* British Gas, *set by* UKPN". A supplier passing through DUoS sets nothing, so drawing a "sets" edge from it would be wrong.
- **Two-step setting** (approves_revenue, then sets) is drawn as a two-hop path: Ofgem ▷ UKPN ▶ tariff. This is the key way GB differs from a US PUC rate case, where the commission sets the tariff directly.

### Bill panel ("Who sets each part of my bill?"; replaces "Who sets my rate?")

The Bill lens shows this panel and highlights the paths of the selected component in the diagram. Segments are **equal width in v1** (no £ figures; see deferrals).

```
Who sets each part of my bill?   GB · London · Default tariff · Domestic
┌──────────────────────────────── Ofgem price cap ⊤ (limits total unit rate + standing charge) ───────────────────────────────┐
│ Wholesale ≈ │ Transmission │ Distribution │ Balancing │ Policy levies ◆ │ Capacity ◆ │ Supplier costs & margin │ VAT ◆̄ │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
 ▸ Distribution (DUoS)
     Ofgem  ──▷ approves revenue (RIIO-ED2) ──▶  UKPN  ──▶ sets tariff (CDCM methodology)  ──○ British Gas collects ──▶ you
 ▸ Policy levies
     DESNZ (policy) ··◆ LCCC levies CfD cost on suppliers  ──○ supplier collects ──▶ you      [also RO, FiT, ECO, WHD]
 ▸ Wholesale
     ≈ market-set (exchanges + bilateral)  → supplier buys/hedges  → ⊤ Ofgem cap limits pass-through
 Legend: ▶ sets   ⊤ caps   ▷ approves revenue   ◆ levies   ◆̄ taxes   ≈ market   ○ collects only
```

- **The cap is a bracket over the whole bar (D10).** Putting ⊤ on a single component would suggest that Ofgem caps the wholesale price, which it does not. The cap's component allowances are explained in the bracket tooltip.
- **Fixed tariff archetype:** the cap bracket is absent. That is a removed node or edge, so it follows the layout rule.
- **Component names** are country-labelled in data and mapped to a neutral key (section 8): GB shows "Transmission (TNUoS)", "Balancing (BSUoS)" and so on; PJM shows "Transmission", "Ancillary / uplift".
- In **US columns**, the panel looks almost the same as today, since almost every mode is `sets`. PJM capacity becomes `market` (RPM auction) with an ISO node; GB capacity becomes `levies`. **Side by side, this is the clearest teaching moment in the tool.**

---

## 5. Terminology across countries

### Decision D11

- **Data:** a `terms` list per country: `{term, expansion, definition, role, equivalents: [{country, term, caveat}]}`. The `role` key is the same one used for node matching (D2), so the tooltips, the ≈ marker and the Crosswalk all come from one source.
- **Tooltip pattern** (tap or focus to pin; hover alone is not enough on touch screens):

```
┌ Supplier (GB) ───────────────────────────────────────────┐
│ Company that sells electricity to you, buys it wholesale │
│ and bills network and policy charges.                    │
│ ≈ US: REP (ERCOT), competitive supplier / LSE (PJM)      │
│ ≠ Unlike a US "default service" provider, every GB       │
│   customer is with a supplier; there is no utility       │
│   fallback, only a supplier-of-last-resort process.      │
│ Source ↗                                                 │
└──────────────────────────────────────────────────────────┘
```

- **First use in a column** gets a dotted underline (keeps the existing CLAUDE.md rule).
- **Crosswalk drawer.** One table, generated from the roles of the columns on screen. Rows are roles; columns are the columns on screen:

```
Crosswalk                       PJM (US)                 GB
System operator               ≈ PJM (also runs markets)  NESO (balancing + planning; no energy market)
Wholesale market venue          PJM                      EPEX SPOT / N2EX + bilateral
Imbalance settlement            PJM                      Elexon (BSC)
Transmission owner              TOs (e.g. PECO)          NGET / SPT / SHET (+ OFTOs)
Distribution operator           EDC ("wires utility")    DNO (licence area); IDNO
Retail seller                   EGS / competitive supp.  Supplier
Default supply                  Default service (PUC)    Default tariff (price-capped) — any supplier
Energy regulator                FERC + PA PUC (split)    Ofgem (both roles)
Policy                          State legislature        DESNZ
Capacity mechanism              RPM (ISO auction, FERC)  Capacity Market (gov. scheme; NESO runs auctions, ESC settles)
```

- **False friends to seed** (each gets a `≠` caveat):
  - "transmission": in Scotland 132 kV is transmission, in England & Wales it is distribution `[verify]`, while the US threshold differs by utility and FERC test;
  - "capacity market": an ISO auction under FERC versus a government scheme paid for by a levy;
  - "system operator" versus "ISO": NESO runs no energy market;
  - "default service" versus "default tariff";
  - "independent": IDNO means not an incumbent DNO, unlike the "independent" in ISO;
  - "supplier", "utility" (rarely used in GB), "standing charge" versus "customer charge";
  - "regulator": Ofgem covers both FERC-like and PUC-like roles.
- **Rejected:** a free-standing glossary page. It drifts away from the data and is not context-specific.
- **Rejected:** auto-translating labels into the other country's terms. That hides the local names users need to recognise on their bills.

---

## 6. Accessibility, mobile, dark mode, palettes, single file

### Colour: one colour meaning per lens (D6)

| Lens | Coloured by | Neutral |
|---|---|---|
| Roles | edges by type (6 colours + 6 dash patterns) | nodes (surface colour) |
| Bill | selected component's path highlighted (`sets_rate` colour); others dimmed | nodes |
| Ownership | node fills by owner type (6 tints + letter glyph) | edges (grey, dash kept) |

**Edge palette (Okabe-Ito, colour-blind safe), each paired with a dash pattern:**

| Edge type | Light | Dark | Dash |
|---|---|---|---|
| regulates | #0072B2 blue | #56B4E9 | solid |
| pays | #009E73 green | #2BC79A | `6 3` |
| sets_rate | #D55E00 vermillion | #F07A2A | solid, 2.5 px (heaviest) |
| dispatches | #E69F00 orange | #F2B740 | `2 3` |
| plans_procures | #CC79A7 purple | #E09AC3 | `10 4 2 4` |
| delivers | #5F6B76 slate | #A3AEB8 | `1 4` |

`rate_mode` terminators (▶ ⊤ ▷ ◆) are added to sets_rate edges, so mode never relies on colour.

**Ownership tints:** low-saturation tints of the same Okabe-Ito hues: G blue, M purple, C green, L orange, P vermillion, X neutral grey with a 45° hatch. Node text stays at ≥ 4.5:1 contrast because fills are tints, not full-strength colours. In dark mode, fills are darkened tints with light text. The letter glyph carries the meaning for colour-blind users and in greyscale print.

All colours are CSS custom properties on `:root`, redefined under `@media (prefers-color-scheme: dark)` and `[data-theme]`. A palette check (ΔE between adjacent categories, ≥ 3:1 contrast against both backgrounds) belongs in `validate/` as a pytest that reads the CSS variables, so a bad colour change fails a test.

### Keyboard and screen reader

- Nodes are `<g tabindex="0" role="button" aria-label="UKPN, distribution operator, Distribution & Retail lane, owned by CK group consortium, Hong Kong">`. Arrow keys move within a lane, PageUp/PageDown between lanes, Enter pins the tooltip.
- **List view (D12)** is a text version of the current state:

```
GB · England · London · Default tariff · Domestic
POLICY & REGULATION
  • Ofgem (energy regulator, public body) — regulates: NESO, NGET, UKPN, supplier; caps: default tariff; approves revenue: NGET, UKPN
  …
WHO SETS EACH PART OF MY BILL
  • Distribution: Ofgem approves revenue → UKPN sets tariff → supplier collects
```

  The same view serves screen readers, printing and copying text into notes.
- `prefers-reduced-motion`: lens changes cross-fade off and snap instantly.
- Focus rings use `currentColor` plus a 2 px offset and stay visible in both themes.

### Mobile (< 640 px)

```
┌───────────────────────────┐
│ [PJM ▸] [GB ▸] [+]        │  ← column tabs (compare collapses to one visible column)
│ Lens: Roles|Bill|Owner    │
│ ▾ GB · England · London…  │  ← chain collapses into one summary row; tap to expand
├───────────────────────────┤
│ POLICY & REGULATION       │
│ [DESNZ][Ofgem★]           │  ← nodes wrap inside lane; lanes stay top-to-bottom
│ [Parliament][HMT★]        │
│ SYSTEM & MARKET OPS       │
│ [NESO≈][Elexon★]…         │
│ …                         │
├───────────────────────────┤
│ Differences vs PJM (4) ▾  │  ← text diff list replaces side-by-side scanning
│  ★ LCCC/ESC  ★ Elexon     │
│  ≈ NESO: no energy market │
└───────────────────────────┘
```

- No horizontal scrolling. Edges between wrapped nodes are drawn as orthogonal connectors, or, when lanes are too crowded, edges are hidden in Roles and shown on node tap.
- The "Differences vs X" list stands in for side-by-side comparison on phones.
- The bill bar becomes a vertical list of components, with the cap bracket drawn as a left-hand rail.

### Single file

All of the above is CSS variables, inline SVG `<marker>` definitions for the terminators, and a small amount of JS. There are no fonts, icons, maps or libraries to load. Country data is still in the generated `data.json`. For `file://`, keep the existing loading approach. If `fetch` of local JSON is blocked in some browsers, build.py should inline `data.json` into a `<script type="application/json">` block; that is worth checking now if it hasn't been done.

---

## 7. Recommended minimal v1 of the country feature

**In v1 (estimate: ~14 to 18 h on top of US v1):**

1. Schema additions from section 8, approved before work starts (~1 h discussion).
2. Country picker as the first link in each column's chain; locked Market chip; data-driven level labels; NI coverage note (~2 h).
3. Lane display renames and per-column subtitles (~1 h).
4. `role` on every node; ★ / ≈ markers matched on role; cross-country banner (~2 h).
5. GB data: base plus 3 archetypes (`domestic_default_capped`, `domestic_fixed`, `non_domestic_contract`) and all 14 distribution areas as labels mapped to the 3 TOs. All `needs_verification` until sourced (~5 to 6 h of research).
6. `rate_mode` encodings, the pass-through ring, the bill panel with the cap bracket, equal-width segments (~3 h).
7. Ownership lens: fill + glyph + parent-country chip, "owns no assets" dimming, GB DNO group strip (~2 h).
8. Tooltips with ≈ / ≠ lines; Crosswalk drawer (~2 h).
9. List view, keyboard focus, URL hash state (~2 h).

**New claim tests to add with GB** (following the existing pattern):
- GB `base` has no node with role `wholesale_market_venue` run by the system operator (NESO runs no energy market);
- the NESO node has `owns_assets: false`;
- `domestic_default_capped` has exactly one `caps` edge, from Ofgem, targeting the bill total;
- `domestic_fixed` has no `caps` edge;
- every DUoS path has `approves_revenue` (Ofgem), then `sets` (DNO), then collect-only (supplier);
- each of the 14 areas maps to exactly one TO and one DNO group;
- every owner record has `source.url`.

**Deferred (each with its reason):**

| Deferred | Why |
|---|---|
| DE, AU-NEM, IE-SEM | Test the design on paper now (section 9); build after GB is verified |
| Tile cartogram of GB licence areas in the Ownership lens | Nice, but the dropdowns and the group strip already answer the question |
| Proportional bill bar with £/kWh from the Ofgem cap breakdown | Needs quarterly data with sources and a time dimension (cap changes quarterly) |
| Ownership share chains (e.g. 75/25 splits through holding companies) | High research cost; v1 shows the ultimate parent and a share only if one is stated |
| IDNOs, prepayment, Economy 7 / ToU archetypes | Probably label variants, not shape changes; check before adding |
| OFTOs as individual nodes | Kept as one aggregate node with owner type `X` |
| Time slider (pre/post NESO 2024, pre/post ENWL sale) | Valuable for learning, but needs `valid_from`/`valid_to` on every record |

---

## 8. Schema implications (additive; needs sign-off)

| Change | Field | Notes |
|---|---|---|
| New top level | `country: {code, name, levels[], lane_subtitles, terms[], coverage_notes[]}` | Region files gain a `country` reference; US files get `country: US` |
| Node | `role` (controlled list) | Needed for cross-country matching |
| Node | `owner: {type: G/M/C/L/P/X, licensee, parent, parent_country, share?, source}` | Operator vs owner |
| Node | `owns_assets: bool` | NESO, ISOs, regulators = false |
| Node | `kind` values: rename `iso` to `system_operator` (alias `iso` kept); add `levy_counterparty`, `settlement_body`, `exchange`, `interconnector`, `ministry` | |
| Node | `jurisdiction`: generalise to `national` / `subnational` / `local` / `private` (map federal→national, state→subnational) | "federal" means nothing in GB |
| Edge | `rate_mode` on `sets_rate` (`sets`/`caps`/`approves_revenue`/`levies`/`taxes`/`market`); default `sets` | Existing US data stays valid |
| Edge | `target: bill_total` allowed for `caps` | Cap bracket |
| Path node | `collects_only` per component | Pass-through |
| Component | Neutral keys `energy`, `transmission`, `distribution`, `balancing`, `capacity`, `policy_levies`, `supplier_costs`, `tax`, `exit_fee`, with country display labels; map existing US keys (`generation`→`energy`, `ancillary_uplift`→`balancing`, `riders_public_purpose`→`policy_levies`) | One schema migration, done once in build.py |

---

## 9. Stress test against later countries (on paper)

| Country | What tests the design | Holds? |
|---|---|---|
| Germany | ~800+ DSOs (the Level 2 dropdown becomes a type-to-search box); 4 TSOs by control area with mixed public and foreign ownership; Stadtwerke (M); Grundversorger default supplier; levies and grid fees via BNetzA | Yes. Needs a searchable combobox in the same slot |
| AU-NEM | AEMO is both market operator and planner (closer to an ISO); rule maker AEMC separate from regulator AER (two lane-1 nodes with `regulates` vs a new `makes_rules` label); DMO/VDO is a cap, the same `caps` mode | Yes. Market = NEM, Level 1 = NEM region |
| IE-SEM | One market across two jurisdictions; two TSOs (EirGrid, SONI) and two regulators (CRU, UR) acting jointly as the SEM Committee | Yes. Level 1 = jurisdiction, and the SEM Committee is a lane-1 node with two `part_of` members. This is also where the NI note from GB connects |

None of these needs a different layout, which is the test the lane rule must pass.
