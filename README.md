# NavixAI — Intelligent Indoor Campus Navigation

A clean, modern **indoor navigation web application** for campus buildings. NavixAI provides QR-based positioning, multi-floor shortest-path routing (Dijkstra's algorithm) with lift vs. stairs preferences, interactive SVG floor plans, turn-by-turn directions, and a gamified checkpoint experience.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Database Schema](#database-schema)
- [CSV Data Format](#csv-data-format)
- [Graph & Dijkstra Routing](#graph--dijkstra-routing)
- [QR Workflow](#qr-workflow)
- [API Endpoints](#api-endpoints)
- [Frontend Architecture](#frontend-architecture)
- [Setup Instructions](#setup-instructions)
- [Running Locally](#running-locally)
- [Importing CSV Data](#importing-csv-data)
- [Generating QR Codes](#generating-qr-codes)
- [Running Tests](#running-tests)
- [Deployment Preparation](#deployment-preparation)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    USER / BROWSER                    │
│                                                     │
│  React + Vite Frontend (port 5173)                  │
│  ├── Interactive SVG Indoor Map (zoom/pan)           │
│  ├── ZXing QR Camera Scanner                        │
│  ├── Location & Destination Search                   │
│  ├── Lift vs Stairs Selection Modal                  │
│  ├── Turn-by-Turn Navigation Steps                   │
│  └── Gamified Progress & Achievement Toasts          │
│                                                     │
│               ▼ REST API (fetch) ▼                   │
│                                                     │
│  Django REST Framework Backend (port 8000)           │
│  ├── /api/building/     - Building info              │
│  ├── /api/floors/       - Floor listing              │
│  ├── /api/nodes/        - Node listing + search      │
│  ├── /api/scan/         - QR validation              │
│  ├── /api/routes/       - Dijkstra routing           │
│  └── /api/qr/<node_id>/ - QR image generation        │
│                                                     │
│  Navigation Engine                                   │
│  ├── GraphService   → builds in-memory graph         │
│  ├── DijkstraRouter → shortest-path with mode filter │
│  ├── RouteEngine    → ETA, checkpoints, transitions  │
│  └── InstructionGen → human-readable directions      │
│                                                     │
│               ▼ Django ORM ▼                         │
│                                                     │
│  Database (SQLite dev / MySQL production)             │
│  ├── Building, Floor, Node, Edge, QRCode models      │
│  └── 34 nodes, 94 edges, 3 floors                    │
└─────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Frontend   | React 19, Vite 8, JavaScript/JSX                  |
| Icons      | Lucide React                                      |
| QR Scanner | @zxing/browser                                    |
| Styling    | Vanilla CSS (design tokens, Snazzy Maps aesthetic) |
| Backend    | Python 3, Django 5.2, Django REST Framework        |
| Database   | MySQL (production) / SQLite (development)          |
| QR Gen     | Python `qrcode` library                           |
| Routing    | Dijkstra's Algorithm (custom implementation)       |

---

## Database Schema

```
Building
├── id (BigAutoField)
├── name (CharField)
├── code (CharField, unique)
├── description (TextField)
├── created_at, updated_at

Floor
├── id (BigAutoField)
├── building (FK → Building)
├── floor_number (IntegerField)
├── name (CharField)
├── map_width, map_height (FloatField)
├── created_at, updated_at
└── unique_together: (building, floor_number)

Node
├── id (BigAutoField)
├── node_id (CharField, unique, indexed)
├── building (FK → Building)
├── block (CharField)
├── name (CharField)
├── type (CharField: entrance/room/junction/corridor/stair/lift/amenity/office/lab/restroom)
├── floor (FK → Floor)
├── x, y (FloatField — floor plan coordinates)
├── qr_code (CharField, unique, indexed)
├── is_active, is_checkpoint (BooleanField)
├── created_at, updated_at

Edge
├── id (BigAutoField)
├── from_node (FK → Node)
├── to_node (FK → Node)
├── distance (FloatField — metres)
├── accessible (BooleanField — wheelchair accessible)
├── movement_type (CharField: walk/stairs/lift)
├── is_active (BooleanField)
├── created_at
└── unique_together: (from_node, to_node, movement_type)

QRCode
├── id (BigAutoField)
├── node (OneToOneField → Node)
├── payload (CharField, unique)
├── image_path (CharField)
├── created_at
```

---

## CSV Data Format

```csv
node_id,block,name,type,floor,x,y,qr_code
F1_N01,1,Main Entrance,entrance,1,10,85,CAMPUSNAV:F1_N01
F1_N02,1,Reception,amenity,1,20,85,CAMPUSNAV:F1_N02
F1_N03,1,Main Junction,junction,1,35,85,CAMPUSNAV:F1_N03
```

| Column    | Description                              |
|-----------|------------------------------------------|
| node_id   | Unique identifier (e.g. F1_N01)          |
| block     | Building block/section                   |
| name      | Human-readable name                      |
| type      | entrance/room/junction/stair/lift/amenity/etc |
| floor     | Floor number (positive integer)          |
| x, y      | Coordinates on the floor plan (0-100)    |
| qr_code   | QR payload string                        |

---

## Graph & Dijkstra Routing

The routing system uses a **logical graph layer** separate from the **visual map layer**:

```
MySQL/SQLite  →  Django Nodes + Edges  →  In-Memory Graph  →  Dijkstra  →  Route JSON  →  React Map
```

### Graph Construction
- Nodes and Edges are loaded from the database into an adjacency list
- Intra-floor edges connect rooms, junctions, corridors with `movement_type='walk'`
- Inter-floor edges connect Staircase A nodes with `movement_type='stairs'` and Lift A nodes with `movement_type='lift'`

### Dijkstra with Mode Filtering
- `mode='any'` — uses all edges (fastest route regardless of stairs/lift)
- `mode='lift'` — excludes stairs edges (forces lift transitions)
- `mode='stairs'` — excludes lift edges (forces staircase transitions)

### Route Response
The route engine returns:
- Ordered path with coordinates for map polyline rendering
- Total distance (metres), estimated walking time (minutes)
- Floors crossed, vertical mode used
- Whether both lift and stairs options are available
- Human-readable step-by-step instructions
- Checkpoint timeline for gamified progress tracking

---

## QR Workflow

```
Physical QR Code  →  Camera Scan (@zxing/browser)  →  Decode "CAMPUSNAV:F1_N01"
                                                         ↓
                                           POST /api/scan/ { "payload": "CAMPUSNAV:F1_N01" }
                                                         ↓
                                           Backend validates → returns Node info
                                                         ↓
                                           Frontend sets current location → auto-route
```

Supported payload formats:
- `CAMPUSNAV:<node_id>` (standard)
- `NAVIXAI:<node_id>` (alternative)
- Raw `<node_id>` (fallback)

---

## API Endpoints

| Method | Endpoint                 | Description                                      |
|--------|--------------------------|--------------------------------------------------|
| GET    | `/api/building/`         | List buildings with nested floors                |
| GET    | `/api/floors/`           | List all floors                                  |
| GET    | `/api/nodes/`            | List active nodes (filter: `?floor=1&type=room&q=lab`) |
| GET    | `/api/nodes/<node_id>/`  | Single node detail                               |
| POST   | `/api/scan/`             | Validate QR payload, return node info            |
| GET    | `/api/routes/`           | Calculate route: `?from=F1_N01&to=F2_N08&mode=lift` |
| GET    | `/api/qr/<node_id>/`     | Serve QR code PNG image                          |

### Route API Example

**Request:** `GET /api/routes/?from=F1_N01&to=F2_N08&mode=lift`

**Response:**
```json
{
  "success": true,
  "from": { "node_id": "F1_N01", "name": "Main Entrance", "floor": 1 },
  "to": { "node_id": "F2_N08", "name": "Lab 1", "floor": 2 },
  "distanceMetres": 225.5,
  "durationMinutes": 4,
  "floorsCrossed": 1,
  "verticalMode": "lift",
  "liftStairChoiceAvailable": true,
  "path": [ ... ],
  "instructions": [
    "Start at Main Entrance (Floor 1)",
    "Continue past Reception",
    "Continue straight through Main Junction",
    "Take Lift A up to Floor 2",
    "Arrive at destination: Lab 1"
  ],
  "checkpoints": [ ... ]
}
```

---

## Frontend Architecture

```
frontend/src/
├── main.jsx                          # Entry point, imports global CSS
├── App.jsx                           # Root → NavigationPage
├── styles/
│   ├── global.css                    # Design tokens, keyframe animations
│   ├── components.css                # Layout, sidebar, modals, cards
│   └── map.css                       # SVG map, markers, route polylines
├── services/
│   └── api.js                        # REST API client (fetch wrapper)
├── components/
│   ├── Header.jsx                    # Brand header + Scan Location button
│   ├── Scanner.jsx                   # ZXing camera + test simulator
│   ├── LocationSelector.jsx          # Searchable "From" dropdown
│   ├── DestinationSelector.jsx       # Searchable "To" dropdown
│   ├── NavigationMap.jsx             # Interactive SVG map (zoom/pan/markers/route)
│   ├── RouteSteps.jsx                # Distance/ETA stats + turn-by-turn steps
│   ├── ProgressCard.jsx              # Gamified checkpoint progress tracker
│   ├── LiftStairModal.jsx            # Lift vs Stairs selection modal
│   └── AchievementModal.jsx          # "Destination Reached" celebration
└── pages/
    └── NavigationPage.jsx            # Main orchestrator page
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+ with pip
- Node.js 18+ with npm
- MySQL 8+ (optional — defaults to SQLite for development)

### 1. Clone and configure environment

```bash
cd NavixAI
cp .env.example .env
# Edit .env if needed (DB_ENGINE=sqlite works out of the box)
```

### 2. Install backend dependencies

```bash
pip install django djangorestframework django-cors-headers python-dotenv pymysql qrcode pillow
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Setup database and import data

```bash
cd backend
python manage.py migrate
python manage.py import_nodes ../data/building_nodes.csv
python manage.py generate_qrcodes
python manage.py createsuperuser  # Optional: for Django Admin access
```

---

## Running Locally

**Start backend** (terminal 1):
```bash
cd backend
python manage.py runserver
```
Backend runs at: `http://127.0.0.1:8000`

**Start frontend** (terminal 2):
```bash
cd frontend
npm run dev
```
Frontend runs at: `http://127.0.0.1:5173`

The Vite dev server proxies `/api/*` requests to the Django backend automatically.

**Django Admin:** `http://127.0.0.1:8000/admin/`

---

## Importing CSV Data

```bash
cd backend
python manage.py import_nodes ../data/building_nodes.csv
```

Options:
```bash
python manage.py import_nodes path/to/data.csv --building-code MAIN --building-name "My Building"
```

The importer:
- Validates all CSV rows (headers, types, coordinates, duplicates)
- Creates Building and Floor records automatically
- Creates/updates Node records (idempotent)
- Generates topological edges (walk, stairs, lift)
- Reports detailed results

---

## Generating QR Codes

```bash
cd backend
python manage.py generate_qrcodes
```

PNG files are saved to `qr_codes/` directory (one per node).

QR images are also served dynamically via: `GET /api/qr/<node_id>/`

---

## Running Tests

```bash
cd backend
python manage.py test navigation -v 2
```

Test coverage:
- **CSV Validation:** valid rows, duplicate node_id, invalid floor, invalid type
- **QR Validation:** valid CAMPUSNAV payload, NAVIXAI fallback, unknown codes
- **Routing:** same-floor route, multi-floor via lift, multi-floor via stairs
- **API Endpoints:** nodes list, QR scan, route calculation, QR image generation

---

## Deployment Preparation

1. Set `DB_ENGINE=mysql` in `.env` and configure MySQL credentials
2. Set `DJANGO_DEBUG=False` and generate a strong `DJANGO_SECRET_KEY`
3. Run `python manage.py collectstatic`
4. Build frontend production bundle: `cd frontend && npm run build`
5. Serve `frontend/dist/` with nginx or similar
6. Run Django with gunicorn behind nginx

---

## Project Structure

```
NavixAI/
├── backend/
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py       # Django settings with env vars
│   │   ├── urls.py           # Root URL → /api/ + /admin/
│   │   └── __init__.py       # PyMySQL init
│   └── navigation/
│       ├── models.py          # Building, Floor, Node, Edge, QRCode
│       ├── serializers.py     # DRF serializers
│       ├── views.py           # API views
│       ├── urls.py            # API URL routing
│       ├── admin.py           # Django Admin config
│       ├── tests.py           # 12 automated tests
│       ├── routing/
│       │   ├── graph.py           # NavigationGraph + GraphService
│       │   ├── dijkstra.py        # Dijkstra shortest-path
│       │   ├── route_engine.py    # RouteEngine orchestrator
│       │   └── instruction_generator.py  # Turn-by-turn text
│       ├── qr/
│       │   ├── generator.py       # QR PNG generation
│       │   └── validator.py       # Payload decode + validate
│       ├── importer/
│       │   ├── csv_parser.py      # CSV ingestion + edge generation
│       │   └── validator.py       # Row-level validation
│       └── management/commands/
│           ├── import_nodes.py    # CSV import command
│           └── generate_qrcodes.py # QR batch generator
├── frontend/
│   ├── package.json
│   ├── vite.config.js         # Dev proxy to backend
│   ├── index.html             # SEO meta, Google Fonts
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── services/api.js
│       ├── styles/ (global.css, components.css, map.css)
│       ├── components/ (Header, Scanner, LocationSelector, DestinationSelector,
│       │                NavigationMap, RouteSteps, ProgressCard,
│       │                LiftStairModal, AchievementModal)
│       └── pages/NavigationPage.jsx
├── data/
│   └── building_nodes.csv     # Synthetic test data (34 nodes, 3 floors)
├── qr_codes/                  # Generated QR PNG images (34 files)
├── .env                       # Local environment config
├── .env.example               # Template for environment config
└── README.md
```

---

*Built with NavixAI — Intelligent Indoor Campus Navigation*
