// Build data/maps/<cc>.json: projected, simplified SVG paths for the locator map in the detail panel.
// Only needed when shapes change; the output is committed.
//   cd scripts/maps && npm ci && node make_maps.mjs
// Census and Natural Earth shapes come from npm (us-atlas, world-atlas). Files that need a manual
// download go in scripts/maps/raw/ (git-ignored); a layer whose file is missing is skipped with a warning.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import mapshaper from 'mapshaper';

const require = createRequire(import.meta.url);
const HERE = path.dirname(new URL(import.meta.url).pathname);
const OUT = path.resolve(HERE, '../../data/maps');
const WIDTH = 300;
const ACCESSED = '2026-10-07';

const CENSUS = {
  source: { title: 'US Census Bureau cartographic boundary files, 2017 (via us-atlas 3.0.1)', url: 'https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html', accessed: ACCESSED },
  credit: 'US Census Bureau', licence: 'Public domain (US government work)',
};
const NATURAL_EARTH = {
  source: { title: 'Natural Earth 1:50m admin 0 countries (via world-atlas 2.0.2)', url: 'https://www.naturalearthdata.com/downloads/50m-cultural-vectors/', accessed: ACCESSED },
  credit: 'Natural Earth', licence: 'Public domain',
};

const NATURAL_EARTH_10 = { ...NATURAL_EARTH, source: { ...NATURAL_EARTH.source, title: 'Natural Earth 1:10m admin 0 countries (via world-atlas 2.0.2)', url: 'https://www.naturalearthdata.com/downloads/10m-cultural-vectors/' } };

const POSTAL = { '01': 'AL', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA',
  '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI',
  '27': 'MN', '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC',
  '38': 'ND', '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT',
  '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI', '56': 'WY' };   // contiguous US + DC; AK, HI and territories left out

// TopoJSON object -> same object keeping only features with an area id, under properties.aid
function pick(topo, object, aidOf) {
  const t = structuredClone(topo);
  t.objects = { [object]: t.objects[object] };
  t.objects[object].geometries = t.objects[object].geometries
    .map(g => ({ ...g, properties: { aid: aidOf(g) } })).filter(g => g.properties.aid);
  return t;
}

const COUNTRIES = {
  US: {
    proj: '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +datum=NAD83',
    frame: 'states',
    simplify: '6%',
    layers: [
      { id: 'context', ...NATURAL_EARTH, clip: true,
        topo: pick(require('world-atlas/countries-50m.json'), 'countries', g => ({ 124: 'canada', 484: 'mexico' })[g.id]) },
      { id: 'states', ...CENSUS, topo: pick(require('us-atlas/states-10m.json'), 'states', g => POSTAL[g.id] && POSTAL[g.id].toLowerCase()) },
    ],
    groups: { lower48: Object.values(POSTAL).map(s => s.toLowerCase()) },
  },
  GB: {
    proj: '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy',   // British National Grid
    frame: 'uk',
    simplify: '3%',
    layers: [
      { id: 'context', ...NATURAL_EARTH_10, clip: true,
        topo: pick(require('world-atlas/countries-10m.json'), 'countries', g => ({ 372: 'ireland', 250: 'france' })[g.id]) },
      { id: 'uk', ...NATURAL_EARTH_10, topo: pick(require('world-atlas/countries-10m.json'), 'countries', g => ({ 826: 'uk' })[g.id]) },
    ],
    groups: {},
  },
};

async function build(cc, spec) {
  const inputs = {}, names = [];
  for (const l of spec.layers) {
    const name = `${l.id}.json`;
    const obj = Object.keys(l.topo.objects)[0];
    l.topo.objects = { [l.id]: l.topo.objects[obj] };      // layer name = layer id
    inputs[name] = l.topo; names.push(name);
  }
  const clip = spec.layers.filter(l => l.clip).map(l => l.id).join(',');
  const cmd = [
    `-i ${names.join(' ')} combine-files`,
    `-proj ${spec.proj} target=*`,
    `-simplify ${spec.simplify} keep-shapes target=*`,
    `-rectangle source=${spec.frame} offset=4% name=frame +`,
    clip && `-clip frame target=${clip} remove-slivers`,
    `-o format=svg width=${WIDTH} margin=0 id-field=aid precision=0.1 target=* map.svg`,
  ].filter(Boolean).join(' ');
  const svg = (await mapshaper.applyCommands(cmd, inputs))['map.svg'].toString();
  const viewBox = svg.match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
  const layers = spec.layers.map(l => {
    const g = svg.match(new RegExp(`<g id="${l.id}"[^>]*>([\\s\\S]*?)</g>`));
    const areas = {};
    for (const m of (g ? g[1] : '').matchAll(/<path d="([^"]+)"[^>]*id="([^"]+)"/g))
      areas[m[2]] = (areas[m[2]] ? areas[m[2]] + ' ' : '') + m[1].replace(/ (?=[A-Z])/g, '');
    return { id: l.id, credit: l.credit, source: l.source, licence: l.licence, areas };
  });
  const out = { country: cc, viewBox, projection: spec.proj, layers, groups: spec.groups };
  fs.writeFileSync(path.join(OUT, `${cc.toLowerCase()}.json`), JSON.stringify(out) + '\n');
  console.log(`${cc}: ${layers.map(l => `${l.id} ${Object.keys(l.areas).length}`).join(', ')}; ${(JSON.stringify(out).length / 1024).toFixed(1)} KB`);
}

fs.mkdirSync(OUT, { recursive: true });
for (const [cc, spec] of Object.entries(COUNTRIES)) await build(cc, spec);
