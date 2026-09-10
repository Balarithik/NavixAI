# CampusNav Outdoor + Indoor Navigation — Research & Architecture Plan

## Executive recommendation

Build CampusNav as a **two-layer navigation system**:

1. **Outdoor layer:** Google Maps JavaScript API as the interactive geographic basemap, with CampusNav-owned block/POI data rendered as markers, polygons, and route overlays.
2. **Indoor layer:** CampusNav-owned floor maps and navigation graphs for each building, using the existing CSV → MySQL → Django → React pipeline.

Do not attempt to make Google Maps itself understand room-level indoor navigation. Instead, treat Google Maps as the outdoor geographic shell and switch into a building-specific indoor map when the user selects a block.

The core experience becomes:

`Campus → select/search block → outdoor route/preview → Enter Block → floor map → indoor navigation`

## 1. What the current campus sources tell us

The Euphoria 2026 campus page exposes a campus venue directory and a satellite map, including the main gate, hostels, central library, administration, Computer Block, and academic blocks 1 through 11. The page currently describes the map as a KARE campus satellite map and lists the blocks as selectable campus venues.

The rendered Euphoria page identifies its map stack as Leaflet with Esri tiles, rather than Google Maps. That makes it useful as a reference/source for campus layout, but it should not be treated as a Google Maps data API.

KARE's official sustainability-report campus master plan is a particularly useful source for building/block names and campus layout. It lists Academic Blocks 1–8, as well as many other campus facilities, roads, water bodies and open spaces. The report gives a campus total area of 1,536,957 m².

An official KARE geotagged-photo document identifies the 8th Block as a physical building and provides GPS coordinates of approximately 9.575069° N, 77.675783° E (converted from 9°34'30.25" N, 77°40'32.82" E).

## 2. Recommended product architecture

### Outdoor mode

Use Google Maps JavaScript API for:

- interactive campus basemap
- satellite/roadmap/hybrid views
- pan/zoom
- current location
- outdoor markers
- block selection
- route visualization
- search/autocomplete where appropriate

Google Maps JavaScript API supports customizable map styles, markers, interactive data layers, overlays, and custom graphics. Current Google documentation recommends the modern Routes library for route computation and AdvancedMarkerElement rather than the deprecated legacy Marker API.

### Campus data owned by CampusNav

Maintain your own data for:

- blocks
- building entrances
- campus gates
- walkable paths
- pedestrian junctions
- facilities
- building/floor relationships
- indoor map assets

This should live in MySQL and be served by Django.

### Indoor mode

When a user chooses a block:

`Outdoor Map → Building selected → Building detail → Floor selector → Indoor floor map`

The indoor map remains independent from Google geographic coordinates.

## 3. The key architectural decision: one application, two map engines

Do not try to force the entire application into one map implementation.

Use:

### OutdoorMap

Google Maps JavaScript API.

### IndoorMap

Custom SVG/Canvas renderer using your existing `floor.csv`/database coordinates.

Both are controlled by one navigation state:

```text
navigationMode = OUTDOOR | INDOOR

selectedBuilding
selectedFloor
currentLocation
destination
route
```

This keeps the UX continuous while keeping the technical models correct.

## 4. Outdoor data model

Extend the existing MySQL schema.

### Building

```text
id
building_code
name
category
latitude
longitude
entrance_latitude
entrance_longitude
is_navigable
is_active
```

Examples:

```text
8TH_BLOCK
9TH_BLOCK
CENTRAL_LIBRARY
ADMIN_OFFICE
COMPUTER_BLOCK
```

### OutdoorNode

```text
id
node_id
building_id
type
latitude
longitude
name
```

Types:

```text
gate
junction
walkway
building_entrance
facility
landmark
```

### OutdoorEdge

```text
id
from_node
to_node
distance_m
accessible
is_active
```

This gives you a campus-specific pedestrian graph.

### BuildingFloor

```text
id
building
floor_number
name
map_asset
```

Your existing indoor Node/Edge tables then connect to a Building/Floor.

## 5. Outdoor routing strategy

Use a hybrid strategy.

### For routes outside/approaching the campus

Google Routes API can provide walking routes between geographic origins and destinations.

The current Maps JavaScript Routes library exposes `Route.computeRoutes()` and supports walking routes, route distance, duration, and waypoints.

### For routes inside the campus

Use your own graph.

Reason:

Google can give you a geographic walking route, but CampusNav needs to know campus-specific paths, building entrances, internal pedestrian links, and exactly which entrance connects to a building's indoor graph.

Therefore:

```text
Outside campus
    ↓
Google route
    ↓
Main Gate / campus entrance
    ↓
CampusNav outdoor graph
    ↓
Building entrance
    ↓
CampusNav indoor graph
    ↓
Room
```

For the first outdoor MVP, you can even skip Google route computation and implement the campus graph first.

## 6. Block selection UX

The main screen should look like a modern Google-Maps-style navigation interface, not a conventional dashboard.

Recommended layout:

```text
┌────────────────────────────────────────┐
│ 🔍 Search campus, blocks, places       │
├────────────────────────────────────────┤
│                                        │
│              GOOGLE MAP                │
│                                        │
│        ● 8th Block                     │
│             ───── route ────           │
│                                        │
│                  ◎                     │
│               My location              │
│                                        │
│  + / -                     ◎ locate    │
│                                        │
├────────────────────────────────────────┤
│ 8th Block                              │
│ Academic Block 8                       │
│                                        │
│ [Directions] [Enter Building]          │
└────────────────────────────────────────┘
```

The search bar stays floating above the map.

The result/details area should behave like a bottom sheet.

Avoid a permanent large sidebar on mobile.

## 7. Search experience

The search should unify:

```text
Search campus
Search block
Search room
Search facility
Search department
```

Example:

```text
Search "8th Block"
```

Result:

```text
8th Block
Srinivasa Ramanujan Block
Academic Block

[Directions] [Open]
```

If the user searches:

```text
Room 8301
```

the application should know:

```text
Room 8301
→ 8th Block
→ Floor 3
→ Indoor destination
```

Then the app can automatically perform:

`Outdoor → 8th Block → Floor 3 → Room 8301`

This is a major product opportunity.

## 8. Selecting 8th Block

The intended flow should be:

```text
User selects 8th Block
        ↓
Outdoor map centers on 8th Block
        ↓
Building marker/polygon highlighted
        ↓
Bottom sheet opens
        ↓
"Enter Building"
        ↓
Indoor map opens
        ↓
Floor selector appears
```

For example:

```text
8th Block

Academic Block 8

Ground
Floor 1
Floor 2
Floor 3

[Open Floor Map]
```

Do not require the user to navigate through multiple unrelated pages.

## 9. Indoor floor map architecture

When the user enters a block:

```text
selectedBuilding = 8TH_BLOCK
```

the backend returns:

```json
{
  "building": "8TH_BLOCK",
  "floors": [
    {"floor": 0, "name": "Ground Floor"},
    {"floor": 1, "name": "First Floor"},
    {"floor": 2, "name": "Second Floor"},
    {"floor": 3, "name": "Third Floor"}
  ]
}
```

The frontend dynamically displays available floors.

For each floor:

```text
GET /api/buildings/8TH_BLOCK/floors/3/map/
```

The response supplies the floor-map asset and node data.

## 10. The indoor map should continue using your current CSV architecture

Keep the current model:

```text
floor.csv
  ↓
Django importer
  ↓
MySQL
  ↓
Nodes + Edges
  ↓
Graph
  ↓
Dijkstra
  ↓
Indoor route
  ↓
React indoor map
```

Do not replace the existing indoor engine with Google Maps.

This protects the QR-based navigation work you have already completed.

## 11. Outdoor-to-indoor transition

The cleanest implementation is a routing handoff.

Create:

```text
BuildingEntrance
```

as a bridge entity.

Example:

```text
Outdoor node:
8TH_BLOCK_MAIN_ENTRANCE
       ↓
Indoor node:
F1_N01
```

Then:

```text
Outdoor route
    ↓
8th Block entrance
    ↓
Indoor graph
    ↓
Room / lab
```

This creates one continuous navigation architecture.

## 12. Floor-map asset strategy

There are three good levels of implementation.

### Level 1 — SVG floor plans

Best for your current project.

Store:

```text
building
floor
svg_asset
```

and render node coordinates on top.

Advantages:

- crisp at any zoom
- easy route overlay
- easy custom styling
- lightweight
- compatible with your current x/y system

### Level 2 — Geo-referenced floor overlay

If you have accurate geographic bounds for a floor plan, Google Maps supports image GroundOverlay objects tied to latitude/longitude bounds.

This could let you visually overlay a building plan over its outdoor map location.

### Level 3 — Full indoor map engine

Later, use a dedicated indoor rendering system or vector tiles.

Do not start there.

## 13. Best map experience

Use two visual states.

### OUTDOOR

Google-style geographic map:

- roads
- satellite option
- campus blocks
- POIs
- current location
- outdoor route

### INDOOR

Simplified custom map:

- rooms
- corridors
- stairs
- lifts
- QR locations
- route
- floor selector

Both should share:

- search
- current destination
- route information
- bottom-sheet navigation
- progress UI

## 14. Google Maps styling

Use Google's current map customization mechanisms rather than trying to recreate the Google UI pixel-for-pixel.

Google Maps JavaScript API supports cloud map styling through Map IDs, as well as manual JSON styling.

Recommended visual direction:

- low-detail outdoor map
- muted POIs
- clear pedestrian paths
- restrained labels
- high-contrast CampusNav route
- floating controls
- clean white search surface
- rounded bottom sheet
- current-location button
- map-type/satellite control

The result should be "Google Maps-inspired CampusNav", not a literal clone.

## 15. Important Google Maps policy constraint

Do not build the campus dataset by tracing/digitizing Google satellite imagery.

Google Maps Platform terms explicitly prohibit creating content from Google Maps Content, including tracing or digitizing roadways and building outlines from the Satellite map type.

Therefore:

### Use Google for:

- basemap rendering
- map interaction
- allowed API-derived locations/routes
- outdoor geographic context

### Use CampusNav-owned data for:

- campus block coordinates
- campus pedestrian graph
- building entrances
- indoor maps
- floor layouts
- room locations
- indoor graph

The official KARE campus master plan and KARE-provided campus materials are much better sources for building/block inventory.

## 16. Recommended outdoor data acquisition

Do not scrape Google Maps HTML.

Create a controlled `campus_blocks.csv` initially:

```csv
block_id,name,category,latitude,longitude,entrance_latitude,entrance_longitude
8TH_BLOCK,8th Block,academic,9.575069,77.675783,...
9TH_BLOCK,9th Block,academic,...
LIBRARY,Central Library,facility,...
ADMIN,Admin Office,administration,...
```

Then create:

```text
campus_nodes.csv
campus_edges.csv
```

for walkable paths.

For higher accuracy:

1. Use the official KARE master plan to identify blocks.
2. Use official KARE geotagged materials where available.
3. Verify coordinates in the field using GPS/mobile collection.
4. Record entrances separately from building centers.

## 17. Why building center coordinates are not enough

A common mistake is:

```text
Block center → Block center
```

for routing.

Instead:

```text
Outdoor path
   ↓
Building entrance
   ↓
Indoor entrance node
```

The entrance is the actual routing handoff.

For a block, store:

```text
building_location
main_entrance
secondary_entrances
accessible_entrance
```

This becomes important for wheelchair/accessibility routing later.

## 18. API architecture

Recommended APIs:

### Campus

```text
GET /api/campus/
GET /api/campus/buildings/
GET /api/campus/buildings/<building_id>/
```

### Outdoor

```text
GET /api/outdoor/nodes/
GET /api/outdoor/route/?from=...&to=...
```

### Indoor

Keep your existing:

```text
GET /api/buildings/<id>/floors/
GET /api/nodes/
GET /api/routes/
POST /api/scan/
```

### Search

```text
GET /api/search/?q=8th%20block
```

Return a unified search object:

```json
{
  "type": "building",
  "id": "8TH_BLOCK",
  "name": "8th Block",
  "floor": null
}
```

For rooms:

```json
{
  "type": "room",
  "id": "8301",
  "building": "8TH_BLOCK",
  "floor": 3
}
```

## 19. Unified destination model

This is one of the most important architectural improvements.

A destination should not be only an indoor `node_id`.

Instead:

```text
Destination
 ├── outdoor entity
 ├── building
 ├── floor
 └── indoor node
```

Examples:

### Destination: 8th Block

```text
building = 8TH_BLOCK
```

### Destination: Room 8301

```text
building = 8TH_BLOCK
floor = 3
indoor_node = 8301
```

This allows a single search system to handle both outdoor and indoor destinations.

## 20. End-to-end route examples

### Example A — User wants 8th Block

```text
Search 8th Block
       ↓
Select 8th Block
       ↓
Outdoor map centers on 8th Block
       ↓
[Directions]
       ↓
Campus route
       ↓
8th Block entrance
       ↓
[Enter Building]
```

### Example B — User wants Room 8301

```text
Search Room 8301
       ↓
Result: Room 8301
       ↓
8th Block / Floor 3
       ↓
Outdoor navigation to 8th Block
       ↓
Building entrance
       ↓
Indoor Floor 3
       ↓
Indoor Dijkstra
       ↓
Room 8301
```

This should eventually feel like one route rather than two unrelated applications.

## 21. QR integration

Your existing QR system becomes even more valuable.

If a user scans:

```text
CAMPUSNAV:8TH_BLOCK:F1_N03
```

the application immediately knows:

```text
mode = INDOOR
building = 8TH_BLOCK
floor = 1
currentNode = F1_N03
```

If a user scans a block/entrance QR:

```text
CAMPUSNAV:8TH_BLOCK:ENTRANCE
```

the app can transition from:

```text OUTDOOR → INDOOR
```

without manual building selection.

## 22. UI redesign plan

Do the UI redesign as a product-wide navigation shell.

### Desktop

```text
┌─────────────────────────────────────────────┐
│ 🔍 Search campus...                         │
│                                             │
│                                             │
│                 MAP                         │
│                                             │
│                                             │
│                                     ◎       │
│                                  Locate     │
│                                             │
├─────────────────────────────────────────────┤
│ Selected place / navigation bottom sheet    │
└─────────────────────────────────────────────┘
```

### Mobile

```text
┌───────────────────────┐
│ 🔍 Search campus...   │
├───────────────────────┤
│                       │
│        MAP            │
│                       │
│                       │
│                       │
│                     ◎ │
├───────────────────────┤
│ 8th Block             │
│ Academic Block        │
│                       │
│ [Directions] [Open]   │
└───────────────────────┘
```

Do not use a traditional dashboard as the homepage.

The map should occupy most of the screen.

## 23. Core React architecture

Recommended:

```text
src/
├── app/
│   ├── App.jsx
│   └── navigationStore.js
│
├── components/
│   ├── MapShell.jsx
│   ├── SearchBar.jsx
│   ├── PlaceSheet.jsx
│   ├── MapControls.jsx
│   ├── BuildingSheet.jsx
│   ├── FloorSwitcher.jsx
│   ├── RouteSheet.jsx
│   ├── Scanner.jsx
│   └── NavigationProgress.jsx
│
├── maps/
│   ├── OutdoorMap.jsx
│   ├── IndoorMap.jsx
│   └── mapConfig.js
│
├── services/
│   ├── campusApi.js
│   ├── navigationApi.js
│   └── searchApi.js
│
├── hooks/
│   ├── useOutdoorMap.js
│   └── useNavigation.js
│
└── styles/
```

## 24. Backend architecture

```text
backend/
├── navigation/
│   ├── models/
│   │   ├── building.py
│   │   ├── floor.py
│   │   ├── node.py
│   │   └── edge.py
│   │
│   ├── outdoor/
│   │   ├── routing.py
│   │   ├── graph.py
│   │   └── serializers.py
│   │
│   ├── indoor/
│   │   ├── routing.py
│   │   ├── graph.py
│   │   └── serializers.py
│   │
│   ├── search/
│   │   └── services.py
│   │
│   └── qr/
│       └── services.py
```

Keep outdoor and indoor routing separate but expose them through the same navigation API layer.

## 25. One unified navigation engine

Create a high-level service:

```text
NavigationService
```

which decides:

```text
Where is origin?
Where is destination?
Are they outdoor or indoor?
Which building?
Which floor?
Is a campus transition necessary?
Is a building transition necessary?
Which graph should be used?
```

For example:

```text
OUTDOOR → OUTDOOR
```

uses:

`OutdoorGraph`

```text
INDOOR → INDOOR
```

uses:

`IndoorGraph`

```text
OUTDOOR → INDOOR
```

uses:

`OutdoorGraph → BuildingEntrance → IndoorGraph`

This is much more scalable than adding special cases in React.

## 26. Development roadmap

### Phase 1 — Outdoor map shell

Implement:

- Google Maps JS API
- map ID
- modern markers
- satellite/roadmap
- current location
- KARE campus center
- block markers

### Phase 2 — Campus dataset

Implement:

- buildings table
- outdoor nodes
- outdoor edges
- entrances
- block search

### Phase 3 — Block selection

Implement:

- marker click
- block search
- bottom sheet
- building details
- "Enter Building"

### Phase 4 — Indoor integration

Connect:

```text
Building → Floor → existing indoor map
```

### Phase 5 — Outdoor routing

Implement campus pedestrian graph and route visualization.

### Phase 6 — Cross-boundary routing

Implement:

```text
Outdoor → Building Entrance → Indoor
```

### Phase 7 — Unified search

Search:

```text
block
room
lab
facility
department
```

### Phase 8 — UI redesign

Replace the current dashboard-oriented interface with the map-first experience.

### Phase 9 — Navigation polish

Add:

- route bottom sheet
- turn instructions
- current progress
- floor transitions
- lift/stairs choice
- route recalculation

## 27. MVP target after outdoor work

A visitor should be able to perform:

```text
Open CampusNav
      ↓
See KARE campus map
      ↓
Search "8th Block"
      ↓
8th Block highlighted
      ↓
Tap Directions
      ↓
Outdoor route shown
      ↓
Reach 8th Block entrance
      ↓
Tap Enter Building
      ↓
Floor map opens
      ↓
Choose floor
      ↓
Search/select room
      ↓
Indoor route calculated
      ↓
QR-based or manual navigation
```

## 28. Recommended technology choice

Use:

```text
Outdoor Map
Google Maps JavaScript API

Outdoor Routing
CampusNav custom graph for campus
Google Routes API when external walking directions are useful

Indoor Map
Custom SVG/Canvas

Indoor Routing
Django + Dijkstra

Database
MySQL

Backend
Django + Django REST Framework

Frontend
React + Vite

QR
@zxing/browser + Python qrcode
```

Google's current Maps JavaScript API provides interactive 2D/3D maps, customizable styles, markers and custom data layers. The current AdvancedMarkerElement is preferred over the deprecated legacy Marker API. The modern Routes library provides `Route.computeRoutes()` for route calculation, while Places Autocomplete can provide a polished place-search experience when Places API is enabled.

## 29. What not to do

Do not:

- scrape Google Maps HTML
- scrape Google satellite tiles
- trace campus buildings from Google satellite imagery
- make Google Maps the indoor routing engine
- hard-code all block data in React
- hard-code floor lists
- create separate route logic for every screen
- duplicate the indoor database in frontend constants
- add WebSockets unless genuinely needed
- rebuild your existing QR/indoor engine

## 30. Final architecture

```text
                         CAMPUSNAV
                             │
                    Unified Search/State
                             │
                 ┌───────────┴───────────┐
                 │                       │
            OUTDOOR MODE             INDOOR MODE
                 │                       │
       Google Maps JS API           Custom SVG Map
                 │                       │
       CampusNav Block Data        MySQL Floor Data
                 │                       │
          Outdoor Graph              Indoor Graph
                 │                       │
            Dijkstra /               Dijkstra /
          Google Routes*             A* later
                 │                       │
                 └───────────┬───────────┘
                             │
                     Building Entrance
                             │
                    Outdoor ↔ Indoor
                         Handoff
```

The strongest long-term product is therefore not "a Google Maps clone". It is a **Google-Maps-style campus navigation shell with a CampusNav-owned outdoor pedestrian graph and a CampusNav-owned indoor navigation engine**.

*Use Google Routes where it is appropriate for geographic walking directions; do not make it the source of truth for campus-specific indoor/pedestrian topology.

## Sources

1. Kalasalingam Academy of Research and Education / Euphoria 2026 — Campus venues and satellite map.
2. Kalasalingam Academy of Research and Education — Sustainability Report 2024–25, Campus Master Plan.
3. Kalasalingam Academy of Research and Education — Geotagged Photos / Solar Panels, 8th Block.
4. Google Maps JavaScript API — Overview.
5. Google Maps JavaScript API — Style Reference and Cloud Map Styling.
6. Google Maps JavaScript API — Advanced Markers.
7. Google Maps JavaScript API — Routes Library / Route class.
8. Google Maps JavaScript API — Custom Overlays / GroundOverlay.
9. Google Maps Platform Service Specific Terms.
