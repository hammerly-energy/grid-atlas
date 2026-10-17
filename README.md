# grid-atlas

Live: https://hammerly-energy.github.io/grid-atlas/

An interactive diagram of the institutions in an electricity market: regulators, the grid operator, generators, utilities and customers. Markets can be shown side by side, including across countries.

Markets: ERCOT (most of Texas), PJM (all or part of 13 Mid-Atlantic and Midwest states and Washington, DC) and CAISO (most of California) in the US, and Great Britain (England, Scotland and Wales).

![Great Britain (UK Power Networks London) and PJM (PSE&G, New Jersey) side by side, showing who sets each part of a household bill](docs/img/gb-vs-pjm.png)

## Questions it answers

For a given market, utility and customer type:

1. Who sets each part of the bill (generation, transmission, distribution, capacity, grid services, other charges), and who approves or caps it?
2. Who regulates what?
3. Who owns the power plants, transmission lines and local wires, and who only operates them?

## Coverage

| Market | Customer setups | Utilities | Relationships | Confirmed against a primary source |
|---|---|---|---|---|
| ERCOT | 3 | 5 | 109 | 23 |
| PJM | 7 | 6 | 207 | 130 |
| CAISO | 5 | 7 | 120 | 31 |
| Great Britain | 4 | 14 | 69 | 54 |

A customer setup is a distinct arrangement within a market, for example a customer of a city-owned utility versus a customer who picks a retail supplier. For Great Britain, utilities are the 14 regional distribution network areas.

Each relationship cites a source. Solid lines have been checked against a primary source (statute, regulation, tariff, regulatory order or the body's own publication). Dashed lines have not.

## Tests

1,245 automated tests check the data format, references between records, specific market facts (for example, that ERCOT has no capacity market) and the rendered page.

## Run locally

```
python3 -m pip install -r requirements.txt
python3 scripts/build.py      # YAML -> web/data.json + web/data.js
python3 -m pytest -q -rx
open web/index.html
```

Data is in `data/countries/<country>/`, checked against `data/schema.json`. Research and sources are in `docs/research/`.

## Releases

Each merge to main is tagged (v1.0, v1.1, ...) and published as a GitHub release with a list of data and code changes. The live page shows the version in its footer.

## Next

- MISO, SPP, NYISO and ISO-NE.
