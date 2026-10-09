"""Bill lens ("Who sets my rate?"): the table answers every part of the bill for every setup and class,
names who limits each part and who bills it, and lines up across compare columns.

Runs the real page in headless Chromium; skipped without Playwright, like test_layout.py.
"""
import json
import os
from pathlib import Path
import pytest
import build
from conftest import DATA

sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "web/index.html").as_uri()
ANSWERS = json.loads((ROOT / "web/data.json").read_text())["answers"]


def setups():
    for c in DATA.values():
        for mid, m in c["markets"].items():
            for arch in m["archetypes"]:
                yield mid, arch


@pytest.fixture(scope="module")
def page():
    with sync_api.sync_playwright() as p:
        exe = os.environ.get("CHROMIUM_PATH")
        browser = p.chromium.launch(**({"executable_path": exe} if exe else {}))
        pg = browser.new_page(viewport={"width": 1400, "height": 1600})
        yield pg
        browser.close()


def open_view(page, hash_):
    page.goto(f"{PAGE}#{hash_}")
    page.reload()


ROWS = """() => [...document.querySelectorAll('#col0 table.ans tr.row')].map(tr => ({
  setterMode: tr.cells[1].querySelector('.mode') && tr.cells[1].querySelector('.mode').textContent,
  others: [...tr.cells[2].querySelectorAll('.mode')].map(m => m.textContent),
  text: tr.textContent }))"""
MODE_TEXT = {"sets": "sets", "approves": "approves", "caps": "caps", "levies": "levies",
             "passes_through": "passes through", "market": "market price"}


@pytest.mark.parametrize("mid,arch", list(setups()))
def test_every_part_of_every_bill_has_a_row(page, mid, arch):
    """One row per line item, the setter's mode on it, every limit beside it, and who bills it above the table."""
    classes = sorted({k.split("|")[2] for k in ANSWERS if k.startswith(f"{mid}|{arch}|")})
    assert classes, f"{mid}/{arch}: no answers"
    for cls in classes:
        open_view(page, f"lens=bill&cls={cls}&a={mid}/{arch}&b=/")
        rows = page.evaluate(ROWS)
        want = [it for k, a in ANSWERS.items() if k.startswith(f"{mid}|{arch}|{cls}|") for it in a["items"]]
        assert len(rows) == len(want), f"{mid}/{arch}/{cls}: {len(rows)} rows for {len(want)} line items"
        assert not [r for r in rows if "not entered" in r["text"]], f"{mid}/{arch}/{cls}: a row has no setter"
        got_modes = sorted(r["setterMode"] for r in rows)
        assert got_modes == sorted(MODE_TEXT[it["mode"]] for it in want), f"{mid}/{arch}/{cls}: setter modes differ"
        edges = {e["id"]: e for e in build.resolve(next(c["markets"][mid] for c in DATA.values() if mid in c["markets"]), arch)[1]}
        want_lim = sum(len(it["limits"]) for it in want)
        assert sum(len(r["others"]) for r in rows) == want_lim, f"{mid}/{arch}/{cls}: limits not all shown"
        assert page.locator("#col0 caption .billed").inner_text().startswith("Billed by "), f"{mid}/{arch}/{cls}: no biller"


ALIGN = """() => {
  const cols = [...document.querySelectorAll('.col')].filter(c => c.querySelector('.ans'));
  const tops = k => cols.map(c => { const el = c.querySelector(`tbody[data-k="${k}"]`); return el && Math.round(el.getBoundingClientRect().top); });
  const keys = [...new Set([...document.querySelectorAll('tbody[data-k]')].map(t => t.dataset.k))];
  return { n: cols.length, off: keys.filter(k => new Set(tops(k).filter(x => x !== null)).size > 1).map(k => `${k}: ${tops(k).join(' / ')}`) };
}"""


@pytest.mark.parametrize("cols", [
    "a=pjm/restructured_choice&b=caiso/iou_cca&c=gb/domestic_default_capped",
    "a=ercot/competitive_area&b=pjm/default_service_ipa&c=caiso/iou_bundled",
    "a=ercot/noie&b=gb/supplier_contract",
])
def test_compare_rows_line_up(page, cols):
    """Side by side, each part of the bill starts at the same height in every column that has it; a part
    another market of the same country has still gets a row ("No separate line")."""
    open_view(page, f"lens=bill&cls=residential&{cols}")
    r = page.evaluate(ALIGN)
    assert r["n"] >= 2
    assert not r["off"], "rows out of line: " + "; ".join(r["off"])


def test_whole_bill_cap_is_a_bracket(page):
    open_view(page, "lens=bill&cls=residential&a=gb/domestic_default_capped&b=pjm/restructured_choice")
    assert page.locator("#col0 .capped table.ans").count() == 1, "GB default tariff: table not inside the cap bracket"
    assert page.locator("#col1 .capped").count() == 0, "PJM has no whole-bill cap"
    assert page.locator('#col1 tbody[data-k="whole"]').count() == 0
    assert page.locator('#col1 tr.gap').count() == 0, "no rows for parts only Great Britain has"


def test_class_is_kept_in_the_link(page):
    open_view(page, "lens=bill&cls=large_ci&comp=distribution&a=pjm/restructured_choice&b=/")
    assert page.locator("#cls").input_value() == "large_ci"
    assert "cls=large_ci" in page.url
