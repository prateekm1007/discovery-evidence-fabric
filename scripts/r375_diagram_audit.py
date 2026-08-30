#!/usr/bin/env python3
"""R375 diagnostic: collect ALL text-geometry violations in every mechanism
diagram (the gate raises on the first; this lists them all for one-pass
fixing). Not a gate — a repair tool."""
import sys
sys.path.insert(0, '/home/z/my-project/discovery-evidence-fabric')
import matplotlib
matplotlib.use("Agg")
from premium_package_factory.diagrams import factory


def collect(fig, name):
    errors = []
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    extents = []
    for ax in fig.axes:
        ax_bbox = ax.get_window_extent(r)
        for txt in ax.texts:
            if not txt.get_text().strip():
                continue
            try:
                bb = txt.get_window_extent(r)
            except Exception:
                continue
            extents.append((txt.get_text()[:26], bb))
            if (bb.x0 < ax_bbox.x0 - 6 or bb.x1 > ax_bbox.x1 + 6 or
                    bb.y0 < ax_bbox.y0 - 6 or bb.y1 > ax_bbox.y1 + 6):
                errors.append(
                    f"OUTSIDE '{txt.get_text()[:36]}' bbox "
                    f"[{bb.x0:.0f},{bb.x1:.0f}]x[{bb.y0:.0f},{bb.y1:.0f}] "
                    f"axes [{ax_bbox.x0:.0f},{ax_bbox.x1:.0f}]")
    tol = 1.5
    for i in range(len(extents)):
        for j in range(i + 1, len(extents)):
            ta, a = extents[i]
            tb, b = extents[j]
            ix = min(a.x1, b.x1) - max(a.x0, b.x0)
            iy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if ix > tol and iy > tol:
                errors.append(
                    f"OVERLAP '{ta}' x '{tb}' ({ix:.0f}x{iy:.0f}px)")
    return errors


def main():
    import tempfile
    factory.OUTPUT_DIR = tempfile.mkdtemp()
    # monkeypatch _save's verify with the collector
    orig_save = factory._save

    def spy(fig, name):
        errs = collect(fig, name)
        if errs:
            raise RuntimeError(" || ".join(errs))
        return orig_save(fig, name)

    factory._save = spy
    total = 0
    for gen_name in [n for n in dir(factory) if n.startswith('diagram_P')]:
        try:
            getattr(factory, gen_name)()
        except RuntimeError as e:
            total += 1
            print(f"\n=== {gen_name[8:]} ===")
            for part in str(e).split(" || "):
                print("  ", part[:160])
    print(f"\nfailing diagrams: {total}/15")


if __name__ == "__main__":
    main()
