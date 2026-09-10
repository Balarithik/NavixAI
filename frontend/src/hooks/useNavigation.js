/**
 * useNavigation — single source of truth for campus navigation state.
 * mapMode: 'OUTDOOR' | 'INDOOR'
 * locationSource: 'GPS' | 'QR' | 'MANUAL' | null
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';

const CAMPUS_FALLBACK_CENTER = { lat: 9.574, lng: 77.6752 };

export function useNavigation() {
  const [mapMode, setMapMode] = useState('OUTDOOR');
  const [buildings, setBuildings] = useState([]);
  const [outdoorNodes, setOutdoorNodes] = useState([]);
  const [outdoorEdges, setOutdoorEdges] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [spaces, setSpaces] = useState([]);
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [buildingDetail, setBuildingDetail] = useState(null);

  // Indoor state (existing engine, now building-aware)
  const [floors, setFloors] = useState([]);
  const [activeFloor, setActiveFloor] = useState(1);
  const [allNodes, setAllNodes] = useState([]);
  const [startNode, setStartNode] = useState(null);
  const [destinationNode, setDestinationNode] = useState(null);
  const [route, setRoute] = useState(null);

  // Outdoor / unified state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [destination, setDestination] = useState(null); // unified destination model
  const [unifiedRoute, setUnifiedRoute] = useState(null);
  const [gps, setGps] = useState(null); // {lat, lng}
  const [gpsError, setGpsError] = useState(null);
  const [locationSource, setLocationSource] = useState(null);
  // Unified current location: {kind:'outdoor'|'indoor'|'gps', node_id?, name,
  //  latitude/longitude?, floor?, building_code?, source:'GPS'|'QR'|'MANUAL'}
  const [currentLocation, setCurrentLocation] = useState(null);
  // BROWSE | PREVIEW | ACTIVE | COMPLETE
  const [navigationStatus, setNavigationStatus] = useState('BROWSE');
  // Manual "From" override (a unified search result) — null = automatic.
  const [originOverride, setOriginOverride] = useState(null);
  // Map camera request {lat, lng, key} — maps center on it when key changes.
  const [centerOn, setCenterOn] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const searchTimer = useRef(null);

  const refreshCampus = useCallback(async () => {
    try {
      const [bldgs, onodes, oedges, facs, sps] = await Promise.all([
        api.getCampusBuildings(), api.getOutdoorNodes(), api.getOutdoorEdges(),
        api.getFacilities(), api.getSpaces(),
      ]);
      setBuildings(bldgs || []);
      setOutdoorNodes(onodes || []);
      setOutdoorEdges(oedges || []);
      setFacilities(facs || []);
      setSpaces(sps || []);
    } catch (err) {
      console.error('Campus data refresh failed:', err);
    }
  }, []);

  const refreshIndoor = useCallback(async (buildingCode) => {
    try {
      const [floorData, nodeData] = await Promise.all([
        buildingCode ? api.getBuildingFloors(buildingCode) : api.getFloors(),
        api.getNodes(),
      ]);
      const relevantFloors = buildingCode
        ? (floorData || [])
        : (floorData || []);
      const relevantNodes = buildingCode
        ? (nodeData || []).filter((n) => (n.building_code || 'MAIN') === buildingCode)
        : (nodeData || []);
      setFloors(relevantFloors);
      if (relevantFloors.length > 0) setActiveFloor(relevantFloors[0].floor_number);
      setAllNodes(relevantNodes.length > 0 ? relevantNodes : nodeData || []);
    } catch (err) {
      console.error('Indoor data refresh failed:', err);
    }
  }, []);

  // Refs so the listeners below always see current mode/selection
  // without re-subscribing (avoids duplicate listeners on every change).
  const mapModeRef = useRef(mapMode);
  mapModeRef.current = mapMode;
  const selectedBuildingRef = useRef(selectedBuilding);
  selectedBuildingRef.current = selectedBuilding;
  const lastRefreshRef = useRef(0);

  useEffect(() => {
    const refreshAll = () => {
      // Throttle: tab-focus fires both `focus` and `visibilitychange`;
      // StrictMode double-mount also re-runs this effect — skip refreshes <2s apart.
      const now = Date.now();
      if (now - lastRefreshRef.current < 2000) return;
      lastRefreshRef.current = now;
      refreshCampus();
      if (mapModeRef.current === 'INDOOR' && selectedBuildingRef.current) {
        refreshIndoor(selectedBuildingRef.current.code);
      } else {
        refreshIndoor();
      }
    };
    const onFocus = () => {
      refreshAll();
    };
    const onVisibilityChange = () => {
      if (!document.hidden) onFocus();
    };
    refreshAll();
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [refreshCampus, refreshIndoor]);

  // Debounced unified search
  const onSearchChange = useCallback((q) => {
    setSearchQuery(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!q || q.trim().length < 2) {
      setSearchResults([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    searchTimer.current = setTimeout(async () => {
      try {
        const data = await api.search(q.trim());
        setSearchResults(data.results || []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 250);
  }, []);

  const selectBuilding = useCallback(async (code) => {
    try {
      const detail = await api.getCampusBuilding(code);
      setSelectedBuilding(detail);
      setBuildingDetail(detail);
      setDestination({ type: 'building', id: code, name: detail.name, building_code: code });
    } catch (err) {
      setError(err.message || 'Building not found');
    }
  }, []);

  const enterBuilding = useCallback(async (code) => {
    setLoading(true);
    setError(null);
    try {
      const detail = await api.getCampusBuilding(code);
      setSelectedBuilding(detail);
      setBuildingDetail(detail);
      await refreshIndoor(code);
      setMapMode('INDOOR');
    } catch (err) {
      setError(err.message || 'Could not open building');
    } finally {
      setLoading(false);
    }
  }, [refreshIndoor]);

  const clearSelection = useCallback(() => {
    setSelectedBuilding(null);
    setBuildingDetail(null);
    setDestination(null);
  }, []);

  const exitToCampus = useCallback(() => {
    setMapMode('OUTDOOR');
  }, []);

  const setCurrentLocationFromScan = useCallback((scanData) => {
    if (!scanData || !scanData.valid) return null;
    let loc = null;
    if (scanData.location_type === 'outdoor') {
      loc = {
        kind: 'outdoor', node_id: scanData.location_id || scanData.node_id,
        name: scanData.name, latitude: scanData.latitude, longitude: scanData.longitude,
        building_code: scanData.building_id || null, source: 'QR',
      };
      setCenterOn({ lat: scanData.latitude, lng: scanData.longitude, key: Date.now() });
      setMapMode('OUTDOOR');
    } else {
      loc = {
        kind: 'indoor', node_id: scanData.node_id, name: scanData.name,
        floor: scanData.floor, building_code: scanData.building_id || null, source: 'QR',
      };
      setMapMode('INDOOR');
    }
    setCurrentLocation(loc);
    setLocationSource('QR');
    return loc;
  }, []);

  const requestGps = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setGpsError('Geolocation is not supported on this device.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setGps(coords);
        setCurrentLocation({ kind: 'gps', name: 'My Location', ...coords, source: 'GPS' });
        setCenterOn({ ...coords, key: Date.now() });
        setLocationSource('GPS');
        setGpsError(null);
      },
      (err) => {
        if (err.code === 1) setGpsError('Location permission denied. Enable it to navigate outdoors.');
        else if (err.code === 2) setGpsError('Location unavailable. Try again or pick a start point.');
        else setGpsError('Location request timed out. Try again.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  }, []);

  const startUnifiedRoute = useCallback(async ({ origin, dest, mode = 'any' }) => {
    setLoading(true);
    setError(null);
    try {
      const params = { mode, toType: dest.type, toId: dest.id };
      if (origin.kind === 'gps' && origin.coords) {
        params.fromLat = origin.coords.lat;
        params.fromLon = origin.coords.lng;
      } else if (origin.kind === 'outdoor_node') {
        params.fromType = 'outdoor_node';
        params.fromId = origin.node_id;
      } else if (origin.kind === 'indoor_node') {
        params.fromType = 'indoor_node';
        params.fromId = origin.node_id;
      }
      const data = await api.getUnifiedRoute(params);
      setUnifiedRoute(data);
      setDestination(dest);
      return data;
    } catch (err) {
      setError(err.message || 'Unable to compute route');
      setUnifiedRoute(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    mapMode, setMapMode,
    buildings, outdoorNodes, outdoorEdges, facilities, spaces,
    selectedBuilding, setSelectedBuilding, buildingDetail,
    floors, activeFloor, setActiveFloor, allNodes,
    startNode, setStartNode, destinationNode, setDestinationNode, route, setRoute,
    searchQuery, searchResults, searching, onSearchChange,
    destination, setDestination, unifiedRoute, setUnifiedRoute,
    gps, gpsError, requestGps, locationSource, setLocationSource,
    currentLocation, setCurrentLocation, setCurrentLocationFromScan,
    navigationStatus, setNavigationStatus,
    originOverride, setOriginOverride, centerOn, setCenterOn,
    loading, error, setError,
    refreshCampus, refreshIndoor, selectBuilding, clearSelection,
    enterBuilding, exitToCampus,
    startUnifiedRoute,
    campusCenter: CAMPUS_FALLBACK_CENTER,
  };
}
