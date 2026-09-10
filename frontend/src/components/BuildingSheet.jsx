import React from 'react';
import { Building2, Navigation, DoorOpen, X, MapPin } from 'lucide-react';

export default function BuildingSheet({ building, onClose, onDirections, onEnterBuilding }) {
  if (!building) return null;
  const floors = building.floors || [];
  const hasIndoor = floors.length > 0;
  return (
    <div className="campus-sheet animate-slide-up" role="dialog" aria-label={building.name}>
      <div className="campus-sheet-handle" />
      <div className="campus-sheet-header">
        <div className="campus-sheet-icon"><Building2 size={20} /></div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="campus-sheet-title">{building.name}</div>
          <div className="campus-sheet-sub">
            {building.category ? `${building.category.charAt(0).toUpperCase()}${building.category.slice(1)}` : 'Building'}
            {building.code ? ` · ${building.code}` : ''}
          </div>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close building details"><X size={18} /></button>
      </div>
      {building.description ? <p className="campus-sheet-desc">{building.description}</p> : null}
      <div className="campus-sheet-actions">
        <button className="primary-action-btn" onClick={onDirections}>
          <Navigation size={16} /><span>Directions</span>
        </button>
        <button
          className="secondary-action-btn"
          onClick={() => hasIndoor && onEnterBuilding(building.code)}
          disabled={!hasIndoor}
          title={hasIndoor ? 'Open indoor floor map' : 'Indoor map not yet available for this building'}
        >
          <DoorOpen size={16} /><span>Enter Building</span>
        </button>
      </div>
      <div className="campus-sheet-floors">
        <MapPin size={13} className="text-muted" />
        {hasIndoor ? (
          <span>Available floors: {floors.map((f) => f.name || `Floor ${f.floor_number}`).join(' · ')}</span>
        ) : (
          <span>Outdoor destination only — indoor map coming soon.</span>
        )}
      </div>
    </div>
  );
}
