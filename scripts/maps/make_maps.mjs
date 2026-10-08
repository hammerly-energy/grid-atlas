// Build data/maps/<map>.json: projected, simplified SVG paths for the locator map in the detail panel.
// Only needed when shapes change; the output is committed.
//   cd scripts/maps && npm ci && node make_maps.mjs
//
// One map per region, not per country, so cross-border bodies (NERC, ENTSO-E, a TSO in two
// countries) draw on one frame. Each map lists the countries it serves and each country's home
// area; the page frames a body's map on its home area plus the body's own areas.
//
// Every input is listed in sources.json with its URL and sha256. A changed input fails the
// build instead of silently drawing different shapes. Inputs npm can't supply go in
// scripts/maps/raw/ (git-ignored).
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import mapshaper from 'mapshaper';

const require = createRequire(import.meta.url);
const HERE = path.dirname(new URL(import.meta.url).pathname);
const OUT = path.resolve(HERE, '../../data/maps');
const SOURCES = JSON.parse(fs.readFileSync(path.join(HERE, 'sources.json'), 'utf8'));
const WIDTH = 300;

function read(key) {
  const s = SOURCES[key];
  const file = s.npm ? require.resolve(s.npm) : path.join(HERE, s.file);
  if (!fs.existsSync(file)) throw new Error(`${key}: ${file} missing; download it from ${s.url}`);
  const buf = fs.readFileSync(file);
  const sha = crypto.createHash('sha256').update(buf).digest('hex');
  if (sha !== s.sha256) throw new Error(`${key}: sha256 ${sha} does not match sources.json; check the file, then update the manifest`);
  return buf;
}
const input = key => JSON.parse(read(key));

// ISO/RTO footprints: counties listed in derived/county_rto.csv (from EIA-861 by eia861_counties.py), one copy per RTO
function rtoCounties() {
  const rows = read('county_rto').toString().trim().split('\n').slice(1).map(l => l.split(','));
  const t = structuredClone(input('census_counties'));
  const geoms = t.objects.counties.geometries;
  t.objects = { counties: { type: 'GeometryCollection', geometries: rows.map(([fips, rto]) =>
    ({ ...geoms.find(g => g.id === fips), properties: { aid: rto } })).filter(g => g.type) } };
  return t;
}

// Wires utility territories: California Energy Commission service-area polygons, one per utility.
// IOU franchise territories are exclusive, so an overlap between two IOUs fails the build. Overlaps involving a
// publicly owned utility are printed: the CEC layer draws LADWP's Owens Valley area inside SCE's.
const CEC_IOU = new Set(['pge', 'sce', 'sdge']);
const CEC_UTILITY = { 'PG&E': 'pge', 'SCE': 'sce', 'SDG&E': 'sdge', 'SMUD': 'smud', 'LADWP': 'ladwp' };   // CEC Acronym -> area id
async function utilityAreas() {
  const d = input('cec_utilities');
  d.features = d.features.filter(f => CEC_UTILITY[f.properties.Acronym])
    .map(f => ({ ...f, properties: { aid: CEC_UTILITY[f.properties.Acronym] } }));
  const ids = Object.values(CEC_UTILITY);
  for (const [i, x] of ids.entries()) for (const y of ids.slice(i + 1)) {
    const only = id => ({ ...d, features: d.features.filter(f => f.properties.aid === id) });
    const out = await mapshaper.applyCommands(`-i x.json y.json combine-files -clip y target=x -proj ${MAPS.north_america.proj} target=x -each 'a=this.area' target=x -o format=json target=x out.json`,
      { 'x.json': only(x), 'y.json': only(y) });
    const km2 = JSON.parse(out['out.json']).reduce((s, r) => s + r.a, 0) / 1e6;
    if (km2 > 1 && CEC_IOU.has(x) && CEC_IOU.has(y)) throw new Error(`cec_utilities: ${x} and ${y} overlap by ${km2.toFixed(0)} km²`);
    if (km2 > 1) console.log(`  note: ${x} and ${y} overlap by ${km2.toFixed(0)} km² in the CEC layer`);
  }
  return d;
}

// GB: the 14 DNO licence areas (NESO, British National Grid) reprojected to lon/lat
async function dnoAreas() {
  const out = await mapshaper.applyCommands(
    `-i dno.geojson -proj init=EPSG:27700 wgs84 -each 'aid="dno_"+Name.replace("_","").toLowerCase()' -filter-fields aid -o format=geojson dno.json`,
    { 'dno.geojson': read('neso_dno').toString() });
  return JSON.parse(out['dno.json']);
}

// Northern Ireland: the UK outline minus the DNO areas (GB); only NI (about 14,000 km²) is over 1,000 km², the rest is coastline slivers
async function northernIreland(dno) {
  const uk = pick(input('natural_earth_10m'), 'countries', g => ({ 826: 'ni' })[g.id]);
  uk.objects = { uk: uk.objects.countries };
  const out = await mapshaper.applyCommands(
    `-i uk.json dno.json combine-files -erase dno target=uk -explode target=uk -each 'a=this.area' target=uk -filter 'a > 1e9' target=uk -filter-fields aid target=uk -o format=geojson target=uk ni.json`,
    { 'uk.json': uk, 'dno.json': dno });
  return JSON.parse(out['ni.json']);
}

// Merge each area's features into one shape, area by area. A single -dissolve drops a feature whose geometry another
// area already used (a border county in two ISOs), so each area is dissolved on its own and the results combined.
async function dissolveEach(topo) {
  const obj = Object.keys(topo.objects)[0];
  const aids = [...new Set(topo.objects[obj].geometries.map(g => g.properties.aid))];
  const features = [];
  for (const aid of aids) {
    const t = structuredClone(topo);
    t.objects[obj].geometries = t.objects[obj].geometries.filter(g => g.properties.aid === aid);
    const out = await mapshaper.applyCommands(`-i in.json -dissolve aid -o format=geojson out.json`, { 'in.json': t });
    features.push(...JSON.parse(out['out.json']).features);
  }
  return { type: 'FeatureCollection', features };
}

// TopoJSON object -> topology with only the features that get an area id (properties.aid)
function pick(topo, object, aidOf) {
  const t = structuredClone(topo);
  t.objects = { [object]: t.objects[object] };
  t.objects[object].geometries = t.objects[object].geometries
    .map(g => ({ ...g, properties: { aid: aidOf(g) } })).filter(g => g.properties.aid);
  return t;
}

const POSTAL = { '01': 'AL', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA',
  '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI',
  '27': 'MN', '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC',
  '38': 'ND', '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT',
  '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI', '56': 'WY' };   // contiguous US + DC; AK, HI and territories left out

// ISO 3166 numeric -> area id (alpha-2, lower case). The UK is its own layer.
const EUROPE = { '008': 'al', '040': 'at', '056': 'be', '070': 'ba', '100': 'bg', '112': 'by', '191': 'hr', '196': 'cy', '203': 'cz',
  '208': 'dk', '233': 'ee', '246': 'fi', '250': 'fr', '276': 'de', '300': 'gr', '348': 'hu', '352': 'is', '372': 'ie', '380': 'it',
  '428': 'lv', '440': 'lt', '442': 'lu', '470': 'mt', '498': 'md', '499': 'me', '528': 'nl', '578': 'no', '616': 'pl', '620': 'pt',
  '642': 'ro', '688': 'rs', '703': 'sk', '705': 'si', '724': 'es', '752': 'se', '756': 'ch', '804': 'ua', '807': 'mk' };

const MAPS = {
  north_america: {
    countries: { US: 'lower48' },                 // country -> home area or group
    proj: '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +datum=NAD83',
    frame: { source: 'states', offset: '4%' },    // context is cut to this frame
    interval: 8000,                               // metres; about half a pixel at 300 px wide
    layers: async () => [
      { id: 'context', src: 'natural_earth_50m',
        topo: pick(input('natural_earth_50m'), 'countries', g => ({ 124: 'canada', 484: 'mexico' })[g.id]) },
      { id: 'states', src: 'census_states',
        topo: pick(input('census_states'), 'states', g => POSTAL[g.id] && POSTAL[g.id].toLowerCase()) },
      { id: 'iso', src: 'eia861', overlay: true, approximate: 'county-level approximation from EIA-861', topo: await dissolveEach(rtoCounties()) },
      { id: 'utility', src: 'cec_utilities', overlay: true, topo: await utilityAreas(), interval: 3000 },   // drawn zoomed in on the state
    ],
    groups: { lower48: Object.values(POSTAL).map(s => s.toLowerCase()) },
  },
  europe: {
    countries: { GB: 'uk' },
    proj: '+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80',   // ETRS89-LAEA (EPSG:3035)
    bbox: '-25,34,45,72',                         // lon/lat cut before projecting (drops overseas territories)
    interval: 8000,
    layers: async () => {
      const dno = await dnoAreas();
      return [
        { id: 'context', src: 'natural_earth_10m', topo: pick(input('natural_earth_10m'), 'countries', g => EUROPE[g.id]) },
        { id: 'gb_dno', src: 'neso_dno', topo: dno, interval: 1500 },    // GB is drawn zoomed in
        { id: 'ni', src: 'natural_earth_10m', topo: await northernIreland(dno), interval: 1500 },
      ];
    },
    groups: (() => { const gb = 'abcdefghjklmnp'.split('').map(c => `dno_${c}`); return { gb, uk: [...gb, 'ni'] }; })(),
  },
};

// bounding box of an SVG path made only of absolute coordinate pairs (mapshaper's output)
function bbox(d) {
  const n = d.match(/-?[\d.]+/g).map(Number);
  const b = [Infinity, Infinity, -Infinity, -Infinity];
  for (let i = 0; i < n.length; i += 2) { b[0] = Math.min(b[0], n[i]); b[1] = Math.min(b[1], n[i + 1]); b[2] = Math.max(b[2], n[i]); b[3] = Math.max(b[3], n[i + 1]); }
  return b;
}

async function build(id, spec) {
  const layers = await spec.layers(), inputs = {};
  for (const l of layers) {
    if (l.topo.objects) {                                  // TopoJSON: layer name = layer id
      const obj = Object.keys(l.topo.objects)[0];
      l.topo.objects = { [l.id]: l.topo.objects[obj] };
    }
    inputs[`${l.id}.json`] = l.topo;                       // GeoJSON layers are named after the file
  }
  const ids = layers.map(l => l.id).join(',');
  const cmd = [                                            // one dataset per layer, so each simplifies on its own
    ...layers.map(l => `-i ${l.id}.json name=${l.id}`),
    ...(spec.bbox ? layers.map(l => `-clip bbox=${spec.bbox} target=${l.id}`) : []),
    ...layers.map(l => `-proj ${spec.proj} target=${l.id}`),
    ...layers.map(l => `-simplify dp interval=${l.interval || spec.interval} keep-shapes target=${l.id}`),
    spec.frame && `-rectangle source=${spec.frame.source} offset=${spec.frame.offset} name=frame`,
    spec.frame && `-clip frame target=context remove-slivers`,
    `-o format=svg width=${WIDTH} margin=0 id-field=aid precision=0.1 target=${ids} map.svg`,
  ].filter(Boolean).join(' ');
  const svg = (await mapshaper.applyCommands(cmd, inputs))['map.svg'].toString();
  const viewBox = svg.match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
  const out = { id, countries: spec.countries, viewBox, projection: spec.proj, layers: [], groups: spec.groups, bbox: {} };
  for (const l of layers) {
    const g = svg.match(new RegExp(`<g id="${l.id}"[^>]*>([\\s\\S]*?)</g>`));
    const areas = {};
    for (const m of (g ? g[1] : '').matchAll(/<path d="([^"]+)"[^>]*id="([^"]+)"/g))
      areas[m[2]] = (areas[m[2]] ? areas[m[2]] + ' ' : '') + m[1].replace(/ (?=[A-Z])/g, '');
    for (const [a, d] of Object.entries(areas)) out.bbox[a] = bbox(d);
    const s = SOURCES[l.src];
    out.layers.push({ id: l.id, credit: s.credit, licence: s.licence, source: { title: s.title, url: s.url, accessed: s.accessed },
      ...(l.overlay ? { overlay: true } : {}), ...(l.approximate ? { approximate: l.approximate } : {}), areas });
  }
  fs.writeFileSync(path.join(OUT, `${id}.json`), JSON.stringify(out) + '\n');
  console.log(`${id}: ${out.layers.map(l => `${l.id} ${Object.keys(l.areas).length}`).join(', ')}; ${(JSON.stringify(out).length / 1024).toFixed(1)} KB`);
}

fs.mkdirSync(OUT, { recursive: true });
for (const [id, spec] of Object.entries(MAPS)) await build(id, spec);
