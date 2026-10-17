# grid-atlas

**Live: https://hammerly-energy.github.io/grid-atlas/**

An interactive map of who does what in US electricity markets. Pick a market and a utility, and grid-atlas draws the regulators, the grid operator, the generators, the utility and the customer in the same five rows. Two markets can be shown side by side, so the differences between them show up as boxes and lines that are missing, added or connected differently.

It covers three US grid operators: ERCOT (most of Texas), PJM (13 Mid-Atlantic and Midwest states plus Washington, DC) and CAISO (most of California). Great Britain is in progress.

![ERCOT (Oncor, Texas) and PJM (PSE&G, New Jersey) side by side, showing who sets each part of a household bill](docs/img/compare-bill.png)

## What it answers

For any market, utility and customer type (household, small business, large commercial and industrial, very large loads such as data centers):

1. **Who sets my rate, for each part of the bill?** Each part of the bill (generation, transmission, distribution, capacity, grid services and add-on charges) is traced to the body that sets it. Bodies that only approve, cap or collect a charge are shown separately.
2. **Who regulates what?** Market rules, grid reliability, licences and rates, from federal regulators (FERC, the Federal Energy Regulatory Commission, and NERC, the North American Electric Reliability Corporation) to the state utility commission or city council.
3. **Who owns which part of the grid?** Who owns the power plants, transmission lines and local wires, and their parent companies, kept separate from the bodies that only operate the grid.

## Coverage

| Market | Customer setups | Utilities | Relationships | Confirmed against a primary source |
|---|---|---|---|---|
| ERCOT | 3: competitive retail, city-owned utility, co-op | 5 | 125 | 35 |
| PJM | 7: utility default service, Illinois state-run purchasing, competitive supplier, city-arranged supply, utility owns generation and wires, limited choice, co-op | 6 | 266 | 176 |
| CAISO | 5: investor-owned utility, community choice (city or county buys the power), direct access (business buys from its own supplier), city-owned utility inside CAISO, city-owned utility running its own grid area | 7 | 138 | 44 |
| Great Britain | **In progress**: one setup (households on the capped default tariff) | 1 | 23 | 16 |

Every relationship cites a source, shown on hover and in its detail panel. A line is drawn solid only when two independent AI reviewers (Claude) each confirmed it against a primary source: a statute, regulation, tariff, regulatory order, or the body's own publication. The rest are drawn dashed and marked "needs verification".

## How it's checked

Market facts are written as automated tests, so a wrong fact fails the build instead of drawing a wrong diagram. 951 tests check the data format, that every reference resolves, specific market facts (for example, ERCOT has no capacity market, FERC has no say over ERCOT's market rules or rates, and CAISO has no central capacity auction), and the rendered page (every line can be clicked, and none runs through a box it doesn't connect). Three Great Britain facts are marked as expected to fail until that data is entered.

## Run it locally

```
python3 -m pip install -r requirements.txt
python3 scripts/build.py      # YAML -> web/data.json + web/data.js
python3 -m pytest -q -rx      # data format, references and market facts
open web/index.html           # works without a web server
```

Data: `data/countries/<cc>/_country.yaml` (terms and glossary) and `<market>.yaml` (boxes, lines, setups, utilities), checked against `data/schema.json`.
Design and sources: `docs/countries-proposal.md`, `docs/research/`.

## Next

- Great Britain: all four customer setups, the 14 regional distribution networks and their owners.
- The other four US grid operators: MISO, SPP, NYISO and ISO-NE.
