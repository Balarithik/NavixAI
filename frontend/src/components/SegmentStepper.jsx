import React from 'react';
import { Building2, Map as MapIcon, Check } from 'lucide-react';

/**
 * SegmentStepper — one chip per unified-route segment.
 * Shows INDOOR → OUTDOOR → INDOOR journeys as explicit steps and lets the
 * user jump the map to any segment (auto map switching happens on select).
 */
export default function SegmentStepper({ segments = [], activeIndex = 0, onSelect }) {
  if (!segments || segments.length < 2) return null;
  return (
    <div className="segment-stepper" role="tablist" aria-label="Route segments">
      {segments.map((s, i) => {
        const isActive = i === activeIndex;
        const isDone = i < activeIndex;
        const Icon = s.type === 'outdoor' ? MapIcon : Building2;
        return (
          <button
            key={`seg-${i}`}
            role="tab"
            aria-selected={isActive}
            className={`segment-chip${isActive ? ' active' : ''}${isDone ? ' done' : ''}`}
            onClick={() => onSelect(i)}
            title={s.title || s.type}
          >
            <span className="segment-chip-icon">
              {isDone ? <Check size={13} /> : <Icon size={13} />}
            </span>
            <span className="segment-chip-text">
              <span className="segment-chip-title">{s.title || (s.type === 'outdoor' ? 'Outdoor' : 'Indoor')}</span>
              <span className="segment-chip-sub">
                {s.distanceMetres != null ? `${Math.round(s.distanceMetres)} m` : ''}
                {s.durationMinutes != null ? ` · ${s.durationMinutes} min` : ''}
              </span>
            </span>
            <span className="segment-chip-num">{i + 1}</span>
          </button>
        );
      })}
    </div>
  );
}
