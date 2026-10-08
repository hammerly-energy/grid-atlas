"""Pull selected utility territories out of the HIFLD Electric Retail Service Territories archive.

HIFLD Open was taken offline on 2025-08-25; the archived copy (GeoParquet, lon/lat) is on Source Cooperative.
Writes one GeoJSON feature per utility in UTILITIES, lightly simplified so the derived file stays small;
make_maps.mjs simplifies again for drawing.

    python3 -I scripts/maps/hifld_utilities.py scripts/maps/raw/hifld-retail-service-territories.parquet
    # -> scripts/maps/derived/hifld_utilities.geojson
"""
import json, sys
from pathlib import Path
import pyarrow.parquet as pq
import shapely

HERE = Path(__file__).resolve().parent
UTILITIES = {   # EIA utility number (HIFLD ID) -> area id
    '44372': 'oncor', '8901': 'centerpoint', '16604': 'cps',              # ERCOT
    '4110': 'comed', '19876': 'dominion_va', '15477': 'pseg', '14940': 'peco',   # PJM
}
TOLERANCE = 0.002    # degrees, about 200 m; far below a pixel on the state-framed map


def main(src):
    rows = pq.read_table(src, columns=['ID', 'NAME', 'STATE', 'TYPE', 'geometry']).to_pylist()
    features = []
    for r in rows:
        if r['ID'] in UTILITIES:
            g = shapely.simplify(shapely.from_wkb(r['geometry']), TOLERANCE, preserve_topology=True)
            features.append({'type': 'Feature', 'properties': {'aid': UTILITIES[r['ID']], 'eia_id': r['ID'], 'name': r['NAME'], 'type': r['TYPE']},
                             'geometry': json.loads(shapely.to_geojson(shapely.set_precision(g, 1e-5)))})
    missing = set(UTILITIES.values()) - {f['properties']['aid'] for f in features}
    assert not missing, f'not in the HIFLD file: {missing}'
    out = HERE / 'derived/hifld_utilities.geojson'
    out.write_text(json.dumps({'type': 'FeatureCollection', 'features': sorted(features, key=lambda f: f['properties']['aid'])}, separators=(',', ':')) + '\n')
    print(f'{len(features)} utilities -> {out.relative_to(HERE)} ({out.stat().st_size / 1024:.0f} KB)')


if __name__ == '__main__':
    main(sys.argv[1])
