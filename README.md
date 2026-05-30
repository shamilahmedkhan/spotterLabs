# Spotter Labs Fuel Route Planner

Backend take-home implementation in Django 6.0.5.

## What it does

- imports and normalizes the provided truck stop pricing CSV
- assigns offline city-centroid coordinates to truck stops during import
- optionally supports a follow-up Census batch geocoder pass for exacter enrichment
- geocodes user-entered start and finish locations through Nominatim with local caching
- calls OSRM once per request for route geometry by default, or OpenRouteService if an API key is provided
- finds truck stops close to the route corridor, using a wider corridor because station coordinates are city-based
- computes a fuel plan for a 500-mile range vehicle at 10 mpg

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

By default the app uses public OSRM routing and Nominatim geocoding. If you want to switch routing to OpenRouteService, set `OPENROUTESERVICE_API_KEY`.

## Commands

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_fuel_prices
.\.venv\Scripts\python.exe manage.py geocode_truckstops
.\.venv\Scripts\python.exe manage.py runserver
```

## API

`POST /api/route-plan/`

```json
{
  "start": "Dallas, TX",
  "finish": "Phoenix, AZ"
}
```
