# Scandinavia Trip Map

An interactive map of Sweden and its neighbours for planning a trip. It uses an equal-area projection
(Lambert azimuthal equal-area, centred at 62°N 15°E) so countries and regions compare at true size,
and shows every town as a circle whose area matches its population.

- Shaded terrain, lakes, rivers, borders, railways and roads (motorway, trunk and primary)
- About 8,000 places: every town of 200+ residents in Sweden, Norway, Denmark and Finland,
  and towns of 15,000+ in the surrounding countries
- Filter by population and country, search, a city card with key facts, and a shortlist
- WebGL rendering (deck.gl) for smooth panning and zooming; trackpad pinch zooms, two-finger swipe pans

## Run it

The page loads its data with `fetch`, so it needs a local web server (opening `index.html` as a file won't work):

```bash
npm start
```

This serves `web/` at http://localhost:8765 and opens it.

## Rebuild the data

The generated files in `web/data/` are committed. To rebuild them, download the sources and run the scripts.
Python needs `numpy`, `pillow` and `scipy`; the vector build uses `mapshaper` (`npm install`).

```bash
python3 -m venv .venv && .venv/bin/pip install numpy pillow scipy
npm install
.venv/bin/python scripts/fetch_dem.py data/raw/dem mosaic   # detailed terrain tiles
.venv/bin/python scripts/fetch_dem.py data/raw/dem outer    # coarse outer ring
./scripts/fetch_osm_roads.sh                                # OSM roads via Overpass (slow, retries)
.venv/bin/python scripts/osm_roads_to_geojson.py
./scripts/build_vectors.sh                                  # needs Natural Earth GeoJSON in data/raw/ne
.venv/bin/python scripts/build_relief.py
.venv/bin/python scripts/build_cities.py                    # needs GeoNames dumps in data/raw/geonames
```

Natural Earth layers come from https://github.com/nvkelso/natural-earth-vector (`geojson/` folder) and
GeoNames dumps (`SE`, `NO`, `DK`, `FI`, `cities15000`, `admin1CodesASCII`) from https://download.geonames.org/export/dump/.

## Data sources

- Terrain: [Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) on AWS (Mapzen; includes SRTM, GMTED, ETOPO1 and others)
- Roads in Sweden, Norway and Denmark: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, ODbL
- Water, borders, railways, other roads: [Natural Earth](https://www.naturalearthdata.com/) (public domain)
- Places and population: [GeoNames](https://www.geonames.org/) (CC BY 4.0); figures are municipality
  or locality counts depending on the place
