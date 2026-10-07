"""Layout check: in every view, every relationship line can be clicked on its own,
and no line runs through a box it doesn't connect.

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
