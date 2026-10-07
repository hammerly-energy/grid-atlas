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

function input(key) {
  const s = SOURCES[key];
  const file = s.npm ? require.resolve(s.npm) : path.join(HERE, 'raw', s.file);
  if (!fs.existsSync(file)) throw new Error(`${key}: ${file} missing; download it from ${s.url}`);
  const buf = fs.readFileSync(file);
  const sha = crypto.createHash('sha256').update(buf).digest('hex');
  if (sha !== s.sha256) throw new Error(`${key}: sha256 ${sha} does not match sources.json; check the file, then update the manifest`);
  return JSON.parse(buf);
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
    simplify: '6%',
    layers: () => [
      { id: 'context', src: 'natural_earth_50m',
        topo: pick(input('natural_earth_50m'), 'countries', g => ({ 124: 'canada', 484: 'mexico' })[g.id]) },
      { id: 'states', src: 'census_states',
        topo: pick(input('census_states'), 'states', g => POSTAL[g.id] && POSTAL[g.id].toLowerCase()) },
    ],
    groups: { lower48: Object.values(POSTAL).map(s => s.toLowerCase()) },
  },
  europe: {
    countries: { GB: 'uk' },
    proj: '+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80',   // ETRS89-LAEA (EPSG:3035)
    bbox: '-25,34,45,72',                         // lon/lat cut before projecting (drops overseas territories)
    simplify: '3%',
    layers: () => [
      { id: 'context', src: 'natural_earth_10m', topo: pick(input('natural_earth_10m'), 'countries', g => EUROPE[g.id]) },
      { id: 'uk', src: 'natural_earth_10m', topo: pick(input('natural_earth_10m'), 'countries', g => ({ 826: 'uk' })[g.id]) },
    ],
    groups: {},
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
  const layers = spec.layers(), inputs = {};
  for (const l of layers) {
    const obj = Object.keys(l.topo.objects)[0];
    l.topo.objects = { [l.id]: l.topo.objects[obj] };      // layer name = layer id
    inputs[`${l.id}.json`] = l.topo;
  }
  const ids = layers.map(l => l.id).join(',');
  const cmd = [
    `-i ${Object.keys(inputs).join(' ')} combine-files`,
    spec.bbox && `-clip bbox=${spec.bbox} target=${ids}`,
    `-proj ${spec.proj} target=${ids}`,
    `-simplify ${spec.simplify} keep-shapes target=${ids}`,
    spec.frame && `-rectangle source=${spec.frame.source} offset=${spec.frame.offset} name=frame +`,
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
    out.layers.push({ id: l.id, credit: s.credit, licence: s.licence, source: { title: s.title, url: s.url, accessed: s.accessed }, areas });
  }
  fs.writeFileSync(path.join(OUT, `${id}.json`), JSON.stringify(out) + '\n');
  console.log(`${id}: ${out.layers.map(l => `${l.id} ${Object.keys(l.areas).length}`).join(', ')}; ${(JSON.stringify(out).length / 1024).toFixed(1)} KB`);
}

fs.mkdirSync(OUT, { recursive: true });
for (const [id, spec] of Object.entries(MAPS)) await build(id, spec);
