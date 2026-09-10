/**
 * OutdoorMap — Google Maps JavaScript API when a key is configured,
 * otherwise a CampusNav-owned fallback campus map rendered from backend data.
 * Google-specific code is isolated in this file.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { LocateFixed, Plus, Minus } from 'lucide-react';

const GOOGLE_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
const GOOGLE_MAP_ID = import.meta.env.VITE_GOOGLE_MAP_ID || '';

let googlePromise = null;
function loadGoogleMaps() {
  if (typeof window !== 'undefined' && window.google?.maps) return Promise.resolve(window.google.maps);
  if (googlePromise) return googlePromise;
  googlePromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(GOOGLE_KEY)}&v=weekly&libraries=marker`;
    script.async = true;
    script.defer = true;
    script.onload = () => (window.google?.maps ? resolve(window.google.maps) : reject(new Error('Google Maps failed to load')));
    script.onerror = () => reject(new Error('Google Maps failed to load'));
    document.head.appendChild(script);
  });
  return googlePromise;
}

export default function OutdoorMap({
  buildings = [],
  outdoorNodes = [],
  outdoorEdges = [],
  facilities = [],
  spaces = [],
  routePath = [],
  gps = null,
  currentLocation = null,
  centerOn = null,
  routeActive = false,
  destPoint = null,
  selectedCode = null,
  center,
  onSelectBuilding,
  onLocate,
}) {
  const useGoogle = Boolean(GOOGLE_KEY);
  // Single "you are here" ping: QR/manual current location wins, else live GPS.
  const ping = currentLocation?.latitude != null
    ? { lat: Number(currentLocation.latitude), lng: Number(currentLocation.longitude), label: currentLocation.name, via: currentLocation.source }
    : gps
      ? { lat: gps.lat, lng: gps.lng, label: 'My Location', via: 'GPS' }
      : null;
  return (
    <div className="outdoor-map-wrap">
      {useGoogle ? (
        <GoogleCampusMap
          buildings={buildings}
          facilities={facilities}
          routePath={routePath}
          ping={ping}
          destPoint={destPoint}
          centerOn={centerOn}
          selectedCode={selectedCode}
          center={center}
          onSelectBuilding={onSelectBuilding}
        />
      ) : (
        <FallbackCampusMap
          buildings={buildings}
          outdoorNodes={outdoorNodes}
          outdoorEdges={outdoorEdges}
          facilities={facilities}
          spaces={spaces}
          routePath={routePath}
          ping={ping}
          centerOn={centerOn}
          routeActive={routeActive}
          destPoint={destPoint}
          selectedCode={selectedCode}
          onSelectBuilding={onSelectBuilding}
        />
      )}
      <div className="outdoor-map-controls" role="group" aria-label="Map controls">
        <button className="map-ctrl-btn" onClick={onLocate} title="My location" aria-label="Go to my location">
          <LocateFixed size={18} />
        </button>
      </div>
      {!useGoogle && (
        <div className="outdoor-map-notice">Preview campus map — add a Google Maps key for satellite view.</div>
      )}
    </div>
  );
}

function GoogleCampusMap({ buildings, facilities = [], routePath, ping, destPoint, centerOn, selectedCode, center, onSelectBuilding }) {
  const divRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const overlaysRef = useRef([]);
  const [mapError, setMapError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    loadGoogleMaps()
      .then((maps) => {
        if (cancelled || !divRef.current || mapRef.current) return;
        mapRef.current = new maps.Map(divRef.current, {
          center: center || { lat: 9.574, lng: 77.6752 },
          zoom: 16,
          mapId: GOOGLE_MAP_ID || undefined,
          disableDefaultUI: true,
          zoomControl: false,
        });
      })
      .catch((err) => !cancelled && setMapError(err.message));
    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Markers (AdvancedMarkerElement preferred, legacy fallback)
  useEffect(() => {
    const maps = window.google?.maps;
    const map = mapRef.current;
    if (!maps || !map) return;
    markersRef.current.forEach((m) => {
      try {
        if (m.map !== undefined) m.map = null;
        else m.setMap(null);
      } catch { /* noop */ }
    });
    markersRef.current = [];
    const useAdvanced = Boolean(maps.marker?.AdvancedMarkerElement);
    buildings.filter((b) => b.latitude && b.longitude).forEach((b) => {
      const pos = { lat: Number(b.latitude), lng: Number(b.longitude) };
      const isSel = b.code === selectedCode;
      if (useAdvanced) {
        const el = document.createElement('div');
        el.className = `g-marker${isSel ? ' selected' : ''}`;
        el.textContent = b.name;
        el.onclick = () => onSelectBuilding(b.code);
        const marker = new maps.marker.AdvancedMarkerElement({ map, position: pos, content: el, title: b.name });
        markersRef.current.push(marker);
      } else {
        const marker = new maps.Marker({ map, position: pos, title: b.name });
        marker.addListener('click', () => onSelectBuilding(b.code));
        markersRef.current.push(marker);
      }
      if (isSel) map.panTo(pos);
    });
    // Secondary facility POIs (standalone ones only — building-linked share the building marker)
    facilities.filter((f) => f.latitude && f.longitude && !f.building_code).forEach((f) => {
      const pos = { lat: Number(f.latitude), lng: Number(f.longitude) };
      if (useAdvanced) {
        const el = document.createElement('div');
        el.className = 'g-marker secondary';
        el.textContent = f.name;
        const marker = new maps.marker.AdvancedMarkerElement({ map, position: pos, content: el, title: f.name });
        markersRef.current.push(marker);
      } else {
        markersRef.current.push(new maps.Marker({
          map, position: pos, title: f.name,
          icon: { path: maps.SymbolPath.CIRCLE, scale: 6, fillColor: '#0D9488', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2 },
        }));
      }
    });
  }, [buildings, facilities, selectedCode, onSelectBuilding]);

  // Center on explicit requests (selection is handled in the marker effect)
  const centerKey = centerOn?.key;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !centerOn) return;
    map.panTo({ lat: Number(centerOn.lat), lng: Number(centerOn.lng) });
    map.setZoom(Math.max(map.getZoom() || 16, 17));
  }, [centerKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Route + location + destination overlays
  useEffect(() => {
    const maps = window.google?.maps;
    const map = mapRef.current;
    if (!maps || !map) return;
    overlaysRef.current.forEach((o) => {
      try {
        if (o.map !== undefined) o.map = null;
        else o.setMap(null);
      } catch { /* noop */ }
    });
    overlaysRef.current = [];
    if (routePath.length > 1) {
      const path = routePath.map((p) => ({ lat: Number(p.latitude), lng: Number(p.longitude) }));
      const line = new maps.Polyline({
        path, geodesic: true, strokeColor: '#2563EB', strokeWeight: 5, strokeOpacity: 0.9, map,
      });
      overlaysRef.current.push(line);
      const bounds = new maps.LatLngBounds();
      path.forEach((p) => bounds.extend(p));
      map.fitBounds(bounds, 48);
    }
    const putDot = (pos, title, color) => {
      if (window.google?.maps?.marker?.AdvancedMarkerElement) {
        const el = document.createElement('div');
        el.className = `g-dot${color === '#EF4444' ? ' dest' : ''}`;
        el.title = title;
        overlaysRef.current.push(
          new maps.marker.AdvancedMarkerElement({ map, position: pos, content: el, title }));
      } else {
        overlaysRef.current.push(new maps.Circle({
          center: pos, radius: 12, fillColor: color, fillOpacity: 1,
          strokeColor: '#fff', strokeWeight: 3, map,
        }));
      }
    };
    if (ping) {
      putDot({ lat: ping.lat, lng: ping.lng },
        ping.via === 'QR' ? `${ping.label} · Located by QR` : (ping.label || 'My Location'), '#2563EB');
    }
    if (destPoint) {
      putDot({ lat: Number(destPoint.latitude), lng: Number(destPoint.longitude) },
        'Destination', '#EF4444');
    }
  }, [routePath, ping, destPoint]);

  if (mapError) return <div className="outdoor-map-error">Map unavailable: {mapError}</div>;
  return <div ref={divRef} className="google-map-canvas" />;
}

/**
 * Illustrated campus map in the spirit of classic university wayfinding maps:
 * soft green ground, white building footprints, path network drawn from the
 * real outdoor-edge graph, water/parking context, minimal labels.
 * Everything is data-driven (backend API); no hard-coded geometry.
 */
const FOOTPRINT = {
  academic: { w: 9, h: 6.5 },
  facility: { w: 8, h: 6 },
  administration: { w: 8, h: 6 },
  hostel: { w: 7, h: 5 },
  gate: { w: 4, h: 3 },
  landmark: { w: 5, h: 4 },
  other: { w: 6, h: 4.5 },
};
const LABELED_CATEGORIES = new Set(['academic', 'facility', 'administration', 'hostel']);

function FallbackCampusMap({ buildings, outdoorNodes, outdoorEdges = [], facilities = [], spaces = [], routePath, ping, centerOn, routeActive, destPoint, selectedCode, onSelectBuilding }) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  // Camera window in SVG units; null = full campus. Driven by route / centerOn.
  const [view, setView] = useState(null);
  const drag = useRef(null);
  const centerKey = centerOn?.key;
  const routeKey = routeActive && routePath.length > 1 ? routePath.map((p) => p.node_id).join(',') : '';

  const nodeById = useMemo(() => {
    const m = {};
    outdoorNodes.forEach((n) => { m[n.node_id] = n; });
    return m;
  }, [outdoorNodes]);

  // Walkable paths (dedupe bidirectional pairs) with resolved coordinates.
  const roads = useMemo(() => {
    const seen = new Set();
    const list = [];
    (outdoorEdges || []).forEach((e) => {
      const a = nodeById[e.from_node_id];
      const b = nodeById[e.to_node_id];
      if (!a || !b) return;
      const key = [e.from_node_id, e.to_node_id].sort().join('|');
      if (seen.has(key)) return;
      seen.add(key);
      list.push({ key, ax: Number(a.latitude), ay: Number(a.longitude), bx: Number(b.latitude), by: Number(b.longitude) });
    });
    return list;
  }, [outdoorEdges, nodeById]);

  const pts = useMemo(() => {
    const list = [];
    buildings.forEach((b) => {
      if (b.latitude && b.longitude) list.push({ lat: Number(b.latitude), lng: Number(b.longitude) });
    });
    outdoorNodes.forEach((n) => list.push({ lat: Number(n.latitude), lng: Number(n.longitude) }));
    facilities.forEach((f) => {
      if (f.latitude && f.longitude) list.push({ lat: Number(f.latitude), lng: Number(f.longitude) });
    });
    spaces.forEach((s) => {
      if (s.latitude && s.longitude) list.push({ lat: Number(s.latitude), lng: Number(s.longitude) });
    });
    return list;
  }, [buildings, outdoorNodes, facilities, spaces]);

  const bounds = useMemo(() => {
    if (pts.length === 0) return { minLat: 9.572, maxLat: 9.576, minLng: 77.674, maxLng: 77.6765 };
    const lats = pts.map((p) => p.lat);
    const lngs = pts.map((p) => p.lng);
    const pad = 0.0006;
    return {
      minLat: Math.min(...lats) - pad, maxLat: Math.max(...lats) + pad,
      minLng: Math.min(...lngs) - pad, maxLng: Math.max(...lngs) + pad,
    };
  }, [pts]);

  const W = 100; const H = 70;
  const project = (lat, lng) => ({
    x: ((lng - bounds.minLng) / Math.max(1e-9, bounds.maxLng - bounds.minLng)) * W,
    y: (1 - (lat - bounds.minLat) / Math.max(1e-9, bounds.maxLat - bounds.minLat)) * H,
  });
  const toXY = (p) => project(Number(p.latitude), Number(p.longitude));

  // Map camera: fit active route, else center requested point, else full campus.
  useEffect(() => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
    if (routeKey) {
      const xs = [], ys = [];
      routePath.forEach((p) => { const { x, y } = toXY(p); xs.push(x); ys.push(y); });
      const pad = 6;
      setView({
        x: Math.max(0, Math.min(...xs) - pad), y: Math.max(0, Math.min(...ys) - pad),
        w: Math.min(W, Math.max(...xs) - Math.min(...xs) + pad * 2),
        h: Math.min(H, Math.max(...ys) - Math.min(...ys) + pad * 2),
      });
    } else if (centerOn) {
      const { x, y } = project(Number(centerOn.lat), Number(centerOn.lng));
      setView({ x: Math.max(0, x - 15), y: Math.max(0, y - 10.5), w: 30, h: 21 });
    } else {
      setView(null);
    }
  }, [routeKey, centerKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Declutter: junctions/walkways only while navigating their route; spaces only as context then.
  const routeIds = useMemo(() => new Set(routePath.map((p) => p.node_id)), [routePath]);
  const importantNodes = outdoorNodes.filter((n) =>
    ['gate', 'building_entrance', 'facility', 'landmark'].includes(n.type));
  const routeOnlyNodes = routeActive
    ? outdoorNodes.filter((n) => routeIds.has(n.node_id) && !importantNodes.includes(n))
    : [];

  const pathPts = routePath.map((p) => {
    const { x, y } = project(Number(p.latitude), Number(p.longitude));
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return (
    <div
      className="fallback-map"
      onMouseDown={(e) => { drag.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }; }}
      onMouseMove={(e) => { if (drag.current) setPan({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y }); }}
      onMouseUp={() => { drag.current = null; }}
      onMouseLeave={() => { drag.current = null; }}
    >
      <div className="fallback-zoom" role="group" aria-label="Zoom controls">
        <button className="map-ctrl-btn" onClick={() => setZoom((z) => Math.min(z * 1.25, 4))} title="Zoom in" aria-label="Zoom in"><Plus size={16} /></button>
        <button className="map-ctrl-btn" onClick={() => setZoom((z) => Math.max(z / 1.25, 0.5))} title="Zoom out" aria-label="Zoom out"><Minus size={16} /></button>
      </div>
      <svg
        viewBox={view ? `${view.x} ${view.y} ${view.w} ${view.h}` : `0 0 ${W} ${H}`}
        className="fallback-svg"
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
      >
        <defs>
          <filter id="fb-shadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="0.7" stdDeviation="0.7" floodColor="#94A3B8" floodOpacity="0.55" />
          </filter>
        </defs>

        {/* Campus ground */}
        <rect x="0" y="0" width={W} height={H} rx="3" className="fb-ground" />

        {/* Green + water context from campus spaces */}
        {spaces.filter((s) => s.latitude && s.longitude).map((s) => {
          const { x, y } = project(Number(s.latitude), Number(s.longitude));
          const isWater = ['water_body', 'recharge_pond'].includes(s.space_type);
          if (!routeActive && !isWater && s.space_type !== 'landscape') return null;
          return (
            <g key={s.space_id || s.id}>
              <ellipse cx={x} cy={y} rx={isWater ? 4.5 : 6} ry={isWater ? 3 : 4}
                className={isWater ? 'fb-water' : 'fb-green'} />
              {(routeActive || isWater) && (
                <text x={x} y={y - (isWater ? 3.6 : 4.6)} textAnchor="middle" className="fb-space-label">{s.name}</text>
              )}
            </g>
          );
        })}

        {/* Walkable path network (real outdoor edges) */}
        {roads.map((r) => {
          const a = project(r.ax, r.ay);
          const b = project(r.bx, r.by);
          return (
            <g key={`road-${r.key}`}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="fb-road-casing" />
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="fb-road" />
            </g>
          );
        })}

        {/* Route overlay (white casing + blue line + direction flow) */}
        {pathPts && (
          <g>
            <polyline points={pathPts} className="fb-route-casing" />
            <polyline points={pathPts} className="fb-route" />
            <polyline points={pathPts} className="fb-route-dash" />
          </g>
        )}

        {/* Route-only graph dots (decluttered otherwise) */}
        {routeOnlyNodes.map((n) => {
          const { x, y } = project(Number(n.latitude), Number(n.longitude));
          return <circle key={n.node_id} cx={x} cy={y} r="0.9" className="fallback-junction" />;
        })}

        {/* Standalone facility POIs */}
        {facilities.filter((f) => f.latitude && f.longitude && !f.building_code).map((f) => {
          const { x, y } = project(Number(f.latitude), Number(f.longitude));
          return (
            <g key={f.facility_id || f.id}>
              <rect x={x - 1.3} y={y - 1.3} width="2.6" height="2.6" rx="0.7" className="fb-facility" />
              <text x={x} y={y - 2} textAnchor="middle" className="fb-poi-label">{f.name}</text>
            </g>
          );
        })}

        {/* Parking badges */}
        {spaces.filter((s) => s.space_type === 'parking' && s.latitude && s.longitude).map((s) => {
          const { x, y } = project(Number(s.latitude), Number(s.longitude));
          return (
            <g key={`park-${s.space_id || s.id}`}>
              <rect x={x - 1.6} y={y - 1.6} width="3.2" height="3.2" rx="0.8" className="fb-parking" />
              <text x={x} y={y + 1.1} textAnchor="middle" className="fb-parking-label">P</text>
            </g>
          );
        })}

        {/* Building footprints */}
        {buildings.filter((b) => b.latitude && b.longitude).map((b) => {
          const { x, y } = project(Number(b.latitude), Number(b.longitude));
          const sel = b.code === selectedCode;
          const size = FOOTPRINT[b.category] || FOOTPRINT.other;
          const w = sel ? size.w * 1.3 : size.w;
          const h = sel ? size.h * 1.3 : size.h;
          const labeled = sel || LABELED_CATEGORIES.has(b.category);
          return (
            <g key={b.code} className="fallback-marker" onClick={() => onSelectBuilding(b.code)}>
              {sel && <rect x={x - w / 2 - 0.8} y={y - h / 2 - 0.8} width={w + 1.6} height={h + 1.6} rx="1.6" className="fb-selected-halo" />}
              <rect x={x - w / 2} y={y - h / 2} width={w} height={h} rx="1.1"
                className={sel ? 'fb-footprint-selected' : 'fb-footprint'} filter="url(#fb-shadow)" />
              <line x1={x - w / 2} y1={y} x2={x + w / 2} y2={y} className="fb-footprint-seam" />
              {labeled && (
                <text x={x} y={y + h / 2 + 2.4} textAnchor="middle" className={sel ? 'fb-label-selected' : 'fb-label'}>
                  {b.name}
                </text>
              )}
              {!labeled && <title>{b.name}</title>}
            </g>
          );
        })}

        {/* Gate / landmark entrance markers */}
        {importantNodes.filter((n) => n.type === 'gate').map((n) => {
          const { x, y } = project(Number(n.latitude), Number(n.longitude));
          return (
            <g key={n.node_id}>
              <circle cx={x} cy={y} r="1.5" className="fb-gate" />
              <text x={x} y={y - 2.2} textAnchor="middle" className="fb-poi-label">{n.name}</text>
            </g>
          );
        })}
        {destPoint && (() => {
          const { x, y } = project(Number(destPoint.latitude), Number(destPoint.longitude));
          return (
            <g>
              <circle cx={x} cy={y} r="2.6" fill="none" stroke="#EF4444" strokeWidth="0.5" opacity="0.7" />
              <circle cx={x} cy={y} r="1.6" className="fallback-dest" />
            </g>
          );
        })()}
        {ping && (() => {
          const { x, y } = project(ping.lat, ping.lng);
          return (
            <g>
              {ping.via === 'QR' && (
                <circle cx={x} cy={y} r="3.2" fill="none" stroke="#2563EB" strokeWidth="0.6" opacity="0.8" />
              )}
              <circle cx={x} cy={y} r="1.6" className="fallback-gps">
                <title>{ping.via === 'QR' ? `${ping.label} · Located by QR` : (ping.label || 'My Location')}</title>
              </circle>
            </g>
          );
        })()}
      </svg>
    </div>
  );
}
