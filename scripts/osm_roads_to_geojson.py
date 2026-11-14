"""Convert Overpass JSON road downloads (out geom) into one GeoJSON of LineStrings."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OSM = ROOT / "data/raw/osm"


def main():
    features = []
    for f in sorted(OSM.glob("roads_*_*.json")):
        for el in json.loads(f.read_text())["elements"]:
            if el.get("type") != "way" or len(el.get("geometry", [])) < 2:
                continue
            tags = el.get("tags", {})
            features.append({
                "type": "Feature",
                "properties": {"kind": tags["highway"], "ref": tags.get("ref", ""), "src": "osm"},
                "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in el["geometry"]]},
            })
    out = OSM / "roads_osm.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))
    kinds = {}
    for ft in features:
        kinds[ft["properties"]["kind"]] = kinds.get(ft["properties"]["kind"], 0) + 1
    print(out.name, len(features), kinds, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
