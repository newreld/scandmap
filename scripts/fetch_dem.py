"""Download Terrarium elevation tiles (AWS open data) covering Scandinavia and mosaic them."""
import io
import math
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

# Detailed tiles for the core map, coarse tiles for the outer buffer ring
DEMS = {
    "mosaic": (7, (-19.5, 48.5), (50.0, 72.5)),
    "outer": (5, (-41.0, 69.0), (41.5, 77.0)),
}
URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/dem")
NAME = sys.argv[2] if len(sys.argv) > 2 else "mosaic"
Z, (LON_MIN, LON_MAX), (LAT_MIN, LAT_MAX) = DEMS[NAME]


def tile_x(lon):
    return int((lon + 180) / 360 * 2**Z)


def tile_y(lat):
    r = math.radians(lat)
    return int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2**Z)


def fetch(xy):
    x, y = xy
    req = urllib.request.Request(URL.format(z=Z, x=x, y=y), headers={"User-Agent": "scanmap/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        img = np.asarray(Image.open(io.BytesIO(r.read())).convert("RGB"), dtype=np.float32)
    return xy, img[..., 0] * 256 + img[..., 1] + img[..., 2] / 256 - 32768


def main():
    x0, x1 = tile_x(LON_MIN), tile_x(LON_MAX)
    y0, y1 = tile_y(LAT_MAX), tile_y(LAT_MIN)
    tiles = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    print(f"{len(tiles)} tiles x{x0}-{x1} y{y0}-{y1}")
    mosaic = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), dtype=np.float32)
    with ThreadPoolExecutor(16) as ex:
        for (x, y), elev in ex.map(fetch, tiles):
            mosaic[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = elev
    OUT.mkdir(parents=True, exist_ok=True)
    np.save(OUT / f"{NAME}.npy", mosaic)
    (OUT / f"{NAME}.txt").write_text(f"{Z} {x0} {y0}\n")
    print("saved", mosaic.shape, mosaic.min(), mosaic.max())


if __name__ == "__main__":
    main()
