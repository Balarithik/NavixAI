import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, MapPin, Navigation, ArrowUpDown, Footprints, Layers, Bug, Maximize } from 'lucide-react';

/**
 * IndoorMap — architectural floor-plan renderer + navigation-graph overlay.
 *
 * Layers (kept separate):
 *   1. Floor-plan visual layer: optional map asset image, else a procedural
 *      architectural backdrop (room blocks, corridor network from edge data).
 *   2. Navigation graph layer: nodes/edges from backend (dynamic, never hard-coded).
 *   3. Route overlay: highlighted path + current/destination markers.
 *
 * Normal mode shows POIs only (rooms, halls, lifts, stairs, entrances,
 * destination). Debug mode ("Show graph") reveals every node id + edge.
 */
const POI_TYPES = new Set([
  'room', 'hall', 'lab', 'office', 'amenity', 'restroom', 'facility',
  'lift', 'stair', 'entrance',
]);
const WALKWAY_TYPES = new Set(['corridor', 'junction', 'door', 'stair', 'lift', 'entrance']);

const ROOM_FILL = {
  lift: '#F5F3FF',
  stair: '#FFFBEB',
  amenity: '#F0FDF4',
  restroom: '#F0FDFA',
  hall: '#EFF6FF',
  lab: '#FDF4FF',
  default: '#F8FAFC',
};

export default function NavigationMap({
  floors = [],
  activeFloor = 1,
  onChangeFloor,
  nodes = [],
  edges = [],
  route = null,
  startNode = null,
  destinationNode = null,
  onNodeClick,
  currentStepIndex = 0,
  buildingName = null,
  floorName = null,
  mapAsset = null,
  mapWidth = 100,
  mapHeight = 100,
  debugDefault = false,
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [debugGraph, setDebugGraph] = useState(debugDefault);
  // Camera window in SVG units; null = full floor.
  const [view, setView] = useState(null);
  const containerRef = useRef(null);

  const W = Number(mapWidth) || 100;
  const H = Number(mapHeight) || 100;
  const baseView = useMemo(
    () => ({ x: -5, y: -5, w: W + 10, h: H + 10 }),
    [W, H],
  );

  // Filter nodes for active floor
  const floorNodes = nodes.filter((n) => Number(n.floor_number || n.floor) === Number(activeFloor));
  const nodeById = useMemo(() => {
    const m = {};
    floorNodes.forEach((n) => { m[n.node_id] = n; });
    return m;
  }, [floorNodes, activeFloor]); // eslint-disable-line react-hooks/exhaustive-deps

  // Same-floor edges (vertical lift/stairs links span floors — markers show those)
  const floorEdges = useMemo(() => {
    if (!edges || edges.length === 0) return [];
    return edges.filter((e) => nodeById[e.from_node_id] && nodeById[e.to_node_id]);
  }, [edges, nodeById]);

  // Corridor network = walk edges between walkway-type nodes (the hallway layer)
  const corridorLines = useMemo(() => (
    floorEdges.filter((e) => {
      const a = nodeById[e.from_node_id];
      const b = nodeById[e.to_node_id];
      return a && b && WALKWAY_TYPES.has(a.type) && WALKWAY_TYPES.has(b.type);
    })
  ), [floorEdges, nodeById]);

  const routeNodeIds = useMemo(
    () => new Set((route?.path || []).map((p) => p.node_id)),
    [route],
  );

  // Extract route path segments for the active floor
  const routePointsOnFloor = (route?.path || []).filter(
    (p) => Number(p.floor) === Number(activeFloor)
  );

  // Floors visited by the route
  const routeFloors = route?.floorsVisited || [];

  // Zoom handlers
  const handleZoomIn = () => setZoom((prev) => Math.min(prev * 1.25, 4));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev / 1.25, 0.5));
  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setView(null);
  };
  const handleFitRoute = () => {
    if (routePointsOnFloor.length === 0) return;
    const xs = routePointsOnFloor.map((p) => Number(p.x));
    const ys = routePointsOnFloor.map((p) => Number(p.y));
    const pad = Math.max(W, H) * 0.12;
    setView({
      x: Math.min(...xs) - pad,
      y: Math.min(...ys) - pad,
      w: Math.max(...xs) - Math.min(...xs) + pad * 2,
      h: Math.max(...ys) - Math.min(...ys) + pad * 2,
    });
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Reset camera when the route or floor changes
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setView(null);
  }, [route, activeFloor]);

  // Mouse wheel zoom
  const handleWheel = (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prev) => Math.min(Math.max(prev * factor, 0.5), 4));
  };

  // Pan dragging
  const handleMouseDown = (e) => {
    if (e.target.tagName.toLowerCase() === 'button') return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  // Auto-switch floor if start or route requires it
  useEffect(() => {
    if (route && routePointsOnFloor.length === 0 && routeFloors.length > 0) {
      // If current floor has no route points, switch to the first floor with route
      onChangeFloor(routeFloors[0]);
    }
  }, [route]);

  // Construct SVG polyline string for route
  const polylinePoints = routePointsOnFloor.map((p) => `${p.x},${p.y}`).join(' ');

  // Get coordinates of active simulated checkpoint if on this floor
  const activeCheckpoint = route?.checkpoints?.[currentStepIndex];
  const activeCheckpointOnFloor =
    activeCheckpoint && Number(activeCheckpoint.floor) === Number(activeFloor)
      ? floorNodes.find((n) => n.node_id === activeCheckpoint.node_id)
      : null;

  const showNode = (n) => {
    if (debugGraph) return true;
    if (routeNodeIds.has(n.node_id)) return true;
    if (startNode && startNode.node_id === n.node_id) return true;
    if (destinationNode && destinationNode.node_id === n.node_id) return true;
    return POI_TYPES.has(n.type);
  };

  const roomBlockSize = (n) => {
    if (n.type === 'hall') return { w: 16, h: 12 };
    if (n.type === 'stair' || n.type === 'lift') return { w: 10, h: 8 };
    if (n.type === 'door') return { w: 3.4, h: 3.4 };
    return { w: 12, h: 10 };
  };

  const viewBox = view ? `${view.x} ${view.y} ${view.w} ${view.h}`
    : `${baseView.x} ${baseView.y} ${baseView.w} ${baseView.h}`;

  return (
    <div
      ref={containerRef}
      className="map-viewport-wrapper"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Building / Floor context */}
      {(buildingName || floorName) && (
        <div className="floor-context-chip">
          <Layers size={13} />
          <span>{[buildingName, floorName || `Floor ${activeFloor}`].filter(Boolean).join(' • ')}</span>
        </div>
      )}

      {/* Floor Selector Floating Pills */}
      <div className="floor-selector-bar">
        {floors.map((f) => {
          const hasRoutePoints = routeFloors.includes(f.floor_number);
          const isActive = Number(activeFloor) === Number(f.floor_number);
          return (
            <button
              key={f.floor_number}
              className={`floor-btn ${isActive ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                onChangeFloor(f.floor_number);
              }}
              title={f.name || `Switch to Floor ${f.floor_number}`}
            >
              <span>F{f.floor_number}</span>
              {hasRoutePoints && <span className="floor-has-route-dot" />}
            </button>
          );
        })}
      </div>

      {/* Floating Zoom & Reset Map Controls */}
      <div className="map-floating-controls" role="group" aria-label="Indoor map controls">
        <button className="map-ctrl-btn" onClick={handleZoomIn} title="Zoom In" aria-label="Zoom in">
          <ZoomIn size={18} />
        </button>
        <button className="map-ctrl-btn" onClick={handleZoomOut} title="Zoom Out" aria-label="Zoom out">
          <ZoomOut size={18} />
        </button>
        {routePointsOnFloor.length > 1 && (
          <button className="map-ctrl-btn" onClick={handleFitRoute} title="Fit route" aria-label="Fit route in view">
            <Maximize size={16} />
          </button>
        )}
        <button className="map-ctrl-btn" onClick={handleResetView} title="Reset View" aria-label="Reset view">
          <RotateCcw size={16} />
        </button>
        <button
          className={`map-ctrl-btn ${debugGraph ? 'active-debug' : ''}`}
          onClick={() => setDebugGraph((v) => !v)}
          title="Toggle graph debug overlay (node IDs + edges)"
          aria-label="Toggle graph debug overlay"
          aria-pressed={debugGraph}
        >
          <Bug size={16} />
        </button>
      </div>

      {/* Map Legend Floating Pill */}
      <div className="map-legend-pill">
        <div className="legend-item">
          <span className="legend-color-dot" style={{ backgroundColor: 'var(--color-start)' }} />
          <span>Start</span>
        </div>
        <div className="legend-item">
          <span className="legend-color-dot" style={{ backgroundColor: 'var(--color-dest)' }} />
          <span>Destination</span>
        </div>
        <div className="legend-item">
          <span className="legend-color-dot" style={{ backgroundColor: 'var(--color-lift)' }} />
          <span>Lift</span>
        </div>
        <div className="legend-item">
          <span className="legend-color-dot" style={{ backgroundColor: 'var(--color-stair)' }} />
          <span>Stairs</span>
        </div>
      </div>

      {/* Interactive Tooltip on Node Hover */}
      {hoveredNode && (
        <div
          className="map-tooltip"
          style={{ left: tooltipPos.x, top: tooltipPos.y }}
        >
          {hoveredNode.name} ({hoveredNode.type})
          {debugGraph && (
            <span style={{ opacity: 0.75 }}> · {hoveredNode.node_id} · ({hoveredNode.x}, {hoveredNode.y})</span>
          )}
        </div>
      )}

      {/* SVG Canvas for Floor Plan */}
      <svg
        className="svg-map-canvas"
        viewBox={viewBox}
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transition: isDragging ? 'none' : 'transform 0.15s ease-out',
        }}
      >
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Floor-plan asset layer (optional per-floor SVG/PNG) */}
        {mapAsset ? (
          <image href={mapAsset} x="0" y="0" width={W} height={H} preserveAspectRatio="none" opacity="0.9" />
        ) : (
          <rect
            x="0"
            y="0"
            width={W}
            height={H}
            rx="2"
            fill="#FFFFFF"
            stroke="#E2E8F0"
            strokeWidth="0.8"
          />
        )}

        {/* Corridor network layer (walk edges between walkway nodes) */}
        {corridorLines.map((e) => {
          const a = nodeById[e.from_node_id];
          const b = nodeById[e.to_node_id];
          return (
            <g key={`corridor-${e.edge_id || `${e.from_node_id}-${e.to_node_id}`}`}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="map-corridor-band" />
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="map-corridor-guide" />
            </g>
          );
        })}

        {/* Debug: full edge overlay */}
        {debugGraph && floorEdges.map((e) => {
          const a = nodeById[e.from_node_id];
          const b = nodeById[e.to_node_id];
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          return (
            <g key={`dbg-edge-${e.edge_id || `${e.from_node_id}-${e.to_node_id}`}`}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="map-debug-edge" />
              <text x={mx} y={my - 0.6} className="map-debug-edge-label">
                {Number(e.distance).toFixed(0)}m
              </text>
            </g>
          );
        })}

        {/* Render Architectural Room Blocks */}
        {floorNodes.map((n) => {
          if (n.type === 'junction' || n.type === 'corridor') return null;
          if (n.type === 'door') {
            return (
              <g key={`room-rect-${n.node_id}`}>
                <rect
                  x={n.x - 1.7}
                  y={n.y - 1.7}
                  width={3.4}
                  height={3.4}
                  className="map-door-tick"
                  onClick={() => onNodeClick && onNodeClick(n)}
                />
              </g>
            );
          }

          const { w: rectW, h: rectH } = roomBlockSize(n);
          const rectX = n.x - rectW / 2;
          const rectY = n.y - rectH / 2;

          const roomFill = ROOM_FILL[n.type] || ROOM_FILL.default;

          return (
            <g key={`room-rect-${n.node_id}`}>
              <rect
                x={rectX}
                y={rectY}
                width={rectW}
                height={rectH}
                className="map-room-rect"
                fill={roomFill}
                onClick={() => onNodeClick && onNodeClick(n)}
              />
              <text
                x={n.x}
                y={n.y + 1}
                className="map-room-label"
              >
                {n.name.length > 11 ? `${n.name.substring(0, 9)}..` : n.name}
              </text>
            </g>
          );
        })}

        {/* Calculated Route Polyline */}
        {polylinePoints && (
          <g>
            {/* Glow Layer */}
            <polyline
              points={polylinePoints}
              className="route-glow-polyline"
            />
            {/* Solid Route Line */}
            <polyline
              points={polylinePoints}
              className="route-main-polyline"
            />
            {/* Moving Directional Dashes */}
            <polyline
              points={polylinePoints}
              className="route-dash-polyline"
            />
          </g>
        )}

        {/* Render Node Markers */}
        {floorNodes.filter(showNode).map((n) => {
          const isStart = startNode && startNode.node_id === n.node_id;
          const isDest = destinationNode && destinationNode.node_id === n.node_id;
          const isLift = n.type === 'lift';
          const isStair = n.type === 'stair';
          const onRoute = routeNodeIds.has(n.node_id);
          const dimmed = route && !onRoute && !isStart && !isDest;

          return (
            <g
              key={`node-marker-${n.node_id}`}
              className="node-circle-marker"
              opacity={dimmed && !debugGraph ? 0.35 : 1}
              onClick={() => onNodeClick && onNodeClick(n)}
              onMouseEnter={(e) => {
                setHoveredNode(n);
                const bbox = e.currentTarget.getBoundingClientRect();
                const parentBbox = containerRef.current?.getBoundingClientRect() || { left: 0, top: 0 };
                setTooltipPos({
                  x: bbox.left - parentBbox.left + bbox.width / 2,
                  y: bbox.top - parentBbox.top,
                });
              }}
              onMouseLeave={() => setHoveredNode(null)}
            >
              <circle
                cx={n.x}
                cy={n.y}
                r={n.type === 'door' ? 1.4 : 2.2}
                fill={isLift ? '#8B5CF6' : isStair ? '#F59E0B' : n.type === 'door' ? '#D97706' : '#3B82F6'}
                stroke="#FFFFFF"
                strokeWidth="0.8"
              />
              {debugGraph && (
                <text x={n.x} y={n.y - 3} textAnchor="middle" className="map-debug-node-label">
                  {n.node_id}
                </text>
              )}

              {/* Start Location Glowing Pulse Ring */}
              {isStart && (
                <g>
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r="4.5"
                    fill="none"
                    stroke="#10B981"
                    strokeWidth="1.2"
                    opacity="0.8"
                    className="start-pulse-ring"
                  />
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r="2.5"
                    fill="#10B981"
                    stroke="#FFFFFF"
                    strokeWidth="1"
                  />
                </g>
              )}

              {/* Destination Crimson Pin */}
              {isDest && (
                <g className="dest-pin-group">
                  <path
                    d={`M ${n.x} ${n.y - 1} C ${n.x - 2.5} ${n.y - 6} ${n.x - 2.5} ${n.y - 8} ${n.x} ${n.y - 8} C ${n.x + 2.5} ${n.y - 8} ${n.x + 2.5} ${n.y - 6} ${n.x} ${n.y - 1} Z`}
                    fill="#EF4444"
                    stroke="#B91C1C"
                    strokeWidth="0.5"
                  />
                  <circle cx={n.x} cy={n.y - 6} r="1" fill="#FFFFFF" />
                </g>
              )}
            </g>
          );
        })}

        {/* Active Simulated Walking Marker (Gamified Checkpoint Position) */}
        {activeCheckpointOnFloor && (
          <g>
            <circle
              cx={activeCheckpointOnFloor.x}
              cy={activeCheckpointOnFloor.y}
              r="3.5"
              fill="none"
              stroke="#3B82F6"
              strokeWidth="1.2"
              className="start-pulse-ring"
            />
            <circle
              cx={activeCheckpointOnFloor.x}
              cy={activeCheckpointOnFloor.y}
              r="2.2"
              fill="#2563EB"
              stroke="#FFFFFF"
              strokeWidth="0.8"
            />
          </g>
        )}
      </svg>
    </div>
  );
}
