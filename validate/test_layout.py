"""Layout check: in every view, every relationship line can be clicked on its own,
no line runs through a box it doesn't connect, and each line meets its boxes square
(so the arrowhead lines up with the line).

Runs the real page in headless Chromium. Needs Playwright:
    python3 -m pip install playwright && python3 -m playwright install chromium
Skipped when Playwright isn't installed; CI always runs it.
"""
import os
from pathlib import Path
from urllib.parse import quote
import pytest
import build
from conftest import DATA

sync_api = pytest.importorskip("playwright.sync_api")
PAGE = (Path(__file__).resolve().parents[1] / "web/index.html").as_uri()
MIN_CLICKABLE = 3   # of 33 sample points along the middle of a line, this many must hit that line first


def views():
    for c in DATA.values():
        for mid, m in c["markets"].items():
            for arch in m["archetypes"]:
                yield f"lens=roles&a={mid}/{arch}&b=/"
                yield f"lens=owner&a={mid}/{arch}&b=/"
                for comp in build.bill_components(c["profile"], m):
                    yield f"lens=bill&comp={comp}&a={mid}/{arch}&b=/"


CHECK = """(minClickable) => {
  const svg = document.querySelector('#col0 svg');
  const boxes = [...svg.querySelectorAll('g.node')].map(g => ({ id: g.dataset.id, r: g.querySelector('rect').getBoundingClientRect() }));
  const problems = [];
  for (const hit of svg.querySelectorAll('path.edge-hit')) {
    const len = hit.getTotalLength(), ctm = hit.getScreenCTM();
    let clickable = 0; const through = new Set();
    for (let i = 1; i < 40; i++) {
      const q = hit.getPointAtLength(len * i / 40), p = new DOMPoint(q.x, q.y).matrixTransform(ctm);
      if (i >= 4 && i <= 36 && document.elementFromPoint(p.x, p.y) === hit) clickable++;
      for (const b of boxes)
        if (b.id !== hit.dataset.from && b.id !== hit.dataset.to
            && p.x > b.r.left + 2 && p.x < b.r.right - 2 && p.y > b.r.top + 2 && p.y < b.r.bottom - 2) through.add(b.id);
    }
    if (clickable < minClickable) problems.push(`${hit.dataset.edge}: hidden under other lines`);
    // the last stretch into the arrowhead (and the first out of the box) must be straight and square to the box
    for (const [a, b] of [[len - 1, len - 10], [1, 10]]) {
      const p = hit.getPointAtLength(a), q = hit.getPointAtLength(b);
      const vertical = Math.abs(p.x - q.x) < 0.5, horizontal = Math.abs(p.y - q.y) < 0.5;
      if (!vertical && !horizontal) problems.push(`${hit.dataset.edge}: line bends where it meets a box`);
    }
    for (const id of through) problems.push(`${hit.dataset.edge}: runs through ${id}`);
  }
  return problems;
}"""


@pytest.fixture(scope="module")
def page():
    with sync_api.sync_playwright() as p:
        exe = os.environ.get("CHROMIUM_PATH")
        browser = p.chromium.launch(**({"executable_path": exe} if exe else {}))
        pg = browser.new_page(viewport={"width": 1400, "height": 1600})
        yield pg
        browser.close()


@pytest.mark.parametrize("view", list(views()))
def test_every_line_is_clickable(page, view):
    page.goto(f"{PAGE}#{view}")
    page.reload()
    assert page.locator("#col0 svg").count() == 1, f"{view}: no diagram rendered"
    problems = page.evaluate(CHECK, MIN_CLICKABLE)
    assert not problems, f"{view}: " + "; ".join(problems)


TEXT_FITS = """() => {
  const out = [];
  for (const g of document.querySelectorAll('#col0 g.node')) {
    const r = g.querySelector('rect').getBBox();
    for (const t of g.querySelectorAll('text:not(.u):not(.asset-t)')) {
      const b = t.getBBox(), fs = parseFloat(getComputedStyle(t).fontSize);
      if (b.x < r.x + 4 || b.x + b.width > r.x + r.width - 4) out.push(`${g.dataset.id}: '${t.textContent}' overflows its box`);
      if (fs < 8) out.push(`${g.dataset.id}: '${t.textContent}' shrunk to ${fs}px`);
      if (t.textContent.endsWith('…')) out.push(`${g.dataset.id}: '${t.textContent}' is cut off`);
    }
  }
  return out;
}"""


BOXES_APART = """() => {
  const r = [...document.querySelectorAll('#col0 g.node')].map(g => ({ id: g.dataset.id, b: g.querySelector('rect').getBoundingClientRect() }));
  const lanes = [...document.querySelectorAll('#col0 rect.lane-bg')].map(l => l.getBoundingClientRect());
  const out = [];
  for (let i = 0; i < r.length; i++) {
    const a = r[i].b;
    if (!lanes.some(l => a.left >= l.left - 0.5 && a.right <= l.right + 0.5 && a.top >= l.top && a.bottom <= l.bottom))
      out.push(`${r[i].id} sticks out of its lane`);
    for (let j = i + 1; j < r.length; j++) {
      const b = r[j].b;
      if (a.left < b.right + 4 && b.left < a.right + 4 && a.top < b.bottom && b.top < a.bottom) out.push(`${r[i].id} overlaps ${r[j].id}`);
    }
  }
  return out;
}"""


def utility_views():
    for c in DATA.values():
        for mid, m in c["markets"].items():
            for name, u in m["utilities"].items():
                for arch in u["archetypes"]:
                    yield f"lens=roles&a={quote(f'{mid}/{arch}/{name}', safe='/')}&b=/"


@pytest.mark.parametrize("view", list(utility_views()))
def test_box_text_is_never_cut_off(page, view):
    page.goto(f"{PAGE}#{view}")
    page.reload()
    problems = page.evaluate(TEXT_FITS)
    assert not problems, f"{view}: " + "; ".join(problems)


@pytest.mark.parametrize("view", list(views()) + list(utility_views()))
def test_boxes_never_overlap(page, view):
    page.goto(f"{PAGE}#{view}")
    page.reload()
    problems = page.evaluate(BOXES_APART)
    assert not problems, f"{view}: " + "; ".join(problems)


def domain_views():
    maps = build.load_maps()
    for cc, c in DATA.items():
        for mid, m in c["markets"].items():
            seen = set()   # base nodes repeat in every archetype; check each once
            for arch in m["archetypes"]:
                nodes, _ = build.resolve(m, arch)
                for n in nodes.values():
                    if n.get("domain_area") and n["id"] not in seen:
                        seen.add(n["id"])
                        groups = build.map_for(maps, cc).get("groups", {})
                        full = {a for i in n["domain_area"]["full"] for a in groups.get(i, [i])}
                        yield f"lens=roles&a={mid}/{arch}&b=/", n["id"], len(full)


def fill_views():
    """Utilities whose fill carries its own territory: select the utility, then its slot node."""
    for cc, c in DATA.items():
        for mid, m in c["markets"].items():
            nodes = {n.get("slot"): n["id"] for l in [m["base"], *m["archetypes"].values()] for n in l.get("nodes", []) if n.get("slot")}
            for name, u in m["utilities"].items():
                for slot, f in u.get("fills", {}).items():
                    if isinstance(f, dict) and f.get("domain_area"):
                        yield f"lens=roles&a={quote(mid + '/' + u['archetypes'][0] + '/' + name, safe='/')}&b=/", nodes[slot], len(f["domain_area"]["full"])


@pytest.mark.parametrize("view,node,n_full", list(domain_views()) + list(fill_views()))
def test_domain_map_fills_the_selected_body(page, view, node, n_full):
    page.goto(f"{PAGE}#{view}")
    page.reload()
    page.click(f'#col0 g.node[data-id="{node}"]')
    assert page.locator("#col0 .dmap").count() == 1, f"{node}: no map"
    assert page.locator("#col0 .dmap path.full").count() == n_full, f"{node}: wrong areas filled"


SOURCED = """() => [...document.querySelectorAll('#col0 path.edge-hit')]
  .filter(h => !/\\nSource: \\S/.test(h.querySelector('title').textContent)).map(h => h.dataset.edge)"""


@pytest.mark.parametrize("view", list(views()))
def test_every_line_shows_its_source(page, view):
    page.goto(f"{PAGE}#{view}")
    page.reload()
    missing = page.evaluate(SOURCED)
    assert not missing, f"{view}: no source on hover for " + ", ".join(missing)
    hit = page.locator("#col0 path.edge-hit").first
    if hit.count():
        page.evaluate("() => document.querySelector('#col0 path.edge-hit').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
        assert page.locator("#col0 .panel dt", has_text="Source").count() >= 1, f"{view}: line panel has no source"


@pytest.mark.parametrize("width", [390, 1400])
def test_clicking_keeps_the_scroll_position(page, width):
    """Selecting a box or line redraws the columns; the page and the diagram's sideways scroll must not jump."""
    page.set_viewport_size({"width": width, "height": 700})
    page.goto(f"{PAGE}#lens=roles&a=ercot/competitive_area&b=/")
    page.reload()
    for target in ['#col0 g.node[data-id="residential"]', "#col0 path.edge-hit"]:
        page.evaluate("() => { scrollTo(0, document.documentElement.scrollHeight); const d = document.querySelector('#col0 .diagram'); d.scrollLeft = d.scrollWidth; }")
        before = page.evaluate("() => [scrollY, document.querySelector('#col0 .diagram').scrollLeft]")
        page.evaluate("(sel) => document.querySelector(sel).dispatchEvent(new MouseEvent('click', {bubbles: true}))", target)
        after = page.evaluate("() => [scrollY, document.querySelector('#col0 .diagram').scrollLeft]")
        assert after == before, f"{width}px, {target}: scroll {before} -> {after}"
    page.set_viewport_size({"width": 1400, "height": 1600})


@pytest.mark.parametrize("mid,first,second", [("caiso", "PG&E", "SMUD"), ("ercot", "Oncor", "CenterPoint"), ("pjm", "ComEd", "Dominion Energy Virginia")])
def test_switching_utility_keeps_the_utility_box_selected(page, mid, first, second):
    page.goto(f"{PAGE}#lens=roles&a={quote(f'{mid}//{first}', safe='/')}&b=/")
    page.reload()
    box = page.evaluate("(u) => [...document.querySelectorAll('#col0 g.node')].find(g => g.textContent.includes(u)).dataset.id", first)
    page.click(f'#col0 g.node[data-id="{box}"]')
    page.locator("#col0 .chain select").nth(1).select_option(second)
    assert page.locator("#col0 .panel h3").inner_text().startswith(second)
    page.click('#col0 g.node[data-id="ferc"]')
    page.locator("#col0 .chain select").nth(1).select_option(first)
    assert page.locator("#col0 .panel h3").inner_text() == "FERC", "a box that is still drawn stays selected"
