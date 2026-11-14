"""Render a shaded-relief basemap (hypsometric tint + hillshade) in the equal-area projection."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates, gaussian_filter

from proj import EXTENT, OUTER_EXTENT, OUTER_RES, RES, inverse

ROOT = Path(__file__).resolve().parent.parent
DEM = ROOT / "data/raw/dem"
SS = 2  # land mask supersampling

LAND_STOPS = [  # elevation m -> RGB
    (0, (176, 202, 158)), (80, (190, 211, 166)), (250, (212, 219, 177)), (500, (226, 218, 182)),
    (800, (214, 197, 164)), (1100, (196, 178, 150)), (1500, (214, 207, 198)), (1900, (246, 246, 246)),
]
SEA_STOPS = [(0, (200, 222, 236)), (-100, (184, 211, 230)), (-400, (166, 198, 222)), (-2000, (148, 184, 212))]


def ramp(v, stops):
    xs = np.array([s[0] for s in stops], dtype=float)
    order = np.argsort(xs)
    xs = xs[order]
    cols = np.array([s[1] for s in stops], dtype=float)[order]
    return np.stack([np.interp(v, xs, cols[:, i]) for i in range(3)], axis=-1)


def sample_dem(lon, lat, name):
    z, x0, y0 = map(int, (DEM / f"{name}.txt").read_text().split())
    mosaic = np.load(DEM / f"{name}.npy")
    n = 2 ** z
    px = ((lon + 180) / 360 * n - x0) * 256 - 0.5
    r = np.radians(lat)
    py = ((1 - np.log(np.tan(r) + 1 / np.cos(r)) / np.pi) / 2 * n - y0) * 256 - 0.5
    return map_coordinates(mosaic, [py, px], order=1, mode="nearest").astype(np.float32)


def land_mask(w, h, extent, res):
    img = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(img)
    xmin, _, _, ymax = extent
    to_px = lambda ring: [((x - xmin) / res * SS, (ymax - y) / res * SS) for x, y in ring]
    gj = json.loads((ROOT / "data/build/land.json").read_text())
    for g in gj.get("geometries") or [f["geometry"] for f in gj["features"]]:
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            d.polygon(to_px(poly[0]), fill=255)
            for hole in poly[1:]:
                d.polygon(to_px(hole), fill=0)
    return np.asarray(img.resize((w, h), Image.BOX), dtype=np.float32) / 255


def hillshade(elev, res, az=315, alt=45, zf=2.5):
    gy, gx = np.gradient(elev * zf, res)
    slope = np.arctan(np.hypot(gx, gy))
    # gy points south (image rows); ESRI convention: aspect = atan2(dz/dy, -dz/dx)
    aspect = np.arctan2(gy, -gx)
    a, b = np.radians(360 - az + 90), np.radians(alt)
    return np.clip(np.sin(b) * np.cos(slope) + np.cos(b) * np.sin(slope) * np.cos(a - aspect), 0, 1)


def render(extent, res, dem, out_name, zf):
    xmin, ymin, xmax, ymax = extent
    w, h = int((xmax - xmin) / res), int((ymax - ymin) / res)
    xs = xmin + (np.arange(w) + 0.5) * res
    ys = ymax - (np.arange(h) + 0.5) * res
    X, Y = np.meshgrid(xs, ys)
    lon, lat = inverse(X, Y)
    elev = sample_dem(lon, lat, dem)
    mask = land_mask(w, h, extent, res)

    land_elev = np.maximum(elev, 0)
    # Multi-directional hillshade, normalised so flat ground = 1
    shade = sum(wt * hillshade(land_elev, res, az, zf=zf) for wt, az in [(0.6, 315), (0.25, 270), (0.15, 0)])
    shade = shade / np.sin(np.radians(45))
    land = ramp(land_elev, LAND_STOPS) * np.clip(1 + 0.75 * (shade - 1), 0.35, 1.25)[..., None]

    sea_depth = gaussian_filter(np.minimum(elev, 0), 2)
    sea = ramp(sea_depth, SEA_STOPS)

    rgb = land * mask[..., None] + sea * (1 - mask[..., None])
    out = ROOT / "web/data"
    out.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    # Split into tiles no larger than 4096 px, the GPU texture limit on many phones
    nx, ny = -(-w // 4096), -(-h // 4096)
    nx, ny = max(nx, 2 if w > 4096 else 1), max(ny, 2 if h > 4096 else 1)
    stem = out_name.rsplit(".", 1)[0]
    for old in out.glob(f"{stem}-[0-9]*-[0-9]*.jpg"):
        old.unlink()
    xs = [round(i * w / nx) for i in range(nx + 1)]
    ys = [round(j * h / ny) for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            name = f"{stem}-{j}-{i}.jpg" if nx * ny > 1 else out_name
            img.crop((xs[i], ys[j], xs[i + 1], ys[j + 1])).save(out / name, quality=86, optimize=True, progressive=True)
    print(out_name, w, h, f"{nx}x{ny} tiles", "x:", xs, "y:", ys)


def main():
    render(EXTENT, RES, "mosaic", "relief.jpg", 2.5)
    # Coarser pixels flatten slopes, so exaggerate more to keep a similar look
    render(OUTER_EXTENT, OUTER_RES, "outer", "relief-outer.jpg", 6)


if __name__ == "__main__":
    main()
