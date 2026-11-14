#!/bin/sh
# Clip, project (equal-area, see proj.py) and simplify vector layers into web/data.
set -e
cd "$(dirname "$0")/.."
NE=data/raw/ne
OUT=data/build
mkdir -p $OUT web/data
MS=node_modules/.bin/mapshaper
PROJ="+proj=laea +lat_0=62.0 +lon_0=15.0 +R=6371000 +units=m +no_defs"
LL_BOX=-45,40,75,80
XY_BOX=-2000000,-1800000,1900000,1550000

layer() { # name, simplify %, extra commands..., inputs after --
  name=$1; pct=$2; shift 2
  $MS -i "$@" combine-files -merge-layers force -clip bbox=$LL_BOX -proj "$PROJ" -clip bbox=$XY_BOX \
    -simplify $pct keep-shapes -rename-layers $name -o $OUT/$name.json format=geojson precision=10 force
}

layer land 40% $NE/ne_10m_land.geojson $NE/ne_10m_minor_islands.geojson
$MS -i $OUT/land.json -filter-fields '' -o $OUT/land.json force
layer lakes 50% $NE/ne_10m_lakes.geojson $NE/ne_10m_lakes_europe.geojson
$MS -i $OUT/lakes.json -filter-fields name -o $OUT/lakes.json force
layer rivers 50% $NE/ne_10m_rivers_lake_centerlines.geojson $NE/ne_10m_rivers_europe.geojson
$MS -i $OUT/rivers.json -filter-fields name,scalerank -o $OUT/rivers.json force
layer borders 50% $NE/ne_10m_admin_0_boundary_lines_land.geojson
$MS -i $OUT/borders.json -filter-fields '' -o $OUT/borders.json force
layer rail 20% $NE/ne_10m_railroads.geojson
$MS -i $OUT/rail.json -filter-fields '' -o $OUT/rail.json force

# Natural Earth highways, normalised to the OSM road classes
$MS -i $NE/ne_10m_roads.geojson -filter 'type == "Major Highway" || type == "Secondary Highway"' \
  -each 'kind = type == "Major Highway" ? "trunk" : "primary"; ref = name || ""; src = "ne"' \
  -filter-fields kind,ref,src -o $OUT/ne_roads.geojson force
if [ -s data/raw/osm/roads_osm.geojson ]; then
  # OSM inside Sweden/Norway/Denmark, Natural Earth for the surrounding countries
  $MS -i $NE/ne_10m_admin_0_countries.geojson -filter '["SWE","NOR","DNK"].indexOf(ADM0_A3) > -1' \
    -o $OUT/osm_countries.geojson force
  $MS -i $OUT/ne_roads.geojson -clip bbox=$LL_BOX -erase $OUT/osm_countries.geojson -o $OUT/ne_roads.geojson force
  layer roads 15% data/raw/osm/roads_osm.geojson $OUT/ne_roads.geojson
else
  layer roads 50% $OUT/ne_roads.geojson
fi
# Merge the many short ways into one multi-line per source, road class and route number
$MS -i $OUT/roads.json -dissolve kind,ref,src -o $OUT/roads.json force

$MS -i $OUT/land.json $OUT/lakes.json $OUT/rivers.json $OUT/borders.json $OUT/rail.json $OUT/roads.json \
  combine-files -o web/data/layers.topo.json format=topojson quantization=200000 force
ls -la $OUT web/data
