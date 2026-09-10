import React from 'react';
import { Search, X, Loader2, Building2, MapPin, DoorOpen, Landmark, Trees } from 'lucide-react';

const TYPE_ICON = {
  building: Building2,
  outdoor: MapPin,
  room: DoorOpen,
  facility: Landmark,
  space: Trees,
};

export default function SearchBar({ query, results = [], searching, onChange, onSelect, onClear }) {
  const open = query && query.trim().length >= 2;
  return (
    <div className="campus-search">
      <div className="campus-search-box">
        <Search size={18} className="campus-search-icon" />
        <input
          value={query}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search campus, block, room, facility..."
          aria-label="Search campus"
          className="campus-search-input"
        />
        {searching ? (
          <Loader2 size={16} className="animate-spin text-muted" />
        ) : query ? (
          <button className="icon-btn" style={{ width: 28, height: 28 }} onClick={onClear} aria-label="Clear search">
            <X size={15} />
          </button>
        ) : null}
      </div>
      {open && (
        <div className="campus-search-results animate-slide-up">
          {results.length === 0 && !searching ? (
            <div className="campus-search-empty">No places found. Try “8th Block” or “Room 101”.</div>
          ) : (
            results.map((r) => {
              const Icon = TYPE_ICON[r.type] || MapPin;
              return (
                <button key={`${r.type}-${r.id}`} className="campus-search-item" onClick={() => onSelect(r)}>
                  <span className="campus-search-item-icon"><Icon size={16} /></span>
                  <span className="campus-search-item-text">
                    <span className="campus-search-item-name">{r.name}</span>
                    <span className="campus-search-item-sub">{r.subtitle}</span>
                  </span>
                  <span className="campus-search-item-type">{r.type}</span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
