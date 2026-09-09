# NavixAI — Implementation Walkthrough

## What Was Built

A complete, working **indoor campus navigation web application** with:
- **Django REST Framework backend** (Python) — routing engine, QR validation, CSV import, REST API
- **React + Vite frontend** (JavaScript) — interactive SVG map, QR scanner, gamified progress
- **SQLite database** (with MySQL-ready config) — 34 nodes, 94 edges, 3 floors

---

## Backend (Milestones 1–5) — All Complete ✅

### Models & Database
| File | Purpose |
|------|---------|
| [models.py](file:///e:/projects/NavixAI/backend/navigation/models.py) | Building, Floor, Node, Edge, QRCode with FK relationships and indexes |
| [admin.py](file:///e:/projects/NavixAI/backend/navigation/admin.py) | Django Admin with search/filter for all entities |

### CSV Import Pipeline
| File | Purpose |
|------|---------|
| [csv_parser.py](file:///e:/projects/NavixAI/backend/navigation/importer/csv_parser.py) | Parses CSV, creates nodes, auto-generates topological edges (walk + stairs + lift) |
| [validator.py](file:///e:/projects/NavixAI/backend/navigation/importer/validator.py) | Validates headers, types, coordinates, detects duplicates |
| [import_nodes.py](file:///e:/projects/NavixAI/backend/navigation/management/commands/import_nodes.py) | `python manage.py import_nodes data/building_nodes.csv` — idempotent |

### Dijkstra Routing Engine
| File | Purpose |
|------|---------|
| [graph.py](file:///e:/projects/NavixAI/backend/navigation/routing/graph.py) | Builds NavigationGraph from DB with adjacency lists |
| [dijkstra.py](file:///e:/projects/NavixAI/backend/navigation/routing/dijkstra.py) | Shortest-path with mode filtering (lift/stairs/any) |
| [route_engine.py](file:///e:/projects/NavixAI/backend/navigation/routing/route_engine.py) | Orchestrates route calc: distance, ETA, checkpoints, floor transitions, lift/stair availability |
| [instruction_generator.py](file:///e:/projects/NavixAI/backend/navigation/routing/instruction_generator.py) | Human-readable turn-by-turn directions |

### QR Generation & Validation
| File | Purpose |
|------|---------|
| [generator.py](file:///e:/projects/NavixAI/backend/navigation/qr/generator.py) | Generates QR PNG images using `qrcode` library |
| [validator.py](file:///e:/projects/NavixAI/backend/navigation/qr/validator.py) | Validates CAMPUSNAV/NAVIXAI payload formats |
| [generate_qrcodes.py](file:///e:/projects/NavixAI/backend/navigation/management/commands/generate_qrcodes.py) | Batch generates 34 QR PNGs |

### REST API
| File | Purpose |
|------|---------|
| [views.py](file:///e:/projects/NavixAI/backend/navigation/views.py) | 7 API endpoints: building, floors, nodes, node detail, scan, routes, QR image |
| [serializers.py](file:///e:/projects/NavixAI/backend/navigation/serializers.py) | DRF serializers for all models |
| [urls.py](file:///e:/projects/NavixAI/backend/navigation/urls.py) | URL routing under `/api/` |

---

## Frontend (Milestones 6–10) — All Complete ✅

### Core Components
| Component | Purpose |
|-----------|---------|
| [NavigationPage.jsx](file:///e:/projects/NavixAI/frontend/src/pages/NavigationPage.jsx) | Main orchestrator: state management, route calc, modals, toasts |
| [Header.jsx](file:///e:/projects/NavixAI/frontend/src/components/Header.jsx) | NavixAI branding + "Scan Location" button |
| [Scanner.jsx](file:///e:/projects/NavixAI/frontend/src/components/Scanner.jsx) | ZXing camera QR scanner + test simulator dropdown |
| [LocationSelector.jsx](file:///e:/projects/NavixAI/frontend/src/components/LocationSelector.jsx) | Searchable "From" dropdown with QR shortcut |
| [DestinationSelector.jsx](file:///e:/projects/NavixAI/frontend/src/components/DestinationSelector.jsx) | Searchable "To" dropdown with filtering |
| [NavigationMap.jsx](file:///e:/projects/NavixAI/frontend/src/components/NavigationMap.jsx) | Interactive SVG map: zoom/pan/markers/animated route polyline/floor switcher |
| [RouteSteps.jsx](file:///e:/projects/NavixAI/frontend/src/components/RouteSteps.jsx) | Distance/ETA stats + numbered step-by-step directions |
| [ProgressCard.jsx](file:///e:/projects/NavixAI/frontend/src/components/ProgressCard.jsx) | Gamified checkpoint progress: bar, timeline, "Simulate Step" |
| [LiftStairModal.jsx](file:///e:/projects/NavixAI/frontend/src/components/LiftStairModal.jsx) | Lift vs Stairs choice cards with recalculation |
| [AchievementModal.jsx](file:///e:/projects/NavixAI/frontend/src/components/AchievementModal.jsx) | "Destination Reached 🎯" celebration with XP and stats |

### Styling
| File | Purpose |
|------|---------|
| [global.css](file:///e:/projects/NavixAI/frontend/src/styles/global.css) | Design tokens (colors, shadows, radii), keyframe animations |
| [components.css](file:///e:/projects/NavixAI/frontend/src/styles/components.css) | Layout, sidebar, search fields, modals, progress cards |
| [map.css](file:///e:/projects/NavixAI/frontend/src/styles/map.css) | SVG floor plan, route polylines, markers, tooltips |

---

## Testing & Verification — All Pass ✅

### Automated Tests (12/12 passing)
```
test_duplicate_node_id_rejected ... ok
test_invalid_floor_rejected ... ok
test_invalid_node_type_rejected ... ok
test_valid_csv_rows ... ok
test_api_nodes_endpoint ... ok
test_api_qr_image_endpoint ... ok
test_api_routes_endpoint ... ok
test_api_scan_endpoint ... ok
test_multi_floor_lift_mode ... ok
test_multi_floor_stairs_mode ... ok
test_qr_validation ... ok
test_same_floor_route ... ok
```

### Live API Verification
- `GET /api/nodes/?floor=1` → 12 nodes returned ✅
- `POST /api/scan/` with `CAMPUSNAV:F1_N01` → Valid, Main Entrance ✅
- `GET /api/routes/?from=F1_N01&to=F2_N08&mode=lift` → 225.5m, 12 path nodes via Lift A ✅
- `GET /api/routes/?from=F1_N01&to=F3_N09&mode=stairs` → 174m, 3-floor route via Staircase A ✅
- Frontend build (`npm run build`) → Successful ✅

### Running Servers
- Backend: `http://127.0.0.1:8000` (Django) — Running ✅
- Frontend: `http://127.0.0.1:5173` (Vite) — Running ✅

---

## Key Design Decisions

1. **Graph ≠ Map** — The logical routing graph (Dijkstra) is kept entirely separate from the visual SVG map. Routes are computed from DB edges, not pixel proximity.

2. **Mode filtering in Dijkstra** — Rather than computing one route and relabeling, the router genuinely excludes lift or stairs edges during graph traversal, producing legitimately different paths.

3. **Idempotent imports** — Running `import_nodes` twice creates 0 new nodes, only updates — safe for development iteration.

4. **SQLite default** — `DB_ENGINE=sqlite` enables zero-config local development. Switch to `DB_ENGINE=mysql` for production.

5. **Checkpoint gamification** — Important nodes (entrances, junctions, lifts, stairs) are auto-marked as checkpoints during import. The "Simulate Step" button lets users walk through checkpoints to test the gamified experience without a physical QR scanner.
