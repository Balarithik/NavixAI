# NavixAI — Implementation Plan

NavixAI is a clean, modern, indoor navigation web application designed for campus buildings. The application allows users to scan QR codes for localized indoor positioning (or manually select a location), select destinations, calculate multi-floor shortest routes using Dijkstra's algorithm with lift vs. stairs preferences, visualize routes on an interactive indoor floor map inspired by Google Maps / Snazzy Maps minimalist design, and follow turn-by-turn instructions with a lightweight gamified checkpoint and progress tracking experience.

## User Review Required

> [!IMPORTANT]
> **Database Configuration**:
> The prompt specifies MySQL. We have installed `pymysql` and configured standard MySQL database settings via `.env`. For local development environments where a MySQL daemon may not be running or credentials are not yet configured, the system will automatically fall back to SQLite if MySQL connection fails or if `DB_ENGINE=sqlite` is specified in `.env`. This ensures zero-friction immediate testing while being 100% production-ready for MySQL.

> [!NOTE]
> **Synthetic Floor Data**:
> We have existing synthetic data in `floor data/synthetic data/synthetic data block 1.csv` covering 3 floors (35 nodes, including Entrances, Reception, Corridors, Junctions, Rooms, Labs, Offices, Restrooms, Lift A, and Staircase A). We will copy this to `data/building_nodes.csv` as the default test dataset and generate the comprehensive edge topology.

---

## Proposed Architecture & Milestones

### Component Architecture

```mermaid
graph TD
    User([User / Browser])
    subgraph Frontend [React + Vite]
        UI[UI Controls & Search]
        Map[Interactive SVG Map: Zoom/Pan/Markers/Polyline]
        Scanner[ZXing QR Scanner & Camera]
        Gamify[Gamified Progress & Checkpoints]
        APIClient[Axios/Fetch API Client]
    end

    subgraph Backend [Django REST Framework]
        API[REST API Views]
        QRModule[QR Generator & Validator]
        ImportModule[CSV Importer & Validator]
        RoutingService[Dijkstra Routing Engine]
        InstructionGen[Instruction Generator]
        ORM[Django ORM Models]
    end

    subgraph Storage [Database]
        DB[(MySQL / SQLite)]
    end

    User <--> Frontend
    APIClient <--> API
    API --> RoutingService
    API --> QRModule
    API --> ORM
    ImportModule --> ORM
    ORM <--> DB
```

---

## Milestones & Work Breakdown

### Milestone 1: Environment & Project Foundation
- Create `.env.example` and `.env` with backend configuration (Secret Key, DB credentials, walking speed, coordinate scale factor) and frontend configuration (`VITE_API_BASE_URL`).
- Setup Django backend in `backend/` with `manage.py`, `config/settings.py`, `config/urls.py`, CORS configuration, and REST framework.
- Setup React + Vite frontend in `frontend/` with Lucide React, `@zxing/browser`, and custom minimalist CSS design tokens.
- Copy and standardize `floor data/synthetic data/synthetic data block 1.csv` to `data/building_nodes.csv`.

### Milestone 2: Models & Database Migration
- Implement Django models in `backend/navigation/models.py`:
  - `Building`: `id`, `name`, `code`, `description`
  - `Floor`: `id`, `building` (FK), `floor_number`, `name`, `map_width`, `map_height`
  - `Node`: `id`, `node_id` (unique), `building` (FK), `block`, `name`, `type` (entrance, room, junction, corridor, stair, lift, amenity, office, lab, restroom), `floor` (FK), `x`, `y`, `qr_code`, `is_active`, `is_checkpoint`
  - `Edge`: `id`, `from_node` (FK), `to_node` (FK), `distance`, `accessible`, `movement_type` (walk, stairs, lift), `is_active`
  - `QRCode`: `id`, `node` (OneToOne), `payload`, `image_path`
- Implement Django Admin in `backend/navigation/admin.py` with search, filters, and list views.
- Execute migrations and verify database schema.

### Milestone 3: CSV Import Pipeline
- Implement `backend/navigation/importer/csv_parser.py` and `validator.py`:
  - Validates CSV headers, data types, coordinate bounds, duplicate `node_id`, duplicate `qr_code`, node types.
  - Automatically ensures Building and Floor entities exist.
  - Builds default connected graph edges for the building:
    - Intra-floor corridor and room connectivity based on block/junction topology.
    - Inter-floor connections connecting Staircase A (`F1_N09` ↔ `F2_N01` ↔ `F3_N01`) with `movement_type='stairs'`, and Lift A (`F1_N10` ↔ `F2_N02` ↔ `F3_N02`) with `movement_type='lift'`.
- Implement Django management command `python manage.py import_nodes data/building_nodes.csv` with detailed CLI feedback and idempotency.

### Milestone 4: Graph Construction & Dijkstra Routing Engine
- Implement `backend/navigation/routing/`:
  - `graph.py` / `graph_service.py`: Builds adjacency graph from DB Nodes and Edges with distance calculations.
  - `dijkstra.py`: Dijkstra shortest path algorithm supporting edge filtering (mode: `lift`, `stairs`, or `any`).
  - `route_engine.py`: Computes complete route, detects floor transitions, checks if both lift and stairs are available between source and destination floors.
  - `instruction_generator.py`: Generates human-readable turn-by-turn directions (e.g. "Start at Main Entrance", "Continue 15m to Main Junction", "Take Lift A to Floor 2", "Turn right into corridor", "Arrive at Lab 1 on your left").

### Milestone 5: QR Generation & Validation API
- Implement `backend/navigation/qr/`:
  - `generator.py`: Generates QR code images with `CAMPUSNAV:<node_id>` payloads and saves to `qr_codes/`.
  - Management command or service to generate QR codes for all imported nodes.
- Implement DRF Serializers and Views:
  - `GET /api/building/` & `GET /api/floors/`
  - `GET /api/nodes/` & `GET /api/nodes/<node_id>/`
  - `POST /api/scan/` (validates QR payload, returns node info or error)
  - `GET /api/routes/?from=...&to=...&mode=...` (calculates path, distance, ETA, instructions, checkpoints, lift/stair availability)
  - `GET /api/qr/<node_id>/` (serves QR code image)

### Milestone 6: Frontend Scanner Component
- Implement `frontend/src/components/Scanner.jsx` using `@zxing/browser`:
  - Video stream view finder with target reticle.
  - Handles camera permissions and device selection.
  - Fallback simulated QR selector / test scanner modal for instant desktop testing without physical webcam.
  - Auto-sends decoded QR payload to `POST /api/scan/` and triggers navigation source setting.

### Milestone 7: Search & Location Selection
- Implement `frontend/src/components/LocationSelector.jsx` and `DestinationSelector.jsx`:
  - Clean dropdowns with quick search filtering across names, types, and floors.
  - Quick-action buttons: "Use Scanned Location", "Swap Start & Destination", "Clear".
  - Category tags (e.g., Room, Lab, Lift, Stairs, Restroom).

### Milestone 8 & 9: Indoor Map & Snazzy/Google Maps Minimalist UI
- Implement `frontend/src/components/NavigationMap.jsx`:
  - Custom interactive SVG indoor floor map with zoom (+/- / mouse wheel) and pan (drag).
  - Clean Snazzy Maps minimalist aesthetic: muted architectural floor layout, corridor guides, room outlines.
  - Clear markers: Start pin (green pulse), Destination pin (red pin), Lift/Stairs indicators, corridor junctions.
  - Route polyline: smooth accented route line with animated dash flow indicating walking direction.
  - Multi-floor visualization: floor switcher (F1, F2, F3) showing the segment of the route relevant to the active floor, with badges indicating floor transition points.

### Milestone 10: Lift vs. Stairs Routing & Gamification
- Implement `frontend/src/components/LiftStairModal.jsx`:
  - Pops up when a multi-floor route offers both lift and stairs, letting user choose "Lift (Accessible)" or "Stairs (Active route)".
- Implement `frontend/src/components/ProgressCard.jsx` & `AchievementPanel.jsx`:
  - Progress tracker showing percentage completed, distance walked / remaining.
  - Interactive "Step Next Checkpoint" simulator to simulate walking through the route.
  - Achievement toasts (e.g., "+10 Navigation XP: Checkpoint reached", "🏆 Floor Transition Completed").
  - "Destination Reached 🎯" completion card with stats (distance walked, time taken, XP earned).

### Milestone 11: Polish, Testing, and Documentation
- Comprehensive automated backend unit and integration tests (`tests.py` covering CSV import, graph building, Dijkstra, lift vs stairs, QR scan, and route APIs).
- Production-grade `README.md` with complete architecture diagram, setup guide, API reference, and screenshots.

---

## Verification Plan

### Automated Tests
1. Run backend test suite:
   ```bash
   cd backend
   python manage.py test navigation
   ```
2. Verify CSV import CLI:
   ```bash
   python manage.py import_nodes ../data/building_nodes.csv
   ```
3. Verify QR code batch generator:
   ```bash
   python manage.py generate_qrcodes
   ```

### Manual Verification Flows
1. **API Endpoints**:
   - Verify `GET /api/nodes/` returns imported nodes.
   - Verify `POST /api/scan/` with `{"payload": "CAMPUSNAV:F1_N01"}` returns Main Entrance.
   - Verify `GET /api/routes/?from=F1_N01&to=F2_N08&mode=lift` returns shortest path traversing Lift A with floor transition.
   - Verify `GET /api/routes/?from=F1_N01&to=F2_N08&mode=stairs` returns shortest path traversing Staircase A.
2. **Frontend UI**:
   - Start frontend via `npm run dev` and backend via `python manage.py runserver`.
   - Test scanning / manual start selection: select "Main Entrance" (Floor 1).
   - Test destination selection: select "Lab 1" (Floor 2).
   - Verify Lift vs. Stairs modal triggers and recalculates route upon selection.
   - Verify floor switcher automatically highlights Floor 1 and lets user toggle to Floor 2 to view the second floor segment.
   - Test gamified checkpoint progress: click "Simulate Step" to advance along the checkpoints, verify XP badges, floor transition celebration, and destination reached modal.

### Camera / QR Scanner Verification
1. Open scanner - camera permission requested
2. Live camera preview appears
3. QR detected and decoded
4. POST /api/scan/ validates QR payload
5. Current location updates on map
6. Scanner closes correctly
7. Reopen scanner - camera works again (no stream leaks)
8. Test permission denied handling
9. Test invalid QR code handling
10. Test camera unavailable flow

### Dynamic Map Verification
1. Change room name in floor.csv → import → frontend reflects change after page focus
2. Change x/y coordinates in floor.csv → import → map marker moves after page focus
3. Add new node to floor.csv → import → node appears in search and map after page focus
4. Add new floor to floor.csv → import → floor selector shows new floor after page focus
5. Route visualization uses updated coordinates after data refresh

---

## Outdoor + Indoor Extension (Campus-wide navigation)

See `@docs/campusnav_outdoor_indoor_research_plan.md` for the full researched architecture.
Summary of what was implemented on top of the indoor MVP (which is preserved unchanged):

### Data model (additive, migrations `0002`–`0003`; indoor tables untouched)
- `Building` extended: `category`, `latitude/longitude`, `entrance_latitude/entrance_longitude`,
  `source` + `coordinate_verified` provenance, `is_navigable`, `is_active`.
- `BuildingEntrance` bridge entity: `outdoor_node_id` ↔ `indoor_node_id` per building.
- `OutdoorNode` (`gate|junction|walkway|building_entrance|facility|landmark`, lat/lon,
  `is_accessible`, provenance) and `OutdoorEdge` (`edge_id`, `distance_m`, `accessible`,
  `movement_type`, bidirectional managed via `<edge_id>:R` reverse rows).
- New `CampusFacility` (map/search POI, optional `building` link — never a graph node) and
  `CampusSpace` (parking/landscape/water context — map/search only, never auto-graphed).
- Coordinate rule: `source` ∈ `verified|official|synthetic|unknown`; only 8th Block
  (9.575069, 77.675783, KARE geotagged document) is `verified` — everything else is
  clearly-marked synthetic dev data, never presented as surveyed.

### Split campus CSVs (`data/`, master import `python manage.py import_campus_data [dir] [--only STEP] [--dry-run]`)
- `academic_blocks.csv` (`building_id,name,category,latitude,longitude,is_active,source`)
- `hostels.csv` (same shape, `category=hostel`)
- `campus_facilities.csv` (`facility_id,...,building_id,...`; linked buildings auto-ensured)
- `campus_spaces.csv` (`space_id,...,space_type,...`; context only)
- `outdoor_nodes.csv` (`node_id,...,building_id,...`; FK-validated — only graph nodes route)
- `outdoor_edges.csv` (`edge_id,from_node,to_node,distance_m,movement_type,accessible,bidirectional,is_active`;
  endpoint-FK + self-loop validated, haversine fallback, stale `edge_id`s deactivated not deleted)
- `building_entrances.csv` (`entrance_id,building_id,...,accessible,indoor_node_id,is_active`;
  `indoor_node_id` FK-validated against indoor `Node`)
- Legacy `python manage.py import_campus` kept as a deprecated delegating wrapper.
- All imports: header-tolerant (`#` comments skipped), duplicate-in-file detection, collected
  error lists, idempotent upsert (verified: repeat run → 0 created).

### Routing
- `navigation/outdoor/graph.py` + `route_engine.py`: Dijkstra over the campus pedestrian graph
  (reuses the indoor `DijkstraRouter`; haversine fallback distances), same response shape as indoor.
- `navigation/navigation_service.py`: unified `outdoor | indoor | outdoor_to_indoor` routing with
  `segments[]`, totals, combined instructions/checkpoints. New indoor datasets per building work
  via existing `import_nodes --building-code <CODE>`.

### APIs (existing indoor endpoints untouched)
- `GET /api/campus/buildings/` · `GET /api/campus/buildings/<code>/`
- `GET /api/buildings/<code>/floors/` (dynamic floor selector)
- `GET /api/entrances/?building=<code>` · `GET /api/outdoor/nodes/`
- `GET /api/facilities/` · `GET /api/spaces/` (catalog, map/search only)
- `GET /api/outdoor/route/?from=&to=`
- `GET /api/search/?q=` (unified buildings + hostels + facilities + spaces + outdoor + indoor rooms)
- `GET /api/navigation/route/?from_type=&from_id=/from_lat,from_lon&to_type=&to_id=&mode=`
  (`to_type` also accepts `facility|space`; standalone POIs snap to nearest graph node)

### Frontend (map-first shell, Google-Maps-inspired)
- `hooks/useNavigation.js`: single nav state (`mapMode`, buildings, search, destination,
  unified route, GPS with permission handling, `locationSource: GPS|QR|MANUAL`).
- `maps/OutdoorMap.jsx`: Google Maps JS API (`AdvancedMarkerElement` preferred, legacy fallback)
  when `VITE_GOOGLE_MAPS_API_KEY` is set; otherwise a CampusNav-owned fallback campus map rendered
  from backend data (no key required, no scraped tiles).
- `components/SearchBar.jsx` (unified search), `BuildingSheet.jsx` (Directions / Enter Building),
  `DirectionsPanel.jsx` (outdoor+indoor segments as one journey).
- `pages/NavigationPage.jsx` refactored into the shell: floating search, full-screen
  `OUTDOOR | INDOOR` map, bottom sheets; existing indoor components (SVG map, scanner, lift/stairs,
  progress, achievements) reused unchanged.
- Env: `VITE_GOOGLE_MAPS_API_KEY`, `VITE_GOOGLE_MAP_ID` placeholders in `.env.example`
  (keys never committed).

### Unified outdoor + indoor QR positioning
- Canonical payloads (backend-authoritative, see `navigation/qr/payloads.py`):
  `CAMPUSNAV|OUTDOOR|<node_id>`, `CAMPUSNAV|INDOOR|<bldg>|<floor>|<node_id>`.
  Legacy `CAMPUSNAV:<id>` / `NAVIXAI:<id>` / raw ids still accepted (indoor).
- `OutdoorNode.qr_code` (migration `0004`; importer auto-assigns canonical payload
  unless the CSV provides `qr_code`; duplicates rejected).
- `POST /api/scan/` returns unified `{valid, location_type, location_id, name,
  latitude/longitude | floor/x/y, building_id, ...}` — old indoor keys preserved.
- `GET /api/qr/outdoor/<node_id>/` streams outdoor QR PNGs;
  `python manage.py export_qr_sheet [--only ...]` writes a printable HTML sheet.
- Frontend: one reused `Scanner.jsx` (camera + outdoor/indoor simulator + manual
  entry, inline errors); scan sets `currentLocation` + `locationSource=QR`, centers
  the outdoor map on outdoor scans, primes the indoor start node on indoor scans.
- `navigationStatus: BROWSE|PREVIEW|ACTIVE|COMPLETE` + manual `originOverride`
  ("From" search in the route sheet); `resolveOrigin`: override → QR/GPS → Main Gate.
- Map UX: junctions/walkways/spaces hidden unless navigating; gates/entrances/
  landmarks always; buildings + standalone facilities; route fit-bounds (Google)
  / viewBox fit (fallback); distinct current (QR-ring) + destination markers;
  compact ACTIVE progress (%, next step, checkpoints, Next/End).

### Verified journeys (live API, dev DB: 12 buildings / 12 outdoor nodes / 34 indoor nodes / 8 facilities / 6 spaces)
- Search "8th" → 8th Block; "Swimming" → facility; "Parking" → space; "Hostel" → hostel buildings.
- Outdoor route `MAIN_GATE → EIGHTH_BLOCK_ENTRANCE` (200) with instructions/checkpoints.
- Unified `MAIN_GATE → 8TH_BLOCK` → `mode: outdoor`; `MAIN_GATE → F2_N08 (Lab 1)` →
  `mode: outdoor_to_indoor` with 2 segments; facility/space dests snap to nearest graph node.
- `GET /api/buildings/MAIN/floors/` returns 3 dynamic floors; floor CSV pipeline untouched.
- Backend suite: 34/34 pass (12 indoor + 5 outdoor/unified + 11 importer/catalog + 6 QR).
  Frontend `vite build` + `vite dev` green; earlier `vis is not defined` listener bug fixed.

### UI simplification pass (frontend-only, map-first calm)
- Zones: TOP search / RIGHT rail / BOTTOM single contextual sheet; z-index
  centralized as `--z-*` vars (map 0–10, controls 20, search 30, sheet 40,
  modal 100, toast 110). Floor pills, context chip, zoom/locate rail moved
  below the topbar (no more topbar/floor/End-button collisions); indoor zoom
  rail moved off the bottom sheet area; legend hidden on mobile.
- One sheet at a time (state-driven ternary unchanged): place / directions /
  manual-indoor / hint. Preview collapsed to destination + distance/ETA + Start
  with step details behind an expander; ACTIVE keeps next-instruction focus.
- Removed duplicates: floating End button (panel End remains), inline Scan QR
  button in From-field (single topbar Scan remains).
- Slim segment chips (stats only on active); centered auto-dismiss toasts;
  focus-visible outlines; aria-labels/roles on all map controls.
- Drive-by fix: fallback zoom-out used `Math.max(z/1.25, 4)` — now `0.5` floor.
- Backend untouched; 42/42 tests green; build + dev green.
- Scan contract live: canonical outdoor/entrance/indoor → 200 with typed payload;
  invalid/unknown → 404 friendly message, never a crash; QR PNG 773 bytes;
  unified entrance→room handoff `outdoor_to_indoor` with 2 segments.

### Multi-building upgrade (floor-plan maps + explicit graphs + unified routing)
- Node types extended: `door`, `corridor`, `hall` (+`facility`); routing terminates at
  doors (`Room → Door → Corridor`), never bare room centers. Migration `0005`
  (+`Edge.edge_id`, `Floor.map_asset` for optional per-floor plan assets).
- Explicit indoor importer (`import_indoor_data <dir> --building-code`, dry-run):
  `nodes.csv` / `edges.csv` (+optional `floors.csv`) with collected validation
  (duplicates, unknown endpoints, self-loops, bad coords/movement), idempotent
  upsert, stale managed-edge deactivation. Legacy `import_nodes` untouched.
- Seed graphs: `data/8th_block/` (2 floors, Seminar Hall) + `data/3rd_block/`
  (3 floors, Room 340); outdoor `3RD_BLOCK` + entrance edge E16; entrances now
  bridge to `8B_F1_ENT` / `3B_F1_ENT`. `validate_graph` reports isolates/dead
  edges/bridge gaps (only known outdoor-only buildings remain).
- Unified engine: `routeType` ∈ `indoor|outdoor|outdoor_to_indoor|indoor_to_outdoor|
  multi_building` (`mode` kept as alias); segments carry `title/building/floor`;
  combined instructions gain `Exit … / Enter …` handoff lines; checkpoints carry
  segment index+title. Backend owns all orchestration (segmented legs, Dijkstra).
- Floor API: `GET /api/buildings/<code>/floors/<n>/` → `{building, floor, map:
  {asset,width,height}, nodes, edges}`; node x/y share the map coordinate space.
- Preview outdoor map restyled after classic university wayfinding maps: soft
  green ground, white building footprints with shadows (sized by category,
  selected halo), real path network drawn from `GET /api/outdoor/edges/`
  (white roads with casing), water/parking context from spaces, standalone
  facility POIs, gate markers, minimal labels, cased blue route with flow
  dashes, QR-ring current marker + red destination pin. Google map untouched.
- Frontend IndoorMap: separate plan/graph/route layers; corridor network drawn
  from edge data; POI-only normal mode (route nodes highlighted, rest dimmed);
  debug toggle (all IDs + edge distances); building•floor context chip; fit-route
  + zoom/pan/reset; optional `map_asset` image layer.
- Cross-building UX: `SegmentStepper` (INDOOR→OUTDOOR→INDOOR chips) drives
  automatic map switching; route sheet groups instructions per segment with
  per-part "View on map"; Start begins at segment 0.
- Verified live: `8B_F2_SEM → 3B_F3_R340` = multi_building
  (152m indoor + 166m outdoor + 143m indoor) with Exit/Enter lines; search
  resolves both rooms with building•floor; suite 41/41.
