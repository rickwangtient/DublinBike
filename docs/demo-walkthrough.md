# Demo walkthrough

Show the map first, then the same searches with curl, then the same searches in pgAdmin, then the code. The numbers below match the app while the current data is loaded.

## 1. The map

Open http://localhost:8000.

- There are 115 stations, 1,743 cycle-lane segments, and 60 parks.
- Click the map near Grangegorman. Purple markers are the stations within the distance box.
- Choose St Stephen's Green and click Show park. Six stations are within 200 m. No lane crosses that park.
- Choose Phoenix Park and click Show park. Lanes that cross the park are drawn in orange.
- Save a favourite, then edit it and delete it. That covers create, update, and delete.

## 2. Curl

Run these in a terminal. Each one is the same search the map just did.

All stations, as GeoJSON:

```bash
curl -s "http://localhost:8000/api/stations/" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['features']), 'stations')"
```

Stations within 0.8 km of TU Dublin Grangegorman. The closest is Grangegorman Lower (South), 55 m away:

```bash
curl -s "http://localhost:8000/api/stations/nearby/?lat=53.3547&lng=-6.2795&distance=0.8"
```

This one fails on purpose, because lat and lng are missing:

```bash
curl -s "http://localhost:8000/api/stations/nearby/"
```

It returns `{"error":"lat and lng parameters are required"}`.

Stations inside St Stephen's Green. This returns none, because the stations are on the street:

```bash
curl -s "http://localhost:8000/api/stations/in_park/?park_id=119"
```

Stations within 200 m of the park edge. This returns 6:

```bash
curl -s "http://localhost:8000/api/stations/near_park/?park_id=119&distance=200"
```

Lane segments that cross Phoenix Park. This returns 31:

```bash
curl -s "http://localhost:8000/api/lanes/through_park/?park_id=116"
```

## 3. pgAdmin

Right-click dublin_bike_db and choose Query Tool. Run these one at a time.

How many rows are in each table:

```sql
SELECT 'stations' AS layer, COUNT(*) FROM bikes_station
UNION ALL SELECT 'lanes', COUNT(*) FROM bikes_cyclelane
UNION ALL SELECT 'parks', COUNT(*) FROM bikes_park;
```

The same nearby search, done in PostGIS. `::geography` makes the distance come back in metres:

```sql
SELECT name,
       ROUND(ST_Distance(
           location::geography,
           ST_SetSRID(ST_MakePoint(-6.2795, 53.3547), 4326)::geography
       )) AS metres
FROM bikes_station
WHERE ST_DWithin(
    location::geography,
    ST_SetSRID(ST_MakePoint(-6.2795, 53.3547), 4326)::geography,
    800
)
ORDER BY metres
LIMIT 5;
```

Stations within 200 m of St Stephen's Green:

```sql
SELECT s.name,
       ROUND(ST_Distance(s.location::geography, p.area::geography)) AS metres
FROM bikes_station s
JOIN bikes_park p ON p.name = 'St Stephen''s Green'
WHERE ST_DWithin(s.location::geography, p.area::geography, 200)
ORDER BY metres;
```

Lanes that cross Phoenix Park:

```sql
SELECT COUNT(*) AS lanes_crossing_phoenix_park
FROM bikes_cyclelane l
JOIN bikes_park p ON p.name = 'Phoenix Park'
WHERE ST_Intersects(l.path, p.area);
```

The spatial indexes. Each geometry column has a GiST index:

```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE tablename LIKE 'bikes_%'
  AND indexdef ILIKE '%gist%';
```

## 4. The code

The models are the three shapes. A station is a point, a lane is a line, and a park is a polygon. They are in `bikes/models.py`:

```python
location = models.PointField(srid=4326)       # Station
path = models.LineStringField(srid=4326)      # CycleLane
area = models.MultiPolygonField(srid=4326)    # Park
```

`srid=4326` is normal GPS latitude and longitude, the same system the map uses.

The map click is in `dashboard/templates/dashboard/index.html`. It sends the click location to the API and draws the GeoJSON that comes back:

```javascript
const data = await fetchJson(
    `/api/stations/nearby/?lat=${lat}&lng=${lng}&distance=${km}&min_bikes=${minBikes()}`
);
resultStations.addData(data);
```

That URL is handled by `nearby` in `api/views.py`. `location__distance_lte` is the PostGIS distance query, and the results are ordered closest first:

```python
point = Point(float(lng), float(lat), srid=4326)
distance_km = float(request.query_params.get('distance', 1))
stations = self.get_queryset().filter(
    location__distance_lte=(point, D(km=distance_km))
).annotate(
    distance=Distance('location', point)
).order_by('distance')
return Response(self.get_serializer(stations, many=True).data)
```

The other two searches are in the same file:

```python
# Stations inside the park polygon
stations = self.get_queryset().filter(location__within=park.area)

# Lane lines that cross the park polygon
lanes = CycleLane.objects.filter(path__intersects=park.area)
```

The map, the curl commands, and the pgAdmin queries are all the same three PostGIS searches.
