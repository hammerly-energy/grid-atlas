"""Layout check: in every view, every relationship line can be clicked on its own,
no line runs through a box it doesn't connect, and each line meets its boxes square
(so the arrowhead lines up with the line).

Runs the real page in headless Chromium. Needs Playwright:
    python3 -m pip install playwright && python3 -m playwright install chromium
Skipped when Playwright isn't installed; CI always runs it.
"""
import os
from pathlib import Path
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


@pytest.mark.parametrize("view,node,n_full", list(domain_views()))
def test_domain_map_fills_the_selected_body(page, view, node, n_full):
    page.goto(f"{PAGE}#{view}")
    page.reload()
    page.click(f'#col0 g.node[data-id="{node}"]')
    assert page.locator("#col0 .dmap").count() == 1, f"{node}: no map"
    assert page.locator("#col0 .dmap path.full").count() == n_full, f"{node}: wrong areas filled"
