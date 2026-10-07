import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build  # noqa: E402

DATA = build.load()                       # schema errors fail collection, loudly

def graphs():
    """Yield (cc, market_id, archetype, nodes_by_id, edges) for every resolved diagram."""
    for cc, c in DATA.items():
        for mid, m in c["markets"].items():
            for arch in m["archetypes"]:
                nodes, edges = build.resolve(m, arch)
                yield cc, mid, arch, nodes, edges
