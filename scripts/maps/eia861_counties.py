"""List the RTOs, and selected wires utilities, serving each contiguous-US county from EIA-861, for the locator map.

EIA-861 lists each utility's counties (Service_Territory) and, per state, its customers and balancing authority
(Sales_Ult_Cust, Delivery_Companies; the "Operating in these RTOs" flags in Utility_Data also count market
participation such as the western EIM, so they are not used). Each utility's
customers are spread evenly over its counties in that state; a county is in an RTO's footprint when that RTO's
utilities hold at least MIN_SHARE of its estimated customers. County-level approximation: a border county can be in
two footprints, and a small utility at the edge of a county doesn't pull the county in.

Wires utilities in UTILITY_AREAS get the same estimate: a county is in a utility's territory when the utility holds at
least UTILITY_MIN of its estimated customers, so a county it serves only in part still counts, but a stray listing
(PG&E in San Diego County) does not. The even spread can't tell which utility serves most of a shared county.

    python3 -I scripts/maps/eia861_counties.py scripts/maps/raw/f8612025
    # -> scripts/maps/derived/county_rto.csv, scripts/maps/derived/county_utility.csv
"""
import collections, csv, json, re, sys, unicodedata
from pathlib import Path
import openpyxl

HERE = Path(__file__).resolve().parent
MIN_SHARE = 0.3   # an RTO's utilities must hold at least this share of a county's estimated customers
RTO_BA = {'CISO': 'caiso', 'ERCO': 'ercot', 'PJM': 'pjm', 'MISO': 'miso', 'SWPP': 'spp', 'NYIS': 'nyiso', 'ISNE': 'isone'}   # EIA BA code -> area id
UTILITY_AREAS = {14328: 'pge', 17609: 'sce', 16609: 'sdge'}   # EIA utility number -> area id (PG&E, SCE, SDG&E)
UTILITY_MIN = 0.1
FIPS_STATE = {'01': 'AL', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA',
    '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI',
    '27': 'MN', '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC',
    '38': 'ND', '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT',
    '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI', '56': 'WY'}


def norm(name):
    s = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(saint)\b', 'st', s).replace('.', '').replace("'", '')
    s = re.sub(r'\b(county|parish|borough|city and borough|census area|municipality)\b', '', s)
    return re.sub(r'[^a-z]', '', s)


def main(raw):
    raw = Path(raw)
    topo = json.loads((HERE / 'node_modules/us-atlas/counties-10m.json').read_text())
    fips = {}                                    # (state, normalised name) -> 5-digit FIPS
    for g in topo['objects']['counties']['geometries']:
        st = FIPS_STATE.get(g['id'][:2])
        if st:
            n = norm(g['properties']['name'])
            if st in ('VA', 'MD', 'MO', 'NV') and int(g['id'][2:]) >= 510:    # independent cities share names with counties
                fips[(st, n + 'city')] = g['id']; fips.setdefault((st, n), g['id'])
            else:
                fips[(st, n)] = g['id']

    cust = collections.defaultdict(collections.Counter)    # (utility, state) -> BA code -> customers
    for f, sheet in (('Sales_Ult_Cust_2025.xlsx', 'States'), ('Delivery_Companies_2025.xlsx', 'Delivery Companies')):
        for r in openpyxl.load_workbook(raw / f, read_only=True)[sheet].iter_rows(min_row=4, values_only=True):
            if r[4] in ('Bundled', 'Delivery') and isinstance(r[23], (int, float)):
                cust[(r[1], r[6])][r[8]] += r[23]

    served = collections.defaultdict(list)        # (utility, state) -> FIPS list
    missing = set()
    for r in openpyxl.load_workbook(raw / 'Service_Territory_2025.xlsx', read_only=True)['Counties_States'].iter_rows(min_row=2, values_only=True):
        f = fips.get((r[4], norm(r[5])))
        if f: served[(r[1], r[4])].append(f)
        elif r[4] in FIPS_STATE.values(): missing.add((r[4], r[5]))

    total = collections.Counter()                 # FIPS -> estimated customers
    by_rto = collections.defaultdict(collections.Counter)    # FIPS -> RTO -> estimated customers
    by_util = collections.defaultdict(collections.Counter)   # FIPS -> utility area id -> estimated customers
    for key, fl in served.items():
        for code, c in cust.get(key, {}).items():
            per = c / len(fl)                     # customers spread evenly over the utility's counties in that state
            for f in fl:
                total[f] += per
                if code in RTO_BA: by_rto[f][RTO_BA[code]] += per
                if key[0] in UTILITY_AREAS: by_util[f][UTILITY_AREAS[key[0]]] += per
    out = HERE / 'derived/county_rto.csv'
    weight = {}
    with out.open('w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['fips', 'rto', 'share'])
        for f in sorted(by_rto):
            for rto, c in sorted(by_rto[f].items()):
                if total[f] and c / total[f] >= MIN_SHARE:
                    w.writerow([f, rto, round(c / total[f], 2)]); weight[f] = True
    with (HERE / 'derived/county_utility.csv').open('w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['fips', 'utility', 'share'])
        for f in sorted(by_util):
            for u, c in sorted(by_util[f].items()):
                share = c / total[f]
                if share >= UTILITY_MIN:
                    w.writerow([f, u, round(share, 2)])
    print(f'{len(weight)} counties in an RTO; {len(missing)} county names unmatched: {sorted(missing)[:15]}')


if __name__ == '__main__':
    main(sys.argv[1])
