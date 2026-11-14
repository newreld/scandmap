#!/bin/sh
# Fetch OSM motorway/trunk/primary roads per country from Overpass, retrying with backoff across mirrors.
cd "$(dirname "$0")/../data/raw/osm" || exit 1
EPS="https://overpass-api.de/api/interpreter https://overpass.kumi.systems/api/interpreter https://overpass.private.coffee/api/interpreter"
for c in DK SE NO; do
  for cls in "motorway|trunk" "primary"; do
    f="roads_${c}_$(echo "$cls" | cut -d'|' -f1).json"
    [ -s "$f" ] && head -c 20 "$f" | grep -q '{' && continue
    Q="[out:json][timeout:600];area[\"ISO3166-1\"=\"$c\"][admin_level=2]->.a;way[\"highway\"~\"^($cls)\$\"](area.a);out tags geom qt;"
    wait=30
    for attempt in 1 2 3 4 5 6 7 8; do
      for ep in $EPS; do
        code=$(curl -sS --max-time 700 -A "scanmap-personal-trip-map/0.1" -o "$f.part" -w "%{http_code}" --data-urlencode "data=$Q" "$ep")
        echo "$c $cls attempt $attempt $ep -> $code $(wc -c < "$f.part" 2>/dev/null)"
        if [ "$code" = 200 ] && head -c 20 "$f.part" | grep -q '{'; then mv "$f.part" "$f"; break 2; fi
      done
      sleep $wait; wait=$((wait * 2))
    done
  done
done
rm -f ./*.part
ls -la
