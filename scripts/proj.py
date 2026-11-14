"""Shared map projection: spherical Lambert azimuthal equal-area centred on Sweden.

Must match PROJ4 in build_vectors.sh so raster and vectors line up.
"""
import numpy as np

R = 6371000.0
LON0, LAT0 = 15.0, 62.0
PROJ4 = f"+proj=laea +lat_0={LAT0} +lon_0={LON0} +R={R:.0f} +units=m +no_defs"

# Map extent in projected metres (xmin, ymin, xmax, ymax)
EXTENT = (-1300000.0, -1100000.0, 1250000.0, 1050000.0)
RES = 500.0  # metres per raster pixel

# Outer buffer ring: coarser relief so any part of Scandinavia can be panned to the centre of the screen
OUTER_EXTENT = (-2000000.0, -1800000.0, 1900000.0, 1550000.0)
OUTER_RES = 2000.0

_p0, _l0 = np.radians(LAT0), np.radians(LON0)


def forward(lon, lat):
    p, dl = np.radians(lat), np.radians(lon) - _l0
    k = np.sqrt(2 / (1 + np.sin(_p0) * np.sin(p) + np.cos(_p0) * np.cos(p) * np.cos(dl)))
    x = R * k * np.cos(p) * np.sin(dl)
    y = R * k * (np.cos(_p0) * np.sin(p) - np.sin(_p0) * np.cos(p) * np.cos(dl))
    return x, y


def inverse(x, y):
    rho = np.hypot(x, y)
    c = 2 * np.arcsin(np.clip(rho / (2 * R), -1, 1))
    with np.errstate(invalid="ignore", divide="ignore"):
        lat = np.arcsin(np.cos(c) * np.sin(_p0) + np.where(rho > 0, y * np.sin(c) * np.cos(_p0) / rho, 0))
    lon = _l0 + np.arctan2(x * np.sin(c), rho * np.cos(_p0) * np.cos(c) - y * np.sin(_p0) * np.sin(c))
    return np.degrees(lon), np.degrees(lat)


if __name__ == "__main__":
    pts = {"Bergen": (5.3, 60.4), "Stavanger": (5.7, 58.97), "Esbjerg": (8.45, 55.47), "Gedser": (11.93, 54.57),
           "Haparanda": (24.14, 65.83), "Treriksroset": (20.55, 69.06), "Tromso": (18.95, 69.65),
           "Lofoten": (12.0, 68.0), "Gotland": (19.3, 57.0), "Helsinki": (24.94, 60.17)}
    for n, (lo, la) in pts.items():
        x, y = forward(lo, la)
        print(f"{n:14s} {x/1000:8.0f} {y/1000:8.0f}")
    print("corners lon/lat:", [inverse(np.array(a), np.array(b)) for a, b in
                               [(EXTENT[0], EXTENT[1]), (EXTENT[2], EXTENT[3]), (EXTENT[0], EXTENT[3]), (EXTENT[2], EXTENT[1])]])
