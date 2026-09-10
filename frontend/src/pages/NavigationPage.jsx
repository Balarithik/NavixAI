import React, { useState, useEffect } from 'react';
import { ArrowUpDown, Footprints, RotateCcw, AlertCircle, Sparkles, Navigation, QrCode } from 'lucide-react';
import Header from '../components/Header';
import Scanner from '../components/Scanner';
import LocationSelector from '../components/LocationSelector';
import DestinationSelector from '../components/DestinationSelector';
import NavigationMap from '../components/NavigationMap';
import RouteSteps from '../components/RouteSteps';
import ProgressCard from '../components/ProgressCard';
import LiftStairModal from '../components/LiftStairModal';
import AchievementModal from '../components/AchievementModal';
import { api } from '../services/api';

export default function NavigationPage() {
  const [buildings, setBuildings] = useState([]);
  const [activeBuilding, setActiveBuilding] = useState(null);
  const [floors, setFloors] = useState([]);
  const [activeFloor, setActiveFloor] = useState(1);
  const [allNodes, setAllNodes] = useState([]);

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

  // Load initial building, floor, and node data
  useEffect(() => {
    async function init() {
      try {
        const [bldgData, floorData, nodeData] = await Promise.all([
          api.getBuildings(),
          api.getFloors(),
          api.getNodes(),
        ]);

        if (bldgData && bldgData.length > 0) {
          setBuildings(bldgData);
          setActiveBuilding(bldgData[0]);
        }
        if (floorData && floorData.length > 0) {
          setFloors(floorData);
          setActiveFloor(floorData[0].floor_number);
        }
        if (nodeData) {
          setAllNodes(nodeData);
          // Set default demo start and destination for immediate rich experience
          const defaultStart = nodeData.find((n) => n.node_id === 'F1_N01') || nodeData[0];
          const defaultDest = nodeData.find((n) => n.node_id === 'F2_N08') || nodeData[1];
          if (defaultStart) setStartNode(defaultStart);
          if (defaultDest) setDestinationNode(defaultDest);
        }
      } catch (err) {
        console.error('Failed to load initial navigation data:', err);
      }
    }
    init();
  }, []);

  // Compute route when start, destination, or mode changes
  const calculateRoute = async (fromId, toId, mode = 'any') => {
    if (!fromId || !toId) return;
    setLoadingRoute(true);
    setRouteError(null);

    try {
      const data = await api.getRoute(fromId, toId, mode);
      setRoute(data);
      setCurrentStepIndex(0);

      // If multi-floor transition exists and both lift and stairs are available, prompt user
      if (data.liftStairChoiceAvailable && mode === 'any') {
        setLiftStairModalOpen(true);
      }

      // Automatically sync active floor view to start node's floor
      if (data.path && data.path.length > 0) {
        setActiveFloor(data.path[0].floor);
      }
    } catch (err) {
      setRoute(null);
      setRouteError(err.message || 'Unable to compute route');
    } finally {
      setLoadingRoute(false);
    }
  };

  const handleFindRoute = () => {
    if (startNode && destinationNode) {
      calculateRoute(startNode.node_id, destinationNode.node_id, routingMode);
    }
  };

  const handleSwap = () => {
    const temp = startNode;
    setStartNode(destinationNode);
    setDestinationNode(temp);
    if (destinationNode && temp) {
      calculateRoute(destinationNode.node_id, temp.node_id, routingMode);
    }
  };

  const handleLocationFromScanner = (scanData) => {
    const matchedNode = allNodes.find((n) => n.node_id === scanData.node_id);
    if (matchedNode) {
      setStartNode(matchedNode);
      setActiveFloor(matchedNode.floor_number);
      triggerToast(`Location set to ${matchedNode.name}`, '10');
      if (destinationNode) {
        calculateRoute(matchedNode.node_id, destinationNode.node_id, routingMode);
      }
    }
  };

  const handleNodeClickFromMap = (node) => {
    if (!startNode) {
      setStartNode(node);
      triggerToast(`Start location set: ${node.name}`, '5');
    } else {
      setDestinationNode(node);
      triggerToast(`Destination set: ${node.name}`, '5');
      calculateRoute(startNode.node_id, node.node_id, routingMode);
    }
  };

  const handleSelectMode = (newMode) => {
    setRoutingMode(newMode);
    if (startNode && destinationNode) {
      calculateRoute(startNode.node_id, destinationNode.node_id, newMode);
      triggerToast(`Route updated for ${newMode.toUpperCase()}`, '10');
    }
  };

  const triggerToast = (message, xp) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, xp }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  };

  const handleStepNextCheckpoint = (nextIdx) => {
    setCurrentStepIndex(nextIdx);
    const cp = route?.checkpoints?.[nextIdx];
    if (cp) {
      // Sync active floor to current checkpoint floor
      setActiveFloor(cp.floor);

      if (cp.is_transition) {
        triggerToast(`🏆 Floor transition completed: Floor ${cp.floor}`, '20');
      } else {
        triggerToast(`Checkpoint reached: ${cp.name}`, '10');
      }
    }
  };

  return (
    <div className="app-container">
      {/* App Header */}
      <Header
        activeBuilding={activeBuilding}
        onOpenScanner={() => setScannerOpen(true)}
      />

      {/* Main Workspace: Sidebar & Interactive Map */}
      <div className="main-workspace">
        {/* Left Sidebar: Controls, Directions & Progress */}
        <aside className="nav-sidebar">
          {/* Search Box Inputs */}
          <div className="search-box-card">
            <LocationSelector
              label="From"
              selectedNode={startNode}
              onSelectNode={(node) => {
                setStartNode(node);
                if (node) setActiveFloor(node.floor_number);
                if (node && destinationNode) calculateRoute(node.node_id, destinationNode.node_id, routingMode);
              }}
              nodes={allNodes}
              placeholder="Search start location or scan QR..."
              onOpenScanner={() => setScannerOpen(true)}
            />

            <button className="swap-btn" onClick={handleSwap} title="Swap start and destination">
              <ArrowUpDown size={14} />
            </button>

            <DestinationSelector
              selectedNode={destinationNode}
              onSelectNode={(node) => {
                setDestinationNode(node);
                if (startNode && node) calculateRoute(startNode.node_id, node.node_id, routingMode);
              }}
              nodes={allNodes}
              placeholder="Search destination (Room, Lab, Hall...)"
            />

            <button
              className="primary-action-btn"
              onClick={handleFindRoute}
              disabled={!startNode || !destinationNode || loadingRoute}
            >
              <Navigation size={18} />
              <span>{loadingRoute ? 'Finding Shortest Route...' : 'Find Route'}</span>
            </button>
          </div>

          {/* Route Error Notification */}
          {routeError && (
            <div
              style={{
                margin: 16,
                padding: 12,
                borderRadius: 'var(--radius-md)',
                backgroundColor: '#FEF2F2',
                border: '1px solid #FCA5A5',
                color: '#991B1B',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                fontSize: '0.85rem',
              }}
            >
              <AlertCircle size={20} />
              <span>{routeError}</span>
            </div>
          )}

          {/* Route Details & Gamified Progress */}
          {route && (
            <div className="route-details-scroll">
              <RouteSteps route={route} />

              <ProgressCard
                route={route}
                currentStepIndex={currentStepIndex}
                onStepNext={handleStepNextCheckpoint}
                onResetProgress={() => setCurrentStepIndex(0)}
                onDestinationReached={() => setAchievementOpen(true)}
              />
            </div>
          )}
        </aside>

        {/* Right Area: Minimalist Indoor Navigation Map */}
        <main style={{ flex: 1, display: 'flex', position: 'relative' }}>
          <NavigationMap
            floors={floors}
            activeFloor={activeFloor}
            onChangeFloor={(fn) => setActiveFloor(fn)}
            nodes={allNodes}
            route={route}
            startNode={startNode}
            destinationNode={destinationNode}
            onNodeClick={handleNodeClickFromMap}
            currentStepIndex={currentStepIndex}
          />
        </main>
      </div>

      {/* QR Scanner Modal */}
      <Scanner
        isOpen={scannerOpen}
        onClose={() => setScannerOpen(false)}
        onLocationDetected={handleLocationFromScanner}
        allNodes={allNodes}
      />

      {/* Lift vs Stairs Choice Modal */}
      <LiftStairModal
        isOpen={liftStairModalOpen}
        onClose={() => setLiftStairModalOpen(false)}
        onSelectMode={handleSelectMode}
        currentMode={routingMode}
      />

      {/* Gamified Destination Reached Celebration Modal */}
      <AchievementModal
        isOpen={achievementOpen}
        onClose={() => setAchievementOpen(false)}
        destinationNode={destinationNode}
        route={route}
        xpEarned={50}
        onNewRoute={() => {
          setRoute(null);
          setDestinationNode(null);
        }}
      />

      {/* Floating Achievement Toasts */}
      {toasts.map((t) => (
        <div key={t.id} className="achievement-toast">
          <Sparkles size={16} color="#F59E0B" />
          <span>{t.message}</span>
          <Sparkles size={16} color="#F59E0B" />
        </div>
      ))}
    </div>
  );
}
