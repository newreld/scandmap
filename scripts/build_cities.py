"""Extract populated places from GeoNames, project them and drop suburbs/districts of bigger cities."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

from proj import OUTER_EXTENT as EXTENT, forward

ROOT = Path(__file__).resolve().parent.parent
GN = ROOT / "data/raw/geonames"
COUNTRIES = ["SE", "NO", "DK", "FI"]
KEEP_CODES = {"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLL", "PPLS", "PPLF"}
MIN_POP = 200
csv.field_size_limit(sys.maxsize)


def main():
    admin1 = {}
    with open(GN / "admin1CodesASCII.txt", encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            admin1[row[0]] = row[1]

    # Every place from the focus countries; towns of 15,000+ from the surrounding countries for context
    sources = [(GN / f"{cc}.txt", MIN_POP) for cc in COUNTRIES] + [(GN / "cities15000.txt", 15000)]
    places = []
    for path, min_pop in sources:
        with open(path, encoding="utf-8") as f:
            for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
                if r[6] != "P" or r[7] not in KEEP_CODES or not r[14] or int(r[14]) < min_pop:
                    continue
                cc = r[8]
                if path.name == "cities15000.txt" and cc in COUNTRIES:
                    continue
                elev = r[15] or r[16]
                places.append({
                    "name": r[1], "cc": cc, "pop": int(r[14]), "code": r[7],
                    "region": admin1.get(f"{cc}.{r[10]}", ""), "lon": float(r[5]), "lat": float(r[4]),
                    "elev": int(elev) if elev and elev.lstrip("-").isdigit() and int(elev) > -999 else None,
                })

    x, y = forward(np.array([p["lon"] for p in places]), np.array([p["lat"] for p in places]))
    xmin, ymin, xmax, ymax = EXTENT
    for p, px, py in zip(places, x, y):
        p["x"], p["y"] = float(px), float(py)
    places = [p for p in places if xmin <= p["x"] <= xmax and ymin <= p["y"] <= ymax]

    # Biggest first; drop places that sit inside a much bigger city's core (suburbs, districts, duplicates)
    places.sort(key=lambda p: -p["pop"])
    kept = []
    for p in places:
        absorbed = False
        for k in kept:
            if k["pop"] < 3 * p["pop"] and not (k["name"] == p["name"]):
                continue
            core = 9.0 * np.sqrt(k["pop"])  # metres: ~11 km for Stockholm, ~1 km for a 10k town
            if (k["x"] - p["x"]) ** 2 + (k["y"] - p["y"]) ** 2 < core ** 2:
                absorbed = True
                break
        if not absorbed:
            kept.append(p)

    # Municipalities/suburbs inside a metro area: tag with the metro name so the map can de-emphasise them
    metros = [k for k in kept if k["pop"] >= 300000]
    for p in kept:
        p["metro"] = next((m["name"] for m in metros if m["pop"] >= 8 * p["pop"]
                           and (m["x"] - p["x"]) ** 2 + (m["y"] - p["y"]) ** 2 < 30000 ** 2), "")

    out = [[p["name"], p["cc"], p["pop"], round(p["x"]), round(p["y"]), p["region"], p["elev"], p["metro"]] for p in kept]
    (ROOT / "web/data/cities.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    se = [p for p in kept if p["cc"] == "SE"]
    print(f"{len(places)} in extent -> {len(kept)} kept ({len(se)} SE, {sum(p['pop'] >= 1000 for p in kept)} >=1000)")
    print([(p["name"], p["pop"], p["metro"]) for p in se[:30]])


if __name__ == "__main__":
    main()
