# ROLE

Act as a **Senior Software Architect, Senior Full-Stack Engineer, GIS/Navigation Engineer, Database Designer, and UI/UX Engineer**.

You are responsible for designing and implementing a complete project called:

# CAMPUSNAV

CampusNav is a clean, modern **indoor navigation web application for a single campus building**.

The application must allow a user to:

1. Scan a QR code at their current location.
2. Decode and validate the QR data.
3. Set the scanned location as the current location.
4. Select a destination using a searchable dropdown/search box.
5. Manually select the starting location when a QR code is not available.
6. Calculate the shortest route between the source and destination.
7. Detect whether the route requires a floor transition.
8. If both lift and stairs are available, ask the user to choose.
9. Display the route on a clean indoor building map.
10. Display distance and estimated walking time.
11. Display step-by-step navigation.
12. Display route checkpoints/progress using a lightweight gamified experience.
13. Show obstacles/checkpoints crossed as navigation achievements.
14. Clearly show when the destination has been reached.

The first implementation is strictly for **ONE BUILDING**, but the architecture must support multiple floors within that building.

Do not unnecessarily implement multi-building, GPS, AR, Bluetooth beacons, AI navigation, or other advanced features in the first MVP.

---

# 1. REQUIRED TECHNOLOGY STACK

## Frontend

Use:

* React
* Vite
* JavaScript / JSX
* React Router when appropriate
* CSS
* Lucide React icons
* `@zxing/browser` for QR scanning

Do not use unnecessary heavy frontend libraries.

Frontend must be componentized and maintainable.

---

# 2. BACKEND

Use:

* Python
* Django
* Django REST Framework

Django is responsible for:

* database operations
* CSV import
* validation
* graph construction
* route calculation
* shortest-path algorithm
* distance calculation
* ETA calculation
* floor transitions
* lift/stair routing
* QR generation
* QR validation
* navigation instruction generation
* navigation API

Never place core routing logic inside React.

React should consume APIs and visualize the result.

---

# 3. DATABASE

Use:

* MySQL

Use Django ORM.

Database entities should include:

```text
Building
Floor
Node
Edge
QRCode
```

Use proper foreign-key relationships and indexes.

Do not store the complete navigation graph as one JSON blob.

The graph must be constructable from database Nodes and Edges.

---

# 4. CSV IS THE PRIMARY INPUT

The initial building data will be provided through a CSV file.

CSV format:

```csv
node_id,block,name,type,floor,x,y,qr_code
```

Example:

```csv
node_id,block,name,type,floor,x,y,qr_code
F1_N01,A,Main Entrance,entrance,1,10,85,CAMPUSNAV:F1_N01
F1_N02,A,Reception,amenity,1,20,85,CAMPUSNAV:F1_N02
F1_N03,A,Main Junction,junction,1,35,85,CAMPUSNAV:F1_N03
F1_N04,A,Room 101,room,1,55,85,CAMPUSNAV:F1_N04
```

Implement a robust import pipeline:

```text
CSV
 ↓
Validation
 ↓
Database
 ↓
Graph
 ↓
QR Generation
```

Create a Django management command:

```bash
python manage.py import_nodes data/building_nodes.csv
```

The importer must:

* validate column names
* validate required values
* detect duplicate node IDs
* detect duplicate QR codes
* validate coordinates
* validate floor numbers
* validate node types
* reject malformed records
* report errors clearly
* create/update nodes safely
* avoid creating duplicate records

Make the importer idempotent when possible.

---

# 5. NODE MODEL

Create a Node model with fields similar to:

```text
id
node_id
building
block
name
type
floor
x
y
qr_code
is_active
created_at
updated_at
```

Supported node types:

```text
entrance
room
junction
corridor
stair
lift
amenity
office
lab
restroom
```

Allow additional types if useful.

The `x` and `y` coordinates represent positions on the indoor floor map.

---

# 6. EDGE MODEL

The routing graph must contain explicit connections.

Create an Edge model:

```text
id
from_node
to_node
distance
accessible
movement_type
is_active
```

Movement types:

```text
walk
stairs
lift
```

Edges may be directional or bidirectional.

Design the model so bidirectional navigation is easy.

---

# 7. CSV NODE DATA → GRAPH

The CSV provides node information.

The routing system requires a graph.

Implement a graph-building service.

Example:

```text
Entrance
   |
Reception
   |
Main Junction
  / \
Room 101
Room 102
   |
Stair
   |
Floor 2
```

The graph must contain:

* node IDs
* neighboring nodes
* edge weights
* floor information
* vertical transitions
* movement types

Do not calculate routes directly from the frontend coordinates.

---

# 8. EDGE GENERATION

The application must have a clear method for creating navigation edges.

Do NOT blindly connect every node to every nearby node.

Design a reliable strategy appropriate for indoor maps.

Support either:

1. Explicit edge CSV/import later, OR
2. Controlled connection rules based on node types and coordinates.

For the initial MVP, implement the safest maintainable strategy.

For example:

```text
Entrance → Reception
Reception → Junction
Junction → Room
Junction → Stair
Junction → Lift
```

Distance can initially be calculated using coordinate distance:

```text
distance = sqrt((x2-x1)^2 + (y2-y1)^2)
```

Create a configurable scale factor so pixel/map-coordinate distance can later be converted to real metres.

Do not hard-code fake distances throughout the frontend.

---

# 9. MULTI-FLOOR SUPPORT

The building may contain multiple floors.

Represent floors independently but allow the graph to connect them.

Example:

```text
Floor 1
   |
Stair A
   |
Floor 2
```

Stair and lift connections must be represented as graph edges.

For example:

```text
F1_N09 → F2_N01
```

or equivalent records.

The routing engine must understand that:

```text
Floor 1 → Floor 2
```

is a vertical transition.

---

# 10. LIFT VS STAIRS

This is an important user interaction.

When a route requires a vertical transition and both lift and stairs are available:

Display a modal/card:

```text
Choose Your Route

┌─────────────────────┐
│      🛗 LIFT         │
│ Accessible           │
│ Comfortable          │
└─────────────────────┘

┌─────────────────────┐
│      🪜 STAIRS       │
│ Active route         │
│ May be faster        │
└─────────────────────┘
```

The user's selection must affect the backend route.

Example:

```text
GET /api/routes/?from=F1_N04&to=F2_N08&mode=lift
```

or:

```text
GET /api/routes/?from=F1_N04&to=F2_N08&mode=stairs
```

The route engine must not simply calculate one route and visually rename it.

---

# 11. ROUTING ENGINE

For MVP use:

# Dijkstra's Algorithm

Create a clean routing service.

Suggested architecture:

```text
navigation/
    routing/
        graph_service.py
        dijkstra.py
        route_engine.py
        instruction_generator.py
```

The system must calculate:

* shortest path
* total distance
* estimated walking time
* floors crossed
* vertical transitions
* movement type
* route checkpoints
* human-readable instructions

Design it so A* can replace Dijkstra later without rewriting the API.

---

# 12. ROUTE RESPONSE

The API should return structured information similar to:

```json
{
  "from": {
    "node_id": "F1_N01",
    "name": "Main Entrance",
    "floor": 1
  },
  "to": {
    "node_id": "F2_N08",
    "name": "Lab 1",
    "floor": 2
  },
  "distanceMetres": 48.5,
  "durationMinutes": 2,
  "floorsCrossed": 1,
  "verticalMode": "lift",
  "path": [
    {
      "node_id": "F1_N01",
      "name": "Main Entrance",
      "floor": 1,
      "x": 10,
      "y": 85
    }
  ],
  "instructions": [
    "Start at Main Entrance",
    "Walk towards Reception",
    "Continue to Main Junction",
    "Take the lift to Floor 2",
    "Exit the lift and continue straight",
    "Lab 1 is ahead"
  ],
  "checkpoints": []
}
```

Use a consistent API schema.

---

# 13. QR CODE GENERATION

Every node should have a unique QR payload.

Example:

```text
CAMPUSNAV:F1_N01
```

Generate QR codes using Python.

Use:

```text
qrcode
```

Create:

```text
backend/navigation/qr/generator.py
```

The backend must be able to generate a QR image for every node.

Provide an endpoint such as:

```text
GET /api/qr/F1_N01/
```

The response should provide the corresponding QR image.

Also implement a QR management/admin page if practical.

---

# 14. QR SCANNER

The frontend must contain a polished scanner UI.

Use:

```text
@zxing/browser
```

Scanner flow:

```text
Camera
 ↓
QR detected
 ↓
Decode payload
 ↓
POST /api/scan/
 ↓
Validate payload
 ↓
Find corresponding Node
 ↓
Return node information
 ↓
Set current location
```

Example payload:

```text
CAMPUSNAV:F1_N03
```

API:

```text
POST /api/scan/
```

Request:

```json
{
  "payload": "CAMPUSNAV:F1_N03"
}
```

Response:

```json
{
  "valid": true,
  "node_id": "F1_N03",
  "name": "Main Junction",
  "floor": 1
}
```

Handle invalid QR codes gracefully.

Do not crash the scanner if the QR contains invalid data.

---

# 15. LOCATION SELECTION

The user must have two options.

## Option A — QR

```text
Scan Current Location
```

After scanning:

```text
Current Location:
Main Junction
Floor 1
```

## Option B — Manual

The user can select the starting point using:

```text
Search location...
```

or a searchable dropdown.

Example:

```text
From
[ Main Entrance             ▼ ]
```

Search must work across:

* rooms
* labs
* offices
* junctions
* facilities
* stairs
* lifts
* entrances

---

# 16. DESTINATION SELECTION

Provide the same search/dropdown UX:

```text
To
[ Search destination...     ▼ ]
```

Users should be able to type:

```text
Room 101
Lab 1
Seminar Hall
Faculty Room
Lift
Reception
```

Show useful search results.

Do not display raw node IDs to normal users.

Node IDs should primarily be an internal/backend identifier.

---

# 17. NAVIGATION PAGE

Create a dedicated navigation experience.

Suggested layout:

```text
┌───────────────────────────────────────────────┐
│ CampusNav                              ⚙     │
├───────────────────────────────────────────────┤
│                                               │
│ From                                          │
│ [ Main Entrance                         ]     │
│                                               │
│ To                                            │
│ [ Lab 1                                ]      │
│                                               │
│             [ Find Route ]                    │
│                                               │
├───────────────────────────┬───────────────────┤
│                           │                   │
│       INDOOR MAP          │   ROUTE INFO      │
│                           │                   │
│                           │   48 m             │
│                           │   2 min             │
│                           │                   │
│                           │   Progress 65%     │
│                           │                   │
└───────────────────────────┴───────────────────┘
```

Responsive behavior is required.

Desktop should use a two-column layout.

Mobile should stack the map and navigation information.

---

# 18. MAP UI — IMPORTANT

The visual map experience should be inspired by the supplied **Snazzy Maps / Google Maps example**.

The desired characteristics are:

* clean
* minimal
* modern
* muted background
* simplified visual hierarchy
* reduced unnecessary labels
* strong route visibility
* simple markers
* smooth map interaction
* zoom
* pan
* current location marker
* destination marker

The provided reference is a Snazzy Maps style for Google Maps.

However:

## DO NOT treat the indoor building as a normal Google Maps road map.

Google Maps is primarily useful as the visual inspiration and, if needed later, for outdoor campus location.

For this MVP, the actual indoor navigation map must be based on the building's own floor-plan coordinates.

Implement an indoor map layer using:

* SVG, Canvas, or another appropriate custom map layer
* the `x/y` coordinates stored in the database
* floor-specific map data
* route polylines generated from backend nodes

The final experience should visually feel like a polished simplified map.

---

# 19. GOOGLE MAPS / SNAZZY MAPS STYLE

Use the supplied reference style as visual inspiration:

```javascript
styles: [
  {
    featureType: "administrative",
    stylers: [{ visibility: "off" }]
  },
  {
    featureType: "poi",
    stylers: [{ visibility: "simplified" }]
  },
  {
    featureType: "road",
    elementType: "labels",
    stylers: [{ visibility: "simplified" }]
  },
  {
    featureType: "water",
    stylers: [{ visibility: "simplified" }]
  }
]
```

The actual indoor map should NOT copy Google geographic objects because this is an indoor floor plan.

Instead, reproduce the visual principles:

```text
minimal
+
clean
+
low visual noise
+
simple geometry
+
strong route highlight
+
clear markers
```

Avoid making the map look like a cluttered CAD drawing.

---

# 20. FLOOR MAP DESIGN

Each floor must have a clean map view.

Example:

```text
                    FLOOR 1

       ┌────────────────────────────┐
       │                            │
       │   Room 101    Room 102     │
       │       ┌──────┐             │
       │       │      │             │
       │───────┼──────┼─────────────│
       │       Junction              │
       │          │                 │
       │      Reception             │
       │          │                 │
       │      Main Entrance         │
       │                            │
       └────────────────────────────┘
```

Only display important map information.

Do not show:

* database IDs
* debug coordinates
* backend metadata
* unnecessary node labels
* development information

---

# 21. MAP ROUTE VISUALIZATION

When a route exists:

```text
Current Location
      ●
      │
      │
      ╲
       ╲
        ●──────●
               │
               │
               ★ Destination
```

Highlight the calculated path clearly.

The frontend should receive the route node coordinates from the API and render the route.

The route must update when:

* source changes
* destination changes
* lift/stairs mode changes
* floor changes

---

# 22. FLOOR SWITCHER

Provide a minimal floor control:

```text
┌─────┬─────┬─────┐
│ F1  │ F2  │ F3  │
└─────┴─────┴─────┘
```

Or:

```text
Floor
[ 1 ▼ ]
```

Use whichever creates the cleaner UX.

When a route spans multiple floors, make the active floor obvious.

---

# 23. NAVIGATION INSTRUCTIONS

Convert graph information into human-friendly instructions.

Do not display:

```text
F1_N03 → F1_N06 → F1_N09
```

Display:

```text
1. Continue to the main junction
2. Walk along the corridor
3. Take the stairs to Floor 2
4. Continue straight
5. Destination is on your right
```

Instruction generation belongs in the backend.

Create:

```text
instruction_generator.py
```

Use node types and route geometry to create meaningful instructions.

---

# 24. DISTANCE AND ETA

Display:

```text
48 m
2 min
```

Distance comes from the routing engine.

ETA should be calculated from a configurable walking speed.

Example:

```text
walking_speed = configurable
```

Do not hard-code the final UI to one fake distance.

---

# 25. GAMIFIED NAVIGATION

This is an important part of CampusNav.

The navigation experience should feel slightly like a game without becoming childish.

Create a clean progress component.

Example:

```text
Navigation Progress

██████████████░░░░ 72%

36m completed / 50m

✓ Started
✓ Reception
✓ Junction
✓ Lift
→ Floor 2 Junction
○ Destination
```

The system should track:

* route progress
* checkpoints reached
* distance completed
* distance remaining
* floors crossed
* obstacles/checkpoints crossed

---

# 26. CHECKPOINT / ACHIEVEMENT SYSTEM

Important nodes can become navigation checkpoints.

Examples:

```text
✓ Main Entrance
✓ Reception
✓ Main Junction
✓ Lift
→ Floor 2 Junction
○ Destination
```

Use subtle achievement feedback.

Examples:

```text
Checkpoint reached
+10 Navigation XP
```

or:

```text
🏆 Floor transition completed
```

Do not make the UI childish.

The visual language should remain similar to a modern navigation application.

---

# 27. DESTINATION REACHED

When the user reaches the final checkpoint:

Display:

```text
Destination Reached 🎯

Lab 1

Route completed
48 m walked
2 min navigation

🏆 Navigation Complete
```

Use a subtle success animation.

---

# 28. STITCH MCP

You are explicitly allowed to use **Stitch MCP** for UI/UX generation and refinement.

Use Stitch MCP to help design:

* dashboard/home screen
* QR scanner screen
* location search UI
* destination selection
* navigation screen
* lift/stairs selection modal
* map panel
* navigation progress panel
* achievement/checkpoint components
* responsive mobile layout

The UI should have a consistent design system.

Before generating many screens, establish:

```text
Typography
Spacing
Border radius
Cards
Buttons
Inputs
Icons
Map controls
Modal design
Status indicators
```

Do not generate disconnected screens with inconsistent styles.

Use Stitch MCP as a design accelerator, but ensure the final UI is correctly implemented in React.

---

# 29. UI DESIGN DIRECTION

The interface should feel like:

```text
Google Maps
+
Apple Maps
+
modern SaaS dashboard
+
minimal campus navigation
```

Design principles:

* clean
* premium
* minimal
* professional
* responsive
* accessible
* fast
* low visual noise

Avoid:

* excessive cards
* giant titles
* unnecessary statistics
* fake sample data
* excessive gradients
* excessive animations
* cluttered dashboards
* random decorative elements
* unnecessary icons
* raw database information

The map must remain the visual focus.

---

# 30. FRONTEND COMPONENT STRUCTURE

Use a clean structure similar to:

```text
frontend/
└── src/
    ├── components/
    │   ├── Header.jsx
    │   ├── Scanner.jsx
    │   ├── LocationSelector.jsx
    │   ├── DestinationSelector.jsx
    │   ├── RouteInfo.jsx
    │   ├── NavigationMap.jsx
    │   ├── FloorSelector.jsx
    │   ├── RouteSteps.jsx
    │   ├── ProgressCard.jsx
    │   ├── CheckpointList.jsx
    │   └── LiftStairModal.jsx
    │
    ├── pages/
    │   ├── Home.jsx
    │   ├── Navigation.jsx
    │   └── ScannerPage.jsx
    │
    ├── services/
    │   └── api.js
    │
    ├── maps/
    │   └── building-map.svg
    │
    ├── hooks/
    │   └── useNavigation.js
    │
    ├── utils/
    │   └── navigation.js
    │
    └── styles/
        ├── global.css
        └── theme.css
```

Adapt this structure when necessary, but maintain clear separation of concerns.

---

# 31. BACKEND STRUCTURE

Use a maintainable Django structure similar to:

```text
backend/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
└── navigation/
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    │
    ├── services/
    │   ├── graph_service.py
    │   ├── route_service.py
    │   └── navigation_service.py
    │
    ├── routing/
    │   ├── dijkstra.py
    │   ├── route_engine.py
    │   └── instruction_generator.py
    │
    ├── qr/
    │   ├── generator.py
    │   └── validator.py
    │
    ├── importer/
    │   ├── csv_parser.py
    │   └── validator.py
    │
    └── management/
        └── commands/
            └── import_nodes.py
```

Do not put the entire project into `views.py`.

---

# 32. API DESIGN

Implement at minimum:

```text
GET  /api/building/
GET  /api/floors/
GET  /api/nodes/
GET  /api/nodes/<node_id>/

POST /api/scan/

GET  /api/routes/

GET  /api/qr/<node_id>/
```

Route example:

```text
/api/routes/?from=F1_N01&to=F2_N05&mode=lift
```

Keep API responses predictable and documented.

---

# 33. ERROR HANDLING

Implement proper error states.

Examples:

```text
Invalid QR code
Location not found
Destination not found
No route available
No lift route available
No stairs route available
Invalid source/destination
Server error
Camera permission denied
```

Use clear user-friendly messages.

Never expose Python stack traces or database errors to users.

---

# 34. ADMIN

Use Django Admin for MVP data management.

Admin should allow management of:

```text
Buildings
Floors
Nodes
Edges
QR Codes
```

Make the admin usable.

Use search/filter capabilities for nodes.

---

# 35. SECURITY

Implement basic security best practices:

* environment variables for secrets
* never commit MySQL passwords
* validate API input
* validate QR payloads
* restrict dangerous file uploads
* use Django CSRF/CORS correctly
* avoid SQL injection by using Django ORM
* validate CSV uploads
* do not trust frontend node IDs without backend validation

Create:

```text
.env.example
```

with placeholders.

---

# 36. CONFIGURATION

Use environment variables for:

```text
MYSQL_DATABASE
MYSQL_USER
MYSQL_PASSWORD
MYSQL_HOST
MYSQL_PORT
DJANGO_SECRET_KEY
DJANGO_DEBUG
```

For frontend:

```text
VITE_API_BASE_URL
```

Do not hard-code deployment-specific URLs.

---

# 37. DATA DIRECTORY

Create:

```text
data/
    building_nodes.csv
```

The application should be immediately testable with synthetic data.

---

# 38. DEVELOPMENT SEQUENCE

Do NOT try to generate the entire application randomly in one pass.

Work through these milestones.

## Milestone 1 — Foundation

Create:

```text
Django project
React + Vite project
MySQL connection
Environment configuration
Git-friendly folder structure
```

Verify that backend and frontend run.

---

## Milestone 2 — Database

Implement:

```text
Building
Floor
Node
Edge
QRCode
```

Run migrations.

Verify Django Admin.

---

## Milestone 3 — CSV Import

Implement:

```text
import_nodes
```

Load:

```text
data/building_nodes.csv
```

Verify nodes in MySQL.

---

## Milestone 4 — Graph

Implement:

```text
GraphService
Dijkstra
Edge weights
Floor connections
Lift/stair modes
```

Write tests for route calculations.

---

## Milestone 5 — QR

Implement:

```text
QR generation
QR API
QR validation
POST /api/scan/
```

Test valid and invalid QR values.

---

## Milestone 6 — Frontend Scanner

Implement:

```text
Scanner UI
Camera
QR decoding
Current location
```

---

## Milestone 7 — Search

Implement:

```text
From selector
Destination selector
Search
Dropdown
```

---

## Milestone 8 — Navigation

Implement:

```text
Route API integration
Lift/stairs modal
Distance
ETA
Instructions
```

---

## Milestone 9 — Indoor Map

Implement:

```text
Floor map
Node positions
Route polyline
Current location
Destination
Floor switching
```

The map must remain clean.

---

## Milestone 10 — Gamification

Implement:

```text
Progress
Checkpoints
Distance completed
Floors crossed
Achievements
Destination reached
```

---

## Milestone 11 — UI Polish

Use Stitch MCP where useful.

Improve:

```text
spacing
typography
animations
responsive design
map controls
loading states
empty states
errors
```

---

# 39. TESTING REQUIREMENTS

Write tests for backend functionality.

At minimum test:

### CSV

```text
valid CSV
invalid CSV
duplicate IDs
invalid floor
invalid node type
```

### QR

```text
valid QR
invalid QR
unknown QR
```

### Routing

```text
same-floor route
multi-floor route
lift route
stair route
no-route condition
```

### API

```text
nodes API
scan API
route API
QR API
```

### Frontend

Verify:

```text
scanner works
manual source works
destination search works
route loads
floor switching works
lift/stairs choice works
route appears correctly
errors display correctly
```

---

# 40. IMPORTANT ENGINEERING RULES

Follow these rules throughout the project:

1. Do not hard-code navigation routes in React.
2. Do not hard-code fake route results.
3. Do not put database logic inside UI components.
4. Do not put Dijkstra logic inside React.
5. Do not expose raw database IDs unnecessarily.
6. Do not create giant monolithic files.
7. Do not duplicate business logic.
8. Do not create unnecessary dependencies.
9. Do not generate fake dashboards with irrelevant metrics.
10. Do not fill the interface with sample data that users did not ask for.
11. Keep API contracts explicit.
12. Use reusable components.
13. Use meaningful names.
14. Add comments only where they clarify non-obvious logic.
15. Keep the visual design consistent.
16. Make the application responsive.
17. Make loading/error/empty states polished.
18. Do not break existing functionality when adding features.
19. Run tests after major backend changes.
20. Fix errors rather than hiding them.

---

# 41. MAP ARCHITECTURE RULE

Use this architecture:

```text
MySQL
 ↓
Django Nodes + Edges
 ↓
Graph
 ↓
Dijkstra
 ↓
Route JSON
 ↓
React
 ↓
Indoor Map Renderer
 ↓
Route Visualization
```

The building's floor map is a **visual layer**.

The navigation graph is the **logical layer**.

Keep these two concepts separate.

For example:

```text
MAP LAYER
SVG / Canvas / floor plan
        +
GRAPH LAYER
Nodes / Edges / Routing
```

Do not use visual proximity alone as the routing engine.

---

# 42. FUTURE-READY ARCHITECTURE

Do not implement these now, but structure the code so they can be added later:

```text
A* routing
GPS outdoor navigation
multi-building navigation
Bluetooth beacons
real-time positioning
AR navigation
voice navigation
wheelchair routing
crowd-aware routing
emergency evacuation routing
offline navigation
AI navigation assistant
```

Do not let future features complicate the MVP.

---

# 43. INITIAL PROJECT SUCCESS CRITERIA

The project is considered complete when the following end-to-end flow works:

```text
1. Start Django
2. Start React
3. Connect to MySQL
4. Import building CSV
5. Nodes appear in database
6. QR codes are generated
7. User opens CampusNav
8. User scans QR
9. QR is decoded
10. Current location is detected
11. User searches destination
12. Destination is selected
13. Backend calculates shortest route
14. If necessary, lift/stairs choice appears
15. Route is recalculated according to selection
16. Clean indoor map is displayed
17. Route is highlighted
18. Distance is displayed
19. ETA is displayed
20. Instructions are displayed
21. Checkpoints are displayed
22. Navigation progress is displayed
23. Floor transitions are shown
24. Destination completion is displayed
```

---

# 44. FIRST TASK

Do not immediately generate every file.

First:

1. Analyze the complete requirements.
2. Establish the architecture.
3. Create the folder structure.
4. Create the Django backend.
5. Create the React frontend.
6. Configure MySQL.
7. Create the initial models.
8. Create the initial API structure.
9. Create the initial frontend shell.
10. Run/validate the project.

Then continue milestone-by-milestone.

At each milestone:

* implement
* test
* fix errors
* verify integration
* then proceed

Do not leave broken placeholder code behind.

---

# 45. FINAL UI GOAL

The finished MVP should feel like a real navigation product, not a college-project CRUD dashboard.

The home/navigation experience should be visually centered around:

```text
             CampusNav

       Where are you going?

   From
   [ Scan QR / Search location ]

   To
   [ Search destination ]

        [ Find Route ]

────────────────────────────────────

              MAP

        clean indoor floorplan
        route highlighted

────────────────────────────────────

       48 m       2 min

       Navigation Progress
       ███████████░░ 72%

       ✓ Reception
       ✓ Junction
       → Lift
       ○ Room 205
```

The design must prioritize:

**clarity → map → route → navigation instructions → progress**

not unnecessary dashboard information.

---

# 46. DELIVERABLES

Produce a fully working project with:

```text
✓ React frontend
✓ Django backend
✓ MySQL database
✓ CSV importer
✓ Node management
✓ Edge management
✓ Navigation graph
✓ Dijkstra routing
✓ Multi-floor routing
✓ Lift/stair selection
✓ QR generation
✓ QR scanning
✓ QR validation
✓ Location selection
✓ Destination search
✓ Route API
✓ Indoor map
✓ Floor switching
✓ Distance
✓ ETA
✓ Step-by-step instructions
✓ Navigation progress
✓ Checkpoints
✓ Gamified achievements
✓ Django Admin
✓ Error handling
✓ Tests
✓ .env.example
✓ README.md
```

The README must document:

* project overview
* architecture
* technology stack
* database schema
* CSV format
* graph architecture
* Dijkstra algorithm
* QR workflow
* API endpoints
* frontend architecture
* setup instructions
* MySQL configuration
* running locally
* importing CSV
* generating QR codes
* testing
* deployment preparation

Start by implementing **Milestone 1**, then proceed through the milestones systematically.
