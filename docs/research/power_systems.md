# grid-atlas: power systems review (GB + US operational and regulatory checks)

Reviewer role: power systems engineer. Date: 2026-10-07.
Scope: the operating and engineering details where a simple who-does-what diagram would be wrong. Institution lists and bill line items are covered by the separate policy review.
Read against: `CLAUDE.md` (v1 five-lane model) and the draft `reviews/schema_v2.json` (which adds the `owns`, `operates` and `settles` edges, `rate_mode`, `holds_assets` and `owner`).

Verdict key: **CORRECT** / **CORRECT WITH CAVEAT** / **WRONG** / **MISLEADING AS DRAWN**.

---

## 1. Dispatch model

**Verdict: MISLEADING AS DRAWN if GB reuses the US `dispatches` edge without qualification.**

**US (ERCOT, PJM, CAISO).** The ISO runs security-constrained economic dispatch (SCED) over offers about every 5 minutes, plus a day-ahead security-constrained unit commitment (SCUC). Prices are locational marginal prices (LMPs). ERCOT has been nodal since 2010. PJM and CAISO are also nodal. A resource can self-schedule, but the ISO dispatch is the default and it covers the whole fleet.
Caveat that matters for the consumer lane: **generators are paid nodal prices, but load usually pays an aggregated price**. ERCOT load pays a Load Zone price, PJM load pays a zonal/aggregate LMP, and CAISO load pays a Default Load Aggregation Point (DLAP) price. "Consumers pay LMP" is therefore wrong as a literal statement.

**GB.** GB uses self-dispatch with central balancing.
- Generators, suppliers and traders trade bilaterally and on exchanges (EPEX, N2EX) up to gate closure, which is 1 hour before each 30-minute settlement period.
- Each BM Unit submits a Final Physical Notification (FPN): its own planned output.
- NESO does not clear an energy market and does not set a wholesale price.
- After gate closure, NESO changes BM Unit output from FPN by accepting bids and offers (Bid-Offer Acceptances, BOAs, under Grid Code BC2). NESO also uses non-BM ancillary contracts, such as reserve, response, stability and constraint-management pathfinders.
- There is no locational energy price. GB has one wholesale bidding zone, and since BSC P305 (Nov 2015) a single national imbalance price (System Price).
- **Not every generator is in the BM.** Mandatory participation applies to licensed "large" power stations. The thresholds differ by transmission area: 100 MW in England & Wales, 30 MW in the SPT area and 10 MW in the SHET area. Most embedded generation, and much battery capacity below those thresholds, is not dispatched by NESO at all unless it opts in.

**REMA status (as of Oct 2026).**
- The July 2025 REMA Summer Update rejected zonal pricing and chose "Reformed National Pricing" (RNP).
- DESNZ published the RNP Delivery Plan on 21 Apr 2026. Consultation closed 2 Jun 2026.
- Likely to proceed: a lower mandatory BM participation threshold, and FPNs required to match traded positions.
- Decisions on unit-based bidding and on shortening the settlement period are deferred to late 2026.
- Siting signals are to come mainly from connection-capacity thresholds tied to the Strategic Spatial Energy Plan, plus a possible TNUoS reform. A decision on which siting option is due in 2026.
- A long-term constraint-management market for flexible demand is planned.
- The model should **not** assert anything about unit-bidding, TNUoS redesign or settlement-period length yet.

**How to draw it.**
- US: `ISO -dispatches-> generator/storage`, with `mechanism: central_sced`.
- GB:
  - (a) `generator -dispatches-> (self)` is meaningless. Instead show a `self_schedules` / `notifies` relationship (BM Unit → NESO: FPN), or put `dispatch_model: self_dispatch` on the market node.
  - (b) `NESO -dispatches-> BM Unit` with `mechanism: balancing_redispatch` (BOA).
  - (c) `NESO -plans_procures-> ancillary/flex providers` with `mechanism: ancillary_contract`.
  - The UI label should read "redispatches (BM bids/offers)", not "dispatches".
- Do not draw `NESO -dispatches-> embedded generation`.
- Do not draw a `sets_rate generation` edge from NESO. The generation price is set by suppliers' bilateral and exchange buying. The only administered energy price is the imbalance price, calculated by Elexon under the BSC.

Sources:
- Grid Code (BC1/BC2, PN/BOA): https://www.neso.energy/industry-information/codes/grid-code
- REMA Summer Update 2025: https://www.nortonrosefulbright.com/es-es/knowledge/publications/4399413b/rema-summer-update-no-to-zonal-pricing-yes-to-reformed-national-pricing
- RNP Delivery Plan (Apr 2026): https://energygovuk.citizenspace.com/energy-bills/reformed-national-pricing-delivery-plan/
- RNP summary: https://www.freeths.co.uk/insights-events/legal-articles/2026/reformed-national-pricing-plan-five-key-takeaways/
- ERCOT nodal market: https://www.ercot.com/services/programs/load
- CAISO DLAP: https://www.caiso.com/market-operations

---

## 2. System operator / balancing authority vs who owns the wires

**Verdict: CORRECT premise. The schema must keep "operates", "owns" and "regulates" as three separate relations, because in all four regions the operator owns no wires.**

| Region | System operator / BA / RC | Owns transmission | Owns distribution | Notes |
|---|---|---|---|---|
| GB | **NESO**, publicly owned since 1 Oct 2024. It is the GB system operator for the whole of GB, including Scotland. It owns **no** network assets. | **NGET** (England & Wales), **SPT** (south Scotland), **SHET** (north Scotland), **OFTOs** (offshore transmission links, tendered by Ofgem), plus future CATOs | 14 DNO licence areas in 6 groups (UKPN, NGED, SSEN, SPEN, ENWL, NPg), plus IDNOs | **Voltage boundary:** in England & Wales, transmission is 400/275 kV and 132 kV is *distribution*. In Scotland, 132 kV is *transmission*. "Transmission = ≥132 kV" is therefore wrong for E&W. |
| PJM | PJM is the BA, the Reliability Coordinator and the Transmission Provider under its OATT | TOs (PECO, PSE&G, BGE, AEP, Dominion, …) under the Consolidated TO Agreement. They transfer *functional control* to PJM but keep ownership. | EDCs / utilities (state PUC) | PJM also runs RTEP planning |
| CAISO | CAISO is the BA (CISO) and RC West (it is also RC for many non-CAISO BAs) | Participating TOs (PTOs): PG&E, SCE, SDG&E, and munis such as Anaheim, Riverside, Pasadena, Vernon, Azusa, Banning and Colton | IOUs and munis | Operational control is transferred under the TCA |
| ERCOT | ERCOT ISO is the BA and RC for the ERCOT Interconnection | TSPs: Oncor, CenterPoint, AEP Texas, TNMP, LCRA TSC, munis (Austin Energy, CPS), co-ops | TDSPs (competitive areas), munis, co-ops | Transmission rates (TCOS) are set by **PUCT**, not FERC |

**DSO transition in GB.** DNOs own and operate their networks. Under RIIO-ED2 (2023–28) each DNO has a functionally separated DSO function that runs flexibility markets, with an Ofgem DSO incentive (2025–26 report published Sept 2026).
- Ofgem appointed Elexon as the **Market Facilitator** for local flexibility (July 2024), and also as the Flexibility Market Asset Registration delivery body (Mar 2025).
- NESO is the Regional Energy Strategic Planner (RESP).
- DSOs are **not** separate legal entities. Model DSO as a role (an `operates` edge) of the DNO node, not as a new institution.

**Recommendation.**
- **owns**: `owner -owns-> asset`, with `asset` = transmission | distribution | generation | storage | interconnector | metering. This is physical assets. Equity ownership of the *entity* (for example, CKI owns UKPN) is a separate `owner` attribute, as the v2 draft does.
- **operates**: `operator -operates-> asset`, with an extra field `control: real_time_system_operation | functional_control | asset_operation`. NESO, PJM, CAISO and ERCOT have `real_time_system_operation` over transmission they do not own. A DNO/TO has `asset_operation` (switching, maintenance) over its own network.
- **regulates**: add `domain` (see section 6) so licensing/economic regulation is not confused with operation.
- Test idea: in every region the BA/SO node has `holds_assets: []` and at least one `operates transmission` edge.

Sources:
- NESO designation: https://www.gov.uk/government/publications/designation-of-the-national-energy-system-operator-neso
- OFTO tenders: https://www.ofgem.gov.uk/offshore-electricity-transmission-ofto/ofto-tender-rounds/ofto-tender-round-3
- DSO incentive report 2025-26: https://www.ofgem.gov.uk/transparency-document/distribution-system-operation-incentive-annual-report-2025-2026
- Elexon Market Facilitator: https://www.elexon.co.uk/2024/07/29/elexon-appointed-as-the-market-facilitator-for-local-flexibility/
- Elexon asset registration body: https://www.elexon.co.uk/2025/03/07/elexon-appointed-as-flexibility-market-asset-registration-delivery-body/
- PJM TOs: https://www.pjm.com/about-pjm/member-services/member-list
- CAISO PTOs: https://www.caiso.com/library/transmission-control-agreement

---

## 3. Imbalance settlement: Elexon vs NESO

**Verdict: Elexon needs its own node. Without it the diagram is WRONG about who pays generators for balancing and who charges suppliers for imbalance.**

**GB.**
- Elexon is BSCCo. It administers the Balancing and Settlement Code (BSC) and runs settlement.
- Each BSC Party (suppliers, generators, traders, interconnector users) has Production and Consumption energy accounts. Contract volumes are notified to the ECVAA.
- After metering, Elexon calculates each party's imbalance (metered volume minus contracted volume) and charges or pays it at the **single System Price** (P305, since Nov 2015).
- **The cash for BM Bid-Offer Acceptances also flows through BSC Trading Charges settled by Elexon.** NESO is a BSC party and funds those payments.
- NESO recovers BM costs plus its own ancillary-service contract costs through **BSUoS** (see section 4).
- Ancillary services outside the BM (response, reserve, stability, DFS, constraint contracts) are contracted and paid directly by NESO.
- **Suppliers are the exposed party.** They are BRP-equivalents, and their imbalance exposure is effectively a cost of their retail margin.
- Settlement is being changed by Market-wide Half-Hourly Settlement (MHHS): meter migration began 22 Oct 2025, about 80% by Oct 2026, completion 7 May 2027, and a new 4-month settlement timetable from 2 Jul 2027.
- Ownership: Elexon left NGESO ownership on 1 Oct 2024. It is now held under a "federated model" by 13 large BSC parties, pending code reform, under which Ofgem will license code managers. Elexon also has a subsidiary, EMR Settlement Ltd, that provides services for CfD and Capacity Market settlement.

**US.** The ISO is market operator *and* settlement agent. Settlement is two-part (day-ahead plus real-time deviations at real-time LMP). LSEs/QSEs are the financially exposed parties: in ERCOT, Qualified Scheduling Entities settle with ERCOT. There is no separate US settlement body.

**Edges to draw (GB).**
- `elexon -settles-> supplier` (imbalance and trading charges)
- `elexon -settles-> generator` (BOA payments, imbalance)
- `neso -pays-> elexon` (BM cashflow funding, `label: "funds BM acceptances"`)
- `supplier -pays-> neso`, `rate_component: balancing` (BSUoS)
- Ofgem `regulates` Elexon is **indirect**: Ofgem approves BSC modifications. Use `regulates` with `domain: market_rules`.

Sources:
- BSC / imbalance pricing: https://www.elexon.co.uk/bsc/
- MHHS: https://www.elexon.co.uk/bsc/operational/market-wide-half-hourly-settlement/
- Elexon ownership: https://www.elexon.co.uk/2024/10/01/elexon-ownership-change-on-1-october-2024/
- ERCOT QSE settlement: https://www.ercot.com/services/rq/re/qse

---

## 4. Transmission charging

**Verdict: the brief's BSUoS claim is CORRECT. "TNUoS is locational" is CORRECT WITH CAVEAT: only part of it is.**

**BSUoS.**
- Since **1 Apr 2023**, BSUoS is charged **only to final demand**, under CMP308. Generators, embedded generators, storage export and interconnectors pay none.
- It is an **ex-ante fixed tariff** (CMP361/362), set for six-month periods with notice. Tariff 6 ran Oct 2025–Mar 2026. Tariffs 7 and 8 cover Apr 2026–Mar 2027.
- It is calculated by NESO, not set by Ofgem rate case. Ofgem approves the CUSC methodology.

**TNUoS (CUSC Section 14).**
- **Revenue** is set by Ofgem's price control for each TO (RIIO-T3, from 1 Apr 2026).
- **Tariffs** are calculated by NESO with the DCLF transport model.
- NESO **collects TNUoS from users and passes it to the TOs**. Draw the money path as `supplier -pays-> NESO -pays-> TO`, not `supplier -pays-> TO`.
- **Generation:** 27 locational zones. Wider tariffs vary by technology through annual load factors. The generation *residual* has been ~£0 since Apr 2021 (TCR), with an adjustment to keep average generator charges within the €0–2.50/MWh cap.
- **Demand:** 14 zones.
  - The *locational* part is charged to HH demand on Triad demand (£/kW) and to NHH demand at p/kWh for 4–7 pm.
  - The *residual*, which is most of the revenue, has been a **£/site/day banded charge** since Apr 2022 (TCR). Bands are set by capacity or consumption for non-domestic users and a single band for domestic.
  - Result: most of a household's TNUoS is **not locational**.
- **Embedded generation.** Generators under 100 MW connected to distribution (licence-exempt) get the **Embedded Export Tariff**, paid on Triad export (£/kW), instead of paying generation TNUoS. Embedded generators of 100 MW or more pay generation TNUoS.
- Note for the RNP section: the Delivery Plan lists TNUoS reform as one of the siting levers. Mark the TNUoS structure `as_of` the 2026/27 tariff year.

**US comparison.**
- PJM: each TO has a FERC formula rate (OATT Attachment H-xx). Load pays **Network Integration Transmission Service** per zone, allocated on the zone's 1CP network service peak load, plus RTEP project charges (Schedule 12).
- In restructured PJM states the transmission line on a retail bill is a FERC-set charge that the EDC or supplier *passes through*. The state PUC only sets the retail rate design. So the correct mode is `FERC -sets_rate(transmission, mode: approves)-> TO`, then `EDC -sets_rate(mode: passes_through)-> consumer`.
- CAISO: High-Voltage TAC (CAISO-wide postage stamp) plus Low-Voltage TAC per PTO. TRRs are filed at FERC (non-jurisdictional munis also file TRRs with FERC for TAC inclusion).
- ERCOT: PUCT approves each TSP's TCOS. Costs are allocated to DSPs on **4CP** (June–Sept peaks). This is the closest US analogue to GB Triads, and it is a useful "same idea, different region" callout.

Sources:
- BSUoS: https://neso.energy/charging/balancing-services-use-system-bsuos-charges
- Ofgem CMP361 decision: https://www.ofgem.gov.uk/sites/default/files/2022-12/CMP361%20Accept.pdf
- TNUoS guide: https://www.neso.energy/tnuos-10-minutes-0
- PJM OATT: https://www.pjm.com/directory/merged-tariffs/oatt.pdf
- ERCOT 4CP / TCOS (PUCT Subst. R. 25.192): https://www.puc.texas.gov/agency/rulesnlaws/subrules/electric/25.192/25.192.pdf

---

## 5. Capacity

**Verdict: all four regimes CORRECT as described, with the details below.**

| Region | Mechanism | Who runs it | Who pays | Safe test assertion |
|---|---|---|---|---|
| GB | Capacity Market: **T-4** and **T-1** auctions, central, pay-as-clear | DESNZ (regulations), **NESO as EMR Delivery Body** (prequalification and auctions), Ofgem (CM Rules), **Electricity Settlements Company (ESC)** as Settlement Body, with EMR Settlement Ltd as service provider | **Suppliers** via the ESC supplier charge, based on demand 4–7 pm on winter working days | GB base has a `capacity_auction` market node; ESC `settles` capacity providers; supplier `pays` ESC with `rate_component: capacity` |
| PJM | RPM Base Residual Auction, central, sloped VRR demand curve; FRR alternative | PJM (FERC tariff) | LSEs pay Locational Reliability Charge, passed through to retail | PJM base has a capacity-market node; an FRR alternative exists |
| CAISO | **Bilateral RA obligation**. CPUC sets RA for CPUC-jurisdictional LSEs (IOUs, CCAs, ESPs), using Slice-of-Day since 2025. Munis' local regulatory authorities set their own. CAISO has only a backstop (CPM/RMR) and RA must-offer rules. | CPUC / LRAs; CAISO backstop | LSEs (procure bilaterally) | CAISO base has **no central capacity auction**; a `plans_procures` RA edge goes CPUC → LSE |
| ERCOT | Energy-only. Scarcity is priced through ORDC adders and ancillary services (incl. ECRS since 2023). PUCT dropped the Performance Credit Mechanism. | — | — | ERCOT base has no capacity-market node (keep the existing test) |

GB facts (2026):
- CM regulations were amended with effect from 17 Jul 2026: higher termination fees and credit cover.
- The next auctions are T-1 for 2027/28 (5.0 GW target) and T-4 for 2030/31 (40.9 GW target).

PJM facts:
- The 2028/29 BRA (Jul 2026) cleared at the **$325/MW-day cap**. This is the third auction under the governor-negotiated price collar.
- It is the **first auction in which the whole RTO fell short** of its reliability requirement, by 6,831 MW.
- FRR entities supplied 10,864 MW.
- PJM is seeking FERC approval of a "Backstop Procurement".
- Assert the existence of the node; do not assert prices.

Sources:
- GB CM reset 2026: https://cms.law/en/gbr/legal-updates/capacity-market-reset-raising-the-stakes-on-delivery
- NESO EMR Delivery Body: https://www.neso.energy/what-we-do/energy-markets/electricity-market-reform-emr-delivery-body/delivery-body-updates-events
- EMR Settlement: https://www.emrsettlement.co.uk/
- PJM 2028/29 BRA: https://www.pjm.com/-/media/DotCom/about-pjm/newsroom/2026-releases/20260714-pjm-capacity-auction-procures-138318-mw-of-generation-resources.pdf
- CPUC RA: https://www.cpuc.ca.gov/industries-and-topics/electrical-energy/electric-power-procurement/resource-adequacy-homepage

---

## 6. Reliability standards: who holds the reliability "regulates" edge

**Verdict: the v1 single `regulates` edge type is too coarse. It cannot show both "ERCOT is not FERC-regulated for rates" and "ERCOT is subject to FERC-approved NERC standards".**

**US.**
- Under FPA §215, FERC certifies NERC as the Electric Reliability Organization and approves its standards. These standards are mandatory for all users, owners and operators of the bulk power system **including ERCOT**; Alaska and Hawaii are excluded.
- NERC delegates to six Regional Entities: MRO, NPCC, RF, SERC, **Texas RE** and **WECC**. PJM sits mainly in RF, with part in SERC. CAISO is in WECC. ERCOT is in Texas RE.
- **Resource adequacy is not a NERC/FERC function.** It belongs to states and RTO rules: PJM RAA, CPUC RA, and PUCT's ERCOT reliability standard adopted in 2024.
- PUCT also oversees ERCOT directly. After SB 2 (2021), ERCOT's board is chosen by a selection committee, and PUCT approves ERCOT's budget and protocol changes. Texas RE also acts as PUCT's reliability monitor.
- Correct edges:
  - `FERC -regulates(domain: reliability)-> NERC`
  - `NERC -regulates(reliability)-> Texas RE`
  - `Texas RE -regulates(reliability)-> ERCOT`
  - `PUCT -regulates(market_rules, rates, governance)-> ERCOT`

**GB.**
- There is **no NERC equivalent**.
- Reliability standards are written into licences and industry codes:
  - The **NETS SQSS** is a licence obligation on NESO and the TOs.
  - The **Grid Code** is maintained by NESO, with modifications approved by Ofgem.
  - Distribution Code and Engineering Recommendations (e.g. P2 for distribution security, G99 for connection).
- Enforcement is by **Ofgem** through licence conditions.
- **DESNZ** sets the security-of-supply reliability standard (3 h LOLE, used for Capacity Market sizing) and the Electricity System Restoration Standard.
- ESQCR 2002 safety and continuity is enforced by HSE / DESNZ.
- Edges: `Ofgem -regulates(reliability/licensing)-> NESO`, `-> TOs`, `-> DNOs`. `DESNZ -regulates(policy_standard)-> NESO` (for the LOLE standard). Do not draw a NERC-style node.

Sources:
- NERC Regional Entities: https://www.nerc.com/AboutNERC/keyplayers/Pages/default.aspx
- Texas RE: https://www.texasre.org/
- FERC reliability (FPA 215): https://www.ferc.gov/industries-data/electric/industry-activities/reliability-primer
- SQSS: https://www.neso.energy/industry-information/codes/security-and-quality-supply-standard-sqss
- Grid Code: https://www.neso.energy/industry-information/codes/grid-code

---

## 7. Interconnectors and cross-border seams

**Verdict: GB needs an interconnector node kind (the v2 draft has one). A US "seams/external market" node is worth adding for CAISO and ERCOT.**

**GB.**
- About 10 GW of HVDC interconnectors link GB to FR, BE, NL, NO, DK, IE and NI.
- Regulation:
  - Most are under Ofgem's **cap-and-floor** regime (e.g. NSL, Viking, IFA2, Nemo).
  - Some are merchant or exempt (BritNed, ElecLink).
  - Ofgem approved a further window of five projects in Jan 2025.
- Trading:
  - Since Brexit (1 Jan 2021) GB is out of EU market coupling, so capacity is sold through **explicit auctions** (JAO and others), and day-ahead flows can run against price differences.
  - The TCA's MRLVC has not been implemented.
  - The EU Council authorised talks on UK participation in the EU internal electricity market on 30 Mar 2026. Negotiations are ongoing, so do not assert re-coupling.
- Interconnector operators are separately licensed. They are BSC parties for flows, and pay no BSUoS since 2023.
- **Scope note:** Northern Ireland is in the all-island SEM, regulated by the Utility Regulator, with SONI as system operator and NIE Networks owning the wires. "UK" ≠ GB. The country code `GB` is correct, and NI must be excluded or shown as an interconnected external market.

**US.**
- ERCOT is synchronously isolated, with only DC ties (and a few block-load switching arrangements) to SPP and Mexico.
- That isolation is why ERCOT wholesale sales and transmission are outside FERC's FPA Part II rate jurisdiction. FERC has issued §210/211 interconnection orders for DC ties while disclaiming wider jurisdiction.
- CAISO runs **WEIM** (real-time, 22+ entities) and **EDAM**, live **1 May 2026** with PacifiCorp. Further EDAM joiners: PGE Oct 2026; LADWP, BANC (incl. SMUD), PNM and TID in 2027; IID in 2028.
- Governance: the Western Energy Markets Governing Body has had primary authority since Jul 2025. AB 825 allows a possible transfer to ROWE no earlier than Jan 2028.
- Recommendation: add a node kind `external_market`, or reuse `iso` with `role: market_extension` for WEIM/EDAM, so CAISO's `muni_own_grid` archetype can show LADWP/BANC as **separate BAs that still trade in CAISO-run markets**.

Sources:
- EDAM go-live: https://www.caiso.com/about/news/news-releases/edam-is-live-pacificorp-and-caiso-successfully-launch-new-market-may-1
- EU-UK talks (Mar 2026): https://www.enerdata.net/publications/daily-energy-news/eu-starts-talks-uk-participation-eu-power-market.html
- Ofgem interconnectors: https://www.ofgem.gov.uk/energy-policy-and-regulation/policy-and-regulatory-programmes/interconnectors
- FERC disclaimer on SPP-ERCOT ties: https://www.troutmanenergyreport.com/2009/11/ferc-disclaims-jurisdiction-over-transmission-lines-interconnecting-spp-to-ercot/

---

## 8. Distribution level

**Verdict: the US model is CORRECT (state PUC sets distribution rates). The GB model must show "Ofgem sets revenue, DNO calculates tariff", not "Ofgem sets DUoS".**

**GB.**
- Ofgem sets each DNO's allowed revenue under RIIO-ED2 (Apr 2023–Mar 2028; ED3 is in development).
- DNOs calculate DUoS with common methodologies under the **DCUSA**:
  - **CDCM** for LV/HV connections (most consumers).
  - **EDCM** for EHV connections (site-specific, with locational elements).
- Ofgem approves methodology changes.
- Since Apr 2022 the distribution *residual* is also a £/site/day banded charge (TCR).
- DUoS is billed **to suppliers**, who pass it to customers.
- **IDNOs** own and operate embedded networks (new-build estates) inside DNO areas. They are under a **relative price control**: IDNO charges are capped by reference to the host DNO's equivalent charges.
- Connection charges:
  - Since **Apr 2023** (Access SCR), demand customers no longer pay upstream reinforcement, and generators pay a reduced share. This is a "shallower" boundary.
  - Connection *works* can be contestable (ICPs).
  - The **connection queue** was reformed by NESO "Gate 2" (CMP434/435), with the reordered queue issued in 2025–26.
- Flexibility: DSOs buy local flexibility through tenders (e.g. via platforms). Elexon is the Market Facilitator that standardises products and registration.

**US.**
- Distribution rates for IOUs are set by the state PUC in rate cases: PUCT for TDSPs, CPUC, and PA PUC / NJ BPU / MD PSC etc.
- Munis and co-ops are mostly self-regulated. Two nuances:
  - **Texas munis.** PUCT has appellate jurisdiction over muni rates for customers *outside* city limits. PUCT also sets the muni's *transmission* (TCOS) rate, even though the city council sets the retail rate. The `muni_opted_out` archetype therefore still has a PUCT `sets_rate(transmission)` edge upstream.
  - **Texas co-ops.** PUCT has limited jurisdiction. Members can petition.
- US distribution flexibility markets are nascent: FERC Order 2222 DER aggregation is being implemented by RTOs, with state-run DER programs. Don't model them in v1.

Sources:
- DCUSA / CDCM / EDCM: https://www.dcusa.co.uk/
- Ofgem RIIO-ED2: https://www.ofgem.gov.uk/energy-policy-and-regulation/policy-and-regulatory-programmes/network-price-controls-2021-2028-riio-2/riio-ed2-price-control
- Access SCR decision: https://www.ofgem.gov.uk/decision/access-and-forward-looking-charges-significant-code-review-final-decision
- IDNO price control: https://www.ofgem.gov.uk/energy-policy-and-regulation/industry-licensing/licences-and-licence-conditions
- NESO connections reform: https://www.neso.energy/industry-information/connections/connections-reform
- PURA §33.051 / §40.051: https://statutes.capitol.texas.gov/Docs/UT/htm/UT.33.htm

---

## 9. Errors in the US scaffold (`CLAUDE.md`)

| # | Claim in CLAUDE.md | Verdict | Fix |
|---|---|---|---|
| a | "ERCOT wholesale is not FERC-rate-regulated (no `regulates` edge FERC → ERCOT market for wholesale rates)" | **CORRECT WITH CAVEAT** | The rate claim is right. But a test that forbids *any* FERC→…→ERCOT `regulates` path would be wrong: reliability flows FERC→NERC→Texas RE→ERCOT under FPA §215. Scope the test to `domain in {rates, market_rules}`. Also add PUCT→ERCOT (`market_rules`, `governance`), reflecting SB 2/SB 3 (2021). |
| b | "PJM base has a capacity auction node" | **CORRECT**, but model it as a *market run by PJM*, not an institution | Use kind `market` (or a `function`) with `PJM -operates-> rpm`. Note FRR as an alternative path. Don't assert a price. |
| c | `muni_own_grid` — "e.g. LADWP, SMUD: own balancing authority, outside CAISO's market" | **WRONG on two counts** | (1) SMUD is not itself a BA. **BANC** is the BA; SMUD is its largest member and its operator. LADWP *is* its own BA. IID and TID are other California BAs. (2) LADWP and BANC have been in CAISO's **WEIM** since 2021 and are scheduled for **EDAM in 2027**, so "outside CAISO's market" is false. Say "outside CAISO's BA; participates in CAISO-run WEIM". |
| d | `muni_in_caiso` — "municipal utility inside CAISO's balancing area" | **CORRECT WITH CAVEAT** | Some munis are **PTOs** (Anaheim, Riverside, Pasadena, Vernon, Azusa, Banning, Colton), so they own transmission under CAISO control and recover a TRR through TAC. Others (NCPA members, Silicon Valley Power) run as **Metered Subsystems (MSS)**. Retail rates are set by the city council, not CPUC. Draw an `owns transmission` edge only where the muni is a PTO. |
| e | PJM `vertically_integrated` — "e.g. WV, KY" | **CORRECT WITH CAVEAT** | Only part of KY is in PJM: Kentucky Power (AEP), Duke Energy Kentucky and EKPC. **LG&E/KU is not in PJM** (it is its own BA). Same issue for IL: only **ComEd** is in PJM, and Ameren Illinois is in MISO. The utility→region mapping needs a test. |
| f | PJM `hybrid` — "e.g. VA" | **CORRECT** | Dominion VA is regulated by the SCC with limited retail choice (≥5 MW customers, 100%-renewable products). Many rate elements are set by statute (VCEA), so the legislature has a real `sets_rate` role. |
| g | Lane text "MARKET OPERATOR … dispatches / settles" | **MISLEADING for GB** | GB splits the operator function: NESO (balancing), Elexon (settlement), exchanges (trading), NESO as EMR Delivery Body (capacity). See sections 1 and 3. |
| h | Lane "WHOLESALE … transmission owners" | **CORRECT WITH CAVEAT** | TOs are regulated monopolies whose revenue is set by FERC/PUCT/Ofgem, not wholesale market participants. Fine as a lane placement, but don't draw `pays` edges between TOs and generators for energy. |
| i | `jurisdiction` enum federal/state/local/private | **WRONG for GB** | NESO is publicly owned, Ofgem and DESNZ are national, and Scotland has devolved consenting (s36/s37 Electricity Act consents in Scotland are issued by Scottish Ministers). The v2 draft's `national/subnational` enum fixes this. |
| j | Coverage note "not all of Texas is in ERCOT" | **CORRECT** | El Paso Electric is in WECC. SPS (Xcel) is in SPP. Entergy Texas is in MISO. Lubbock P&L moved into ERCOT in 2021–23. |
| k | Implied "LMP is what load pays" (no explicit claim) | **Guard against it** | Load pays zonal/DLAP/Load Zone prices (section 1). |

Sources:
- BANC: https://www.smud.org/Corporate/About-us/News-and-Media/2021/2021/Four-more-Balancing-Authority-of-Northern-California-members-join-California-ISO
- IID: https://www.tdworld.com/utility-business/news/55294020/imperial-irrigation-district-to-join-both-western-energy-imbalance-market-and-extended-day-ahead-market
- EDAM: https://www.caiso.com/about/news/news-releases/edam-is-live-pacificorp-and-caiso-successfully-launch-new-market-may-1
- PJM zones: https://www.pjm.com/library/maps
- Texas RE: https://www.texasre.org/

---

## Modelling implications

### Node kinds
The v2 draft already has `system_operator`, `settlement_body`, `scheme_administrator`, `interconnector` and `holding_group`. Add or confirm these:
- `reliability_body`: NERC and the Regional Entities (MRO, NPCC, RF, SERC, Texas RE, WECC). Do not use `regulator`. In GB this kind is unused, and the test asserts that.
- `market`: a market or mechanism run by an operator, such as the PJM RPM, GB Capacity Market, GB Balancing Mechanism, WEIM/EDAM, or the GB day-ahead exchanges. This separates *who* from *which market*.
- `exchange`: EPEX/N2EX in GB. Optional; can be folded into `market`.
- `code_body`: optional, only if code administration is shown (CUSC/Grid Code panels, DCUSA). Otherwise leave it out. Do not invent nodes just to fill the picture.
- Use `system_operator` for NESO, and `iso` for an operator that also runs the energy market (ERCOT/PJM/CAISO). This keeps a visible difference: NESO runs no energy market.
- Node attributes:
  - `dispatch_model` on the operator: `central_sced` or `self_dispatch_with_balancing`.
  - `ba: true` on any BA.
  - `bidding_zone` / `pricing: nodal | national`.

### Edge types and qualifiers
v2 allows `mode` and `rate_component` only on `sets_rate`/`pays`. Extend it with these qualifiers:
- `regulates.domain` ∈ {`rates`, `market_rules`, `reliability`, `licensing`, `governance`, `policy_standard`}. Needed for the ERCOT test and for Ofgem's mix of roles.
- `dispatches.mechanism` ∈ {`central_sced`, `balancing_redispatch`, `ancillary_contract`}. The UI label comes from the mechanism.
- New edge `notifies`, or `self_schedules` (BM Unit → NESO: FPN). Optional but more honest.
- `operates.control` ∈ {`real_time_system_operation`, `functional_control`, `asset_operation`}.
- `owns` (physical asset). Keep it separate from `owner` (equity), as the draft does.
- `settles` (Elexon → BSC parties; ESC → capacity providers; ISO → QSE/LSE).
- `sets_rate.mode` (already in v2). Use `approves` for Ofgem revenue (RIIO) and FERC formula rates. Use `sets` for NESO/DNO tariff calculation under the approved methodology. Use `passes_through` for supplier/EDC.
- Optional `basis` on transmission/distribution `sets_rate`/`pays`: `triad`, `4cp`, `1cp_nspl`, `site_day_band`, `p_per_kwh`. This makes the GB-Triad / ERCOT-4CP / PJM-1CP comparison visible.

### Test assertions: GB
1. NESO node has `holds_assets` empty and has an `operates transmission` edge with `control: real_time_system_operation`.
2. No `dispatches` edge in GB has `mechanism: central_sced`. Every GB `dispatches` edge originates at NESO with `balancing_redispatch` or `ancillary_contract`.
3. There is no GB `sets_rate(generation)` edge from NESO or Ofgem with `mode: sets`. The generation price comes from the supplier (`supplier_margin`/`generation`). Ofgem `caps` applies only to domestic default tariffs.
4. BSUoS: exactly one `pays(balancing)` edge into NESO, from supplier/demand. No generator → NESO `pays(balancing)` edge (CMP308, from Apr 2023).
5. TNUoS money path: supplier → NESO → TO (NESO is collection agent). Ofgem → TO is `sets_rate(transmission, mode: approves)`.
6. Elexon node exists with `settles` edges to suppliers and generators, and an `Ofgem -regulates(market_rules)->` edge.
7. Capacity: `capacity_market` node exists. NESO `operates` it (delivery body). ESC `settles` providers. Supplier `pays(capacity)` to ESC.
8. Transmission owners: NGET, SPT and SHET each `owns transmission`. An OFTO slot exists. Encode the voltage-boundary note as data: SPT/SHET `owns` includes 132 kV, and E&W DNOs `owns distribution` includes 132 kV.
9. DNO `sets_rate(distribution, mode: sets)` and Ofgem `sets_rate(distribution, mode: approves)` both exist for every class.
10. No `reliability_body` node in GB. Reliability `regulates` edges originate from Ofgem or DESNZ.
11. No node with country NI or SEM inside the GB market file.
12. Do **not** assert: unit-based bidding, a TNUoS redesign, settlement-period length, EU re-coupling, or a CM clearing price. All are undecided or volatile as of Oct 2026.

### Test assertions: US
1. Replace "no FERC→ERCOT `regulates`" with: no `regulates` edge with `domain in {rates, market_rules}` from FERC to ERCOT or to any ERCOT TSP. AND there is a reliability path FERC→NERC→Texas RE→ERCOT.
2. PUCT `regulates(market_rules|governance)` ERCOT. PUCT `sets_rate(transmission, approves)` covers all ERCOT TSPs, including munis in `muni_opted_out`.
3. Every ISO node: `holds_assets` empty, `ba: true`, `dispatch_model: central_sced`.
4. PJM base: `market` node RPM operated by PJM. FRR alternative edge present (status may be `needs_verification`).
5. CAISO base: no central capacity auction node. A CPUC→LSE `plans_procures` RA edge exists. A CAISO backstop edge is optional.
6. ERCOT base: no capacity-market node (existing test retained).
7. CAISO `muni_own_grid`: the BA node is LADWP or **BANC** (never "SMUD" as a BA). It has a `participates_in` / `pays` edge to WEIM.
8. Utility→region mapping: LG&E/KU and Ameren Illinois must **not** map to PJM. El Paso Electric, SPS and Entergy Texas must **not** map to ERCOT.
9. FERC `sets_rate(transmission, mode: approves)` exists in PJM and CAISO. In restructured archetypes the EDC/IOU → consumer transmission edge is `mode: passes_through`.
10. Reliability: PJM→RF (and SERC), CAISO→WECC, ERCOT→Texas RE. Each region's RE is reachable from NERC.
