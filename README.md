# grid-atlas

Who regulates what, who sets each part of the bill, and who owns which part of the grid, compared side by side across electricity markets: ERCOT, PJM and CAISO first, then Great Britain.

```
python3 -m pip install -r requirements.txt
python3 scripts/build.py      # YAML -> web/data.json + web/data.js
python3 -m pytest -q -rx      # schema, integrity and market claims
open web/index.html           # works from file://
```

Data: `data/countries/<cc>/_country.yaml` (vocabulary, glossary) and `<market>.yaml` (nodes, edges, archetypes, utilities), validated by `data/schema.json`.
Design and sources: `docs/countries-proposal.md`, `docs/research/`.

Status: milestone 1 (scaffold on schema v2). Market data is entered from milestone 2.
