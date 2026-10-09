# Line review: source-backed verification (2026-10-08)

Rule (CLAUDE.md, Christian 2026-10-08): a line is `verified`, and drawn solid, only when two independent Claude power markets reviewers each confirm it against a primary source. These sources count as primary: a statute, a regulation, a tariff, a regulatory order, or an official publication of the ISO, regulator or body. A line stays `needs_verification`, and drawn dashed, when any of these is true:

- its source is secondary;
- a reviewer rejects it;
- a reviewer is unsure about it.

Per-line verdicts and reasons are in `line-review.json`; `test_verified_lines_cite_a_primary_source` checks them against the data.

## Result

| Market | Verified (solid) | Needs verification (dashed) |
|---|---|---|
| ERCOT | 33 | 86 |
| PJM | 171 | 76 |
| CAISO | 44 | 89 |
| GB (thin slice) | 16 | 6 |
| **Total** | **264** | **257** |

One line was removed: `pjm/coop/ferc_coop_tx`. FERC does not regulate REC's rates (FPA 201(f)). ODEC pays PJM for transmission, and FERC's oversight of that is already drawn as `ferc_ws`.

How the reviewers checked: they read some sources directly. These were Va. Code 56-585.3, the NJ BGS order, ERCOT Retail 101, the PEC rate policy, 16 TAC 25.43, SB 6, PURA ch. 33, the CPUC pages, NESO's TNUoS and BSUoS pages, and gov.uk VAT. Other sources were blocked from the cloud, including PA statutes, leginfo and NERC; for those the reviewers worked from their knowledge of the document, and their reasons say so.

## Why lines stay dashed

The relationship is almost always right. What fails is that the cited document does not support the specific claim. Rejects (wrong source): `ferc_nerc_rel` (3, ERCOT), `puct_tdsp_tx` and `puct_coop_tx` (a 1999 proposed rule), and `gb neso_bm` (cites the TNUoS page).

The source changes below would make the most dashed lines eligible for a second review:

| Lines | Current source | Better primary source |
|---|---|---|
| 36 | ERCOT Retail 101 | ERCOT Nodal Protocols §6 and §9; PURA 39.101; 16 TAC 25.475 |
| 34 | CPUC page on publicly owned utilities | City charter or rate ordinance (Anaheim, Riverside, SMUD, LADWP) |
| 21 | CPS Energy press release (secondary) | PURA 40.055; San Antonio rate ordinance |
| 20 | PEC rate policy | PEC tariff (power cost recovery factor, delivery, transmission) |
| 18 | CPUC general rate case page | ERRA decision (generation); PU Code 381 and 399.8 (public purpose) |
| 17 | Va. Code 56-585.3 | REC tariff (wholesale power cost adjustment, transmission) |
| 14 | PJM OATT (retail billing hops) | EDC and supplier retail tariffs; ComEd Transmission Services Charge |
| 16 | CAISO Transmission Control Agreement (retail billing) | IOU and city utility rate schedules; CAISO tariff for the transmission revenue requirement |
| 8 | NERC key players (page now empty) | NERC compliance registry; FPA 215; 18 CFR Part 39 |
| 8 | 220 ILCS 5/16-108 (riders) | 220 ILCS 5/8-103B; ComEd rider tariffs |
| 6 | PAIEUG answer (intervenor filing) | PECO tariff; PA PUC default service order |

## Modelling points raised (not yet changed)

- **ERCOT NOIE transmission:** resolved 2026-10-09 (Christian): the council sets the retail transmission charge and the PUCT regulates only the wholesale rate. `puct_noie_tx` is now `regulates` and was reset to `needs_verification`. ERCOT co-ops still show the PUCT as setter (`puct_coop_tx`); not decided.
- **PJM vertically integrated ancillary costs:** retail recovery goes through a commission-approved clause (WV fuel clause, VA rider), so the commission belongs on the path.
- **PJM competitive supply transmission:** PJM, not the EDC, bills network transmission to the supplier. In OH, NJ and MD a non-bypassable EDC charge is used instead.
- **ERCOT admin fee:** the ancillary hop with `mode: market` also carries the PUCT-approved admin fee item.
- **CAISO city utility balancing:** `balancing_redispatch` is a GB mechanism term.
