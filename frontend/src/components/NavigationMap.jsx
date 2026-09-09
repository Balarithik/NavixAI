import React, { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, MapPin, Navigation, ArrowUpDown, Footprints, Layers } from 'lucide-react';

export default function NavigationMap({
  floors = [],
  activeFloor = 1,
  onChangeFloor,
  nodes = [],
  route = null,
  startNode = null,
  destinationNode = null,
  onNodeClick,
  currentStepIndex = 0,
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Filter nodes for active floor
  const floorNodes = nodes.filter((n) => Number(n.floor_number || n.floor) === Number(activeFloor));

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
  };

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
              title={`Switch to Floor ${f.floor_number}`}
            >
              <span>F{f.floor_number}</span>
              {hasRoutePoints && <span className="floor-has-route-dot" />}
            </button>
          );
        })}
      </div>

      {/* Floating Zoom & Reset Map Controls */}
      <div className="map-floating-controls">
        <button className="map-ctrl-btn" onClick={handleZoomIn} title="Zoom In">
          <ZoomIn size={18} />
        </button>
        <button className="map-ctrl-btn" onClick={handleZoomOut} title="Zoom Out">
          <ZoomOut size={18} />
        </button>
        <button className="map-ctrl-btn" onClick={handleResetView} title="Reset View">
          <RotateCcw size={16} />
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
        </div>
      )}

      {/* SVG Canvas for Floor Plan */}
      <svg
        className="svg-map-canvas"
        viewBox="0 0 110 105"
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

        {/* Muted Floor Boundary */}
        <rect
          x="5"
          y="15"
          width="100"
          height="80"
          rx="4"
          fill="#FFFFFF"
          stroke="#E2E8F0"
          strokeWidth="1"
        />

        {/* Corridor Guideway Grid Lines */}
        <line x1="10" y1="85" x2="85" y2="85" className="map-corridor-guide" />
        <line x1="35" y1="35" x2="35" y2="85" className="map-corridor-guide" />
        <line x1="35" y1="60" x2="85" y2="60" className="map-corridor-guide" />
        <line x1="20" y1="75" x2="90" y2="75" className="map-corridor-guide" />
        <line x1="20" y1="50" x2="85" y2="50" className="map-corridor-guide" />
        <line x1="20" y1="25" x2="85" y2="25" className="map-corridor-guide" />
        <line x1="20" y1="25" x2="20" y2="75" className="map-corridor-guide" />
        <line x1="50" y1="25" x2="55" y2="75" className="map-corridor-guide" />
        <line x1="75" y1="25" x2="80" y2="75" className="map-corridor-guide" />
        <line x1="35" y1="35" x2="90" y2="35" className="map-corridor-guide" />

        {/* Render Architectural Room Cubicles */}
        {floorNodes.map((n) => {
          if (n.type === 'junction') return null;

          const isStairOrLift = n.type === 'stair' || n.type === 'lift';
          const rectW = isStairOrLift ? 10 : 12;
          const rectH = isStairOrLift ? 8 : 10;
          const rectX = n.x - rectW / 2;
          const rectY = n.y - rectH / 2;

          let roomFill = '#F8FAFC';
          if (n.type === 'lift') roomFill = '#F5F3FF';
          else if (n.type === 'stair') roomFill = '#FFFBEB';
          else if (n.type === 'amenity') roomFill = '#F0FDF4';

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
        {floorNodes.map((n) => {
          const isStart = startNode && startNode.node_id === n.node_id;
          const isDest = destinationNode && destinationNode.node_id === n.node_id;
          const isLift = n.type === 'lift';
          const isStair = n.type === 'stair';
          const isJunction = n.type === 'junction';

          return (
            <g
              key={`node-marker-${n.node_id}`}
              className="node-circle-marker"
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
              {isJunction ? (
                <circle cx={n.x} cy={n.y} r="1.2" fill="#94A3B8" opacity="0.6" />
              ) : (
                <circle
                  cx={n.x}
                  cy={n.y}
                  r="2.2"
                  fill={isLift ? '#8B5CF6' : isStair ? '#F59E0B' : '#3B82F6'}
                  stroke="#FFFFFF"
                  strokeWidth="0.8"
                />
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
