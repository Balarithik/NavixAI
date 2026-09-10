import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowUpDown, AlertCircle, Sparkles, Navigation, QrCode,
  Compass, Building2, LocateFixed,
} from 'lucide-react';
import Scanner from '../components/Scanner';
import LocationSelector from '../components/LocationSelector';
import DestinationSelector from '../components/DestinationSelector';
import NavigationMap from '../components/NavigationMap';
import RouteSteps from '../components/RouteSteps';
import ProgressCard from '../components/ProgressCard';
import LiftStairModal from '../components/LiftStairModal';
import AchievementModal from '../components/AchievementModal';
import SearchBar from '../components/SearchBar';
import BuildingSheet from '../components/BuildingSheet';
import DirectionsPanel from '../components/DirectionsPanel';
import SegmentStepper from '../components/SegmentStepper';
import OutdoorMap from '../maps/OutdoorMap';
import { useNavigation } from '../hooks/useNavigation';
import { api } from '../services/api';
import '../styles/campus.css';

export default function NavigationPage() {
  const nav = useNavigation();
  const {
    mapMode, setMapMode, buildings, outdoorNodes, outdoorEdges, facilities, spaces,
    selectedBuilding, floors, activeFloor, setActiveFloor, allNodes,
    searchQuery, searchResults, searching, onSearchChange,
    destination, setDestination, unifiedRoute, setUnifiedRoute,
    gps, gpsError, requestGps, locationSource, setLocationSource,
    currentLocation, setCurrentLocationFromScan,
    navigationStatus, setNavigationStatus,
    originOverride, setOriginOverride, centerOn,
    loading, error, setError,
    refreshIndoor, selectBuilding, clearSelection, enterBuilding, exitToCampus,
    startUnifiedRoute, campusCenter,
  } = nav;
  const { setSelectedBuilding } = nav;

  // Indoor (existing engine, preserved)
  const [startNode, setStartNode] = useState(null);
  const [destinationNode, setDestinationNode] = useState(null);
  const [route, setRoute] = useState(null);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [routeError, setRouteError] = useState(null);
  const [routingMode, setRoutingMode] = useState('any');
  const [liftStairModalOpen, setLiftStairModalOpen] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [achievementOpen, setAchievementOpen] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [toasts, setToasts] = useState([]);
  const [directionsOpen, setDirectionsOpen] = useState(false);
  const [navigating, setNavigating] = useState(false);
  const [outdoorStepIndex, setOutdoorStepIndex] = useState(0);
  // Multi-segment journeys: which unified-route segment the map is showing.
  const [activeSegment, setActiveSegment] = useState(0);
  // Floor detail for the indoor map: edges + map metadata (lazy-loaded).
  const [floorEdges, setFloorEdges] = useState([]);
  const [floorMeta, setFloorMeta] = useState(null);

  const selCode = selectedBuilding?.code || null;

  // ---- Origin resolution: manual override → QR/GPS current → Main Gate ----
  // Declared (useCallback) before first use so render never hits the TDZ;
  // originInfo is derived via useMemo on the stable callback.
  const resolveOrigin = useCallback(() => {
    if (originOverride) {
      if (originOverride.type === 'outdoor') {
        return { origin: { kind: 'outdoor_node', node_id: originOverride.id }, label: originOverride.name };
      }
      if (originOverride.type === 'building') {
        const ent = outdoorNodes.find(
          (n) => n.type === 'building_entrance' && n.building_code === originOverride.id);
        if (ent) return { origin: { kind: 'outdoor_node', node_id: ent.node_id }, label: originOverride.name };
      }
      if ((originOverride.type === 'facility' || originOverride.type === 'space') &&
          originOverride.latitude && originOverride.longitude) {
        return {
          origin: { kind: 'gps', coords: { lat: originOverride.latitude, lng: originOverride.longitude } },
          label: originOverride.name,
        };
      }
      if (originOverride.type === 'room') {
        return {
          origin: { kind: 'indoor_node', node_id: originOverride.indoor_node_id || originOverride.id },
          label: originOverride.name,
        };
      }
    }
    if (currentLocation?.kind === 'outdoor') {
      return { origin: { kind: 'outdoor_node', node_id: currentLocation.node_id }, label: `${currentLocation.name} (QR)` };
    }
    if (currentLocation?.kind === 'gps' || gps) {
      const c = currentLocation?.kind === 'gps' ? currentLocation : gps;
      return { origin: { kind: 'gps', coords: { lat: c.latitude ?? c.lat, lng: c.longitude ?? c.lng } }, label: 'My Location (GPS)' };
    }
    return { origin: { kind: 'outdoor_node', node_id: 'MAIN_GATE' }, label: 'Main Gate' };
  }, [originOverride, currentLocation, gps, outdoorNodes]);

  const originInfo = useMemo(() => resolveOrigin(), [resolveOrigin]);

  const destPoint = useMemo(() => {
    const d = destination;
    if (d && d.latitude && d.longitude) return { latitude: Number(d.latitude), longitude: Number(d.longitude) };
    const seg = unifiedRoute?.segments?.find((s) => s.type === 'outdoor');
    const last = seg?.path?.[seg.path.length - 1];
    if (last) return { latitude: Number(last.latitude), longitude: Number(last.longitude) };
    return null;
  }, [destination, unifiedRoute]);

  // Seed indoor defaults once nodes load (preserves original demo experience)
  useEffect(() => {
    if (allNodes.length > 0 && !startNode && !destinationNode) {
      const s = allNodes.find((n) => n.node_id === 'F1_N01') || allNodes[0];
      const d = allNodes.find((n) => n.node_id === 'F2_N08') || allNodes[1];
      if (s) setStartNode(s);
      if (d) setDestinationNode(d);
    }
  }, [allNodes]); // eslint-disable-line react-hooks/exhaustive-deps

  const calculateRoute = async (fromId, toId, mode = 'any') => {
    if (!fromId || !toId) return;
    setLoadingRoute(true);
    setRouteError(null);
    try {
      const data = await api.getRoute(fromId, toId, mode);
      setRoute(data);
      setCurrentStepIndex(0);
      if (data.liftStairChoiceAvailable && mode === 'any') setLiftStairModalOpen(true);
      if (data.path?.length > 0) setActiveFloor(data.path[0].floor);
    } catch (err) {
      setRoute(null);
      setRouteError(err.message || 'Unable to compute route');
    } finally {
      setLoadingRoute(false);
    }
  };

  const triggerToast = (message) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  };

  const openDirections = async (dest) => {
    setDestination(dest);
    setDirectionsOpen(true);
    setNavigationStatus('PREVIEW');
    setActiveSegment(0);
    setOutdoorStepIndex(0);
    const { origin } = resolveOrigin();
    await startUnifiedRoute({ origin, dest, mode: 'any' });
  };

  // Show one unified-route segment on the correct map (auto map switching).
  const showSegment = useCallback(async (idx) => {
    const segs = unifiedRoute?.segments || [];
    const seg = segs[idx];
    if (!seg) return;
    setActiveSegment(idx);
    if (seg.type === 'outdoor') {
      setMapMode('OUTDOOR');
      return;
    }
    // Indoor segment: load its building + floor context, then prime the map.
    const code = seg.building_code;
    if (!code) return;
    setMapMode('INDOOR');
    try {
      const detail = await api.getCampusBuilding(code);
      setSelectedBuilding(detail);
    } catch { /* keep previous building context */ }
    await refreshIndoor(code);
    const floorNum = seg.floor ?? seg.path?.[0]?.floor;
    if (floorNum) setActiveFloor(floorNum);
    setRoute(seg);
    setCurrentStepIndex(0);
    try {
      const nodes = await api.getNodes();
      const from = nodes.find((n) => n.node_id === seg.from?.node_id);
      const to = nodes.find((n) => n.node_id === seg.to?.node_id);
      if (from) setStartNode(from);
      if (to) setDestinationNode(to);
    } catch { /* markers fall back to route path */ }
  }, [unifiedRoute, refreshIndoor, setActiveFloor, setMapMode, setSelectedBuilding]);

  // Follow segment selection (stepper / per-segment View buttons) and apply
  // segment 0 automatically when a fresh unified route arrives.
  useEffect(() => {
    if (!unifiedRoute?.segments?.length || !directionsOpen) return;
    showSegment(activeSegment);
  }, [activeSegment, showSegment, directionsOpen]);

  // Lazy floor detail: edges + map metadata for the indoor map.
  useEffect(() => {
    async function loadFloorDetail() {
      if (mapMode !== 'INDOOR') return;
      const code = selCode || startNode?.building_code || 'MAIN';
      try {
        const detail = await api.getBuildingFloorDetail(code, activeFloor);
        setFloorEdges(detail.edges || []);
        setFloorMeta({
          asset: detail.map?.asset || null,
          width: detail.map?.width || 100,
          height: detail.map?.height || 100,
          name: detail.floor_name || `Floor ${activeFloor}`,
        });
      } catch {
        setFloorEdges([]);
        setFloorMeta(null);
      }
    }
    loadFloorDetail();
  }, [mapMode, selCode, activeFloor]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- Outdoor flows ----
  const handleSearchSelect = async (result) => {
    onSearchChange('');
    setUnifiedRoute(null);
    if (result.type === 'building') {
      await selectBuilding(result.id);
      setDirectionsOpen(false);
    } else if (result.type === 'facility' && result.building_code) {
      await selectBuilding(result.building_code);
      setDirectionsOpen(false);
    } else {
      // room / outdoor place / standalone facility / space → directions
      await openDirections(result);
    }
  };

  const handleBuildingDirections = async () => {
    if (!selectedBuilding) return;
    await openDirections({ type: 'building', id: selectedBuilding.code, name: selectedBuilding.name });
  };

  const handleEnterBuilding = async (code) => {
    await enterBuilding(code);
    // Jump the stepper to this building's indoor segment when navigating.
    const idx = (unifiedRoute?.segments || []).findIndex(
      (s) => s.type === 'indoor' && s.building_code === code);
    if (idx >= 0) setActiveSegment(idx);
    // If the unified route targeted a room here, prime the indoor route too
    const dest = destination;
    if (dest?.type === 'room' && dest.building_code === code) {
      const entry = unifiedRoute?.segments?.find((s) => s.type === 'indoor');
      if (entry?.path?.length > 0) {
        const fromId = entry.path[0].node_id;
        const toId = dest.indoor_node_id || dest.id;
        const fromNode = allNodes.find((n) => n.node_id === fromId);
        const toNode = allNodes.find((n) => n.node_id === toId);
        if (fromNode) setStartNode(fromNode);
        if (toNode) setDestinationNode(toNode);
        if (fromId && toId) calculateRoute(fromId, toId, routingMode);
      }
    }
  };

  const outdoorPath = useMemo(() => {
    const seg = unifiedRoute?.segments?.find((s) => s.type === 'outdoor');
    return seg?.path || [];
  }, [unifiedRoute]);

  // ---- Unified scan handling (outdoor + indoor, backend-authoritative) ----
  const handleLocationFromScanner = (scanData) => {
    if (!scanData?.valid) return;
    setCurrentLocationFromScan(scanData);
    setLocationSource('QR');
    if (scanData.location_type === 'outdoor') {
      // Outdoor QR: map already centers via centerOn; offer immediate routing.
      setMapMode('OUTDOOR');
      triggerToast(`Current location: ${scanData.name} · Located by QR`);
    } else {
      const matched = allNodes.find((n) => n.node_id === scanData.node_id);
      if (matched) {
        setStartNode(matched);
        setActiveFloor(matched.floor_number);
        triggerToast(`Location set to ${matched.name}`);
        if (destinationNode) calculateRoute(matched.node_id, destinationNode.node_id, routingMode);
      }
      setMapMode('INDOOR');
    }
  };

  return (
    <div className="campus-shell">
      {/* Floating search */}
      <div className="campus-topbar">
        <div className="campus-brand">
          <span className="campus-brand-icon"><Compass size={18} /></span>
          <span className="campus-brand-name">CampusNav</span>
        </div>
        <SearchBar
          query={searchQuery}
          results={searchResults}
          searching={searching}
          onChange={onSearchChange}
          onSelect={handleSearchSelect}
          onClear={() => onSearchChange('')}
        />
        <div className="campus-top-actions">
          <button
            className={`mode-toggle${mapMode === 'OUTDOOR' ? ' active' : ''}`}
            onClick={() => { exitToCampus(); setDirectionsOpen(false); }}
            title="Campus map"
          >
            <Building2 size={15} /><span>Campus</span>
          </button>
          <button
            className={`mode-toggle${mapMode === 'INDOOR' ? ' active' : ''}`}
            onClick={() => setMapMode('INDOOR')}
            title="Indoor map"
          >
            <Navigation size={15} /><span>Indoor</span>
          </button>
          <button className="primary-action-btn campus-scan-btn" onClick={() => setScannerOpen(true)} title="Scan QR">
            <QrCode size={16} /><span>Scan</span>
          </button>
        </div>
      </div>

      {/* Map */}
      <div className="campus-map-area">
        {mapMode === 'OUTDOOR' ? (
          <OutdoorMap
            buildings={buildings}
            outdoorNodes={outdoorNodes}
            outdoorEdges={outdoorEdges}
            facilities={facilities}
            spaces={spaces}
            routePath={outdoorPath}
            gps={gps}
            currentLocation={currentLocation?.kind === 'outdoor' || currentLocation?.kind === 'gps' ? currentLocation : null}
            centerOn={centerOn}
            routeActive={Boolean(unifiedRoute) || navigating}
            destPoint={destPoint}
            selectedCode={selectedBuilding?.code || destination?.building_code || null}
            center={campusCenter}
            onSelectBuilding={(code) => { selectBuilding(code); setDirectionsOpen(false); }}
            onLocate={requestGps}
          />
        ) : (
          <NavigationMap
            floors={floors}
            activeFloor={activeFloor}
            onChangeFloor={setActiveFloor}
            nodes={allNodes}
            edges={floorEdges}
            route={route}
            startNode={startNode}
            destinationNode={destinationNode}
            onNodeClick={(node) => {
              if (!startNode) {
                setStartNode(node);
                triggerToast(`Start: ${node.name}`);
              } else {
                setDestinationNode(node);
                calculateRoute(startNode.node_id, node.node_id, routingMode);
              }
            }}
            currentStepIndex={currentStepIndex}
            buildingName={selectedBuilding?.name || startNode?.building_name || null}
            floorName={floorMeta?.name || floors.find((f) => Number(f.floor_number) === Number(activeFloor))?.name || null}
            mapAsset={floorMeta?.asset || null}
            mapWidth={floorMeta?.width || 100}
            mapHeight={floorMeta?.height || 100}
          />
        )}
        {gpsError && <div className="campus-gps-error"><AlertCircle size={14} /> {gpsError}</div>}
      </div>

      {/* Bottom sheet */}
      <div className="campus-bottom">
        {directionsOpen && (destination || unifiedRoute) ? (
          <>
            <div className="campus-sheet-stack">
              <SegmentStepper
                segments={unifiedRoute?.segments || []}
                activeIndex={activeSegment}
                onSelect={(i) => showSegment(i)}
              />
              <DirectionsPanel
                destination={destination}
                route={unifiedRoute}
                loading={loading}
                error={error}
                originLabel={originInfo.label}
            originOverride={originOverride}
            onPickOrigin={(r) => {
              setOriginOverride(r);
              if (destination) openDirections(destination);
            }}
            onClearOrigin={() => {
              setOriginOverride(null);
              if (destination) openDirections(destination);
            }}
            status={navigationStatus}
            stepIndex={outdoorStepIndex}
            onNextStep={() => setOutdoorStepIndex((i) => i + 1)}
            onStart={() => {
              setNavigating(true);
              setNavigationStatus('ACTIVE');
              setOutdoorStepIndex(0);
              // Begin at the first segment; the stepper effect switches maps.
              showSegment(0);
            }}
            onViewSegment={(i) => showSegment(i)}
            onEnd={() => { setNavigating(false); setNavigationStatus('BROWSE'); }}
            onClose={() => {
              setDirectionsOpen(false); setUnifiedRoute(null);
              setNavigating(false); setNavigationStatus('BROWSE'); setOutdoorStepIndex(0);
              setActiveSegment(0);
            }}
          />
          </div>
          </>
        ) : mapMode === 'OUTDOOR' && selectedBuilding ? (
          <BuildingSheet
            building={selectedBuilding}
            onClose={clearSelection}
            onDirections={handleBuildingDirections}
            onEnterBuilding={handleEnterBuilding}
          />
        ) : mapMode === 'INDOOR' ? (
          <div className="indoor-sheet">
            <div className="indoor-controls">
              <LocationSelector
                label="From"
                selectedNode={startNode}
                onSelectNode={(node) => {
                  setStartNode(node);
                  setLocationSource(node ? 'MANUAL' : locationSource);
                  if (node) setActiveFloor(node.floor_number);
                  if (node && destinationNode) calculateRoute(node.node_id, destinationNode.node_id, routingMode);
                }}
                nodes={allNodes}
                placeholder="Search start location..."
              />
              <button className="swap-btn" onClick={() => {
                setStartNode(destinationNode);
                setDestinationNode(startNode);
                if (destinationNode && startNode) calculateRoute(destinationNode.node_id, startNode.node_id, routingMode);
              }} title="Swap">
                <ArrowUpDown size={14} />
              </button>
              <DestinationSelector
                selectedNode={destinationNode}
                onSelectNode={(node) => {
                  setDestinationNode(node);
                  if (startNode && node) calculateRoute(startNode.node_id, node.node_id, routingMode);
                }}
                nodes={allNodes}
                placeholder="Destination (Room, Lab...)"
              />
              <button
                className="primary-action-btn"
                onClick={() => startNode && destinationNode && calculateRoute(startNode.node_id, destinationNode.node_id, routingMode)}
                disabled={!startNode || !destinationNode || loadingRoute}
              >
                <Navigation size={16} /><span>{loadingRoute ? 'Finding route...' : 'Find Route'}</span>
              </button>
              {routeError && <div className="campus-route-error"><AlertCircle size={14} /> {routeError}</div>}
            </div>
            {route && (
              <div className="indoor-route-scroll">
                <RouteSteps route={route} />
                <ProgressCard
                  route={route}
                  currentStepIndex={currentStepIndex}
                  onStepNext={(idx) => {
                    setCurrentStepIndex(idx);
                    const cp = route?.checkpoints?.[idx];
                    if (cp) {
                      setActiveFloor(cp.floor);
                      triggerToast(cp.is_transition ? `Floor transition: Floor ${cp.floor}` : `Checkpoint: ${cp.name}`);
                    }
                  }}
                  onResetProgress={() => setCurrentStepIndex(0)}
                  onDestinationReached={() => { setAchievementOpen(true); setNavigationStatus('COMPLETE'); }}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="campus-hint">
            <LocateFixed size={14} />
            {currentLocation ? (
              <span>Current location: <strong>{currentLocation.name}</strong> · Located by {currentLocation.source}</span>
            ) : (
              <span>Search a block or room — or tap a building marker to explore.</span>
            )}
            {!gps && <button className="link-btn" onClick={requestGps}>Use my location</button>}
            {locationSource && <span className="loc-source">via {locationSource}</span>}
          </div>
        )}
      </div>

      <Scanner
        isOpen={scannerOpen}
        onClose={() => setScannerOpen(false)}
        onLocationDetected={handleLocationFromScanner}
        allNodes={allNodes}
        outdoorNodes={outdoorNodes}
      />
      <LiftStairModal
        isOpen={liftStairModalOpen}
        onClose={() => setLiftStairModalOpen(false)}
        onSelectMode={(m) => {
          setRoutingMode(m);
          if (startNode && destinationNode) calculateRoute(startNode.node_id, destinationNode.node_id, m);
        }}
        currentMode={routingMode}
      />
      <AchievementModal
        isOpen={achievementOpen}
        onClose={() => { setAchievementOpen(false); setNavigationStatus('BROWSE'); }}
        destinationNode={destinationNode}
        route={route}
        xpEarned={50}
        onNewRoute={() => { setRoute(null); setDestinationNode(null); setNavigationStatus('BROWSE'); }}
      />
      {toasts.map((t) => (
        <div key={t.id} className="achievement-toast">
          <Sparkles size={16} color="#F59E0B" /><span>{t.message}</span><Sparkles size={16} color="#F59E0B" />
        </div>
      ))}
    </div>
  );
}
