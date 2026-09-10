import React, { useRef, useState } from 'react';
import { Navigation, X, Footprints, Clock, PersonStanding, MapPin, Pencil, Check } from 'lucide-react';
import { api } from '../services/api';

const ORIGIN_TYPES = new Set(['outdoor', 'building', 'facility', 'space']);

export default function DirectionsPanel({
  destination, route, loading, error,
  originLabel, originOverride, onPickOrigin, onClearOrigin,
  status = 'PREVIEW', stepIndex = 0, onNextStep, onStart, onEnd, onClose,
  onViewSegment,
}) {
  const [editingOrigin, setEditingOrigin] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const timer = useRef(null);

  const onQuery = (v) => {
    setQ(v);
    if (timer.current) clearTimeout(timer.current);
    if (!v || v.trim().length < 2) { setResults([]); return; }
    timer.current = setTimeout(async () => {
      try {
        const data = await api.search(v.trim());
        setResults((data.results || []).filter((r) => ORIGIN_TYPES.has(r.type)));
      } catch { setResults([]); }
    }, 250);
  };

  if (!destination && !route) return null;
  const segments = route?.segments || [];
  const steps = route?.instructions || [];
  const checkpoints = route?.checkpoints || [];
  const navigating = status === 'ACTIVE';
  const total = Math.max(steps.length, 1);
  const pct = Math.min(100, Math.round(((Math.min(stepIndex, total - 1)) + 1) / total * 100));
  const currentStep = steps[Math.min(stepIndex, steps.length - 1)];

  return (
    <div className="campus-sheet animate-slide-up" role="dialog" aria-label="Directions">
      <div className="campus-sheet-handle" />
      <div className="campus-sheet-header">
        <div className="campus-sheet-icon"><Navigation size={20} /></div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="campus-sheet-title">{destination?.name || 'Directions'}</div>
          <div className="campus-sheet-sub">
            {destination?.building_name || destination?.name || ''}
          </div>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close directions"><X size={18} /></button>
      </div>

      {/* From / To */}
      <div className="dir-fromto">
        <div className="dir-row">
          <span className="dir-dot dir-dot-from" />
          <div className="dir-row-text">
            <span className="dir-label">From</span>
            <span className="dir-value">{originOverride ? originOverride.name : originLabel || 'My Location'}</span>
          </div>
          {!navigating && (
            originOverride ? (
              <button className="link-btn" onClick={onClearOrigin}>Auto</button>
            ) : (
              <button className="link-btn" onClick={() => setEditingOrigin((v) => !v)}>
                <Pencil size={13} /> Change
              </button>
            )
          )}
        </div>
        {editingOrigin && !navigating && (
          <div className="dir-origin-search">
            <input
              value={q}
              onChange={(e) => onQuery(e.target.value)}
              placeholder="Search start: gate, entrance, block..."
              aria-label="Search start location"
              className="dir-origin-input"
            />
            {results.map((r) => (
              <button
                key={`${r.type}-${r.id}`}
                className="dir-origin-item"
                onClick={() => { onPickOrigin(r); setEditingOrigin(false); setQ(''); setResults([]); }}
              >
                <MapPin size={14} />
                <span><strong>{r.name}</strong> <span className="text-muted">· {r.subtitle}</span></span>
              </button>
            ))}
          </div>
        )}
        <div className="dir-row">
          <span className="dir-dot dir-dot-to" />
          <div className="dir-row-text">
            <span className="dir-label">To</span>
            <span className="dir-value">{destination?.name}</span>
          </div>
        </div>
      </div>

      {loading && <div className="campus-sheet-empty">Finding the best route…</div>}
      {error && <div className="campus-route-error">{error}</div>}

      {route && !navigating && (
        <>
          <div className="campus-route-summary">
            <span className="campus-route-stat"><Footprints size={15} /> {route.totalDistanceMetres ?? route.distanceMetres} m</span>
            <span className="campus-route-stat"><Clock size={15} /> {route.totalDurationMinutes ?? route.durationMinutes} min</span>
            {route.mode && <span className="campus-route-mode">{String(route.mode).replace(/_/g, ' ')}</span>}
          </div>
          {segments.length > 1 && (
            <div className="campus-segments">
              {segments.map((s, i) => (
                <span key={i} className="campus-segment-chip">
                  <PersonStanding size={12} /> {s.title || s.type}: {s.distanceMetres != null ? `${Math.round(s.distanceMetres)} m` : ''}
                </span>
              ))}
            </div>
          )}
          <button
            className="link-btn dir-details-toggle"
            onClick={() => setShowDetails((v) => !v)}
            aria-expanded={showDetails}
          >
            {showDetails ? 'Hide step-by-step details' : `Show step-by-step details (${steps.length})`}
          </button>
          {showDetails && (
            segments.length > 1 ? (
              <div className="campus-segments-grouped">
                {segments.map((s, i) => (
                  <div key={i} className="campus-segment-block">
                    <div className="campus-segment-head">
                      <PersonStanding size={13} />
                      <span className="campus-segment-title">{s.title || s.type}</span>
                      <span className="campus-segment-stats">
                        {s.distanceMetres != null ? `${Math.round(s.distanceMetres)} m` : ''}
                        {s.durationMinutes != null ? ` · ${s.durationMinutes} min` : ''}
                      </span>
                    </div>
                    <ol className="campus-route-steps">
                      {(s.instructions || []).map((step, j) => (
                        <li key={j} className="campus-route-step">
                          <span className="campus-route-step-num">{j + 1}</span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                    {onViewSegment && (
                      <button className="link-btn" onClick={() => onViewSegment(i)}>
                        View this part on the map
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <ol className="campus-route-steps">
                {steps.map((step, i) => (
                  <li key={i} className="campus-route-step">
                    <span className="campus-route-step-num">{i + 1}</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            )
          )}
          {onStart && (
            <button className="primary-action-btn" onClick={onStart} style={{ marginTop: 4 }}>
              <Navigation size={16} /><span>Start Navigation</span>
            </button>
          )}
        </>
      )}

      {route && navigating && (
        <div className="nav-active">
          <div className="nav-active-top">
            <span className="progress-percent-badge">{pct}%</span>
            <div className="progress-track" style={{ flex: 1 }}>
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
          <div className="nav-next">
            <span className="nav-next-label">Next</span>
            <span className="nav-next-step">{currentStep}</span>
          </div>
          {checkpoints.length > 0 && (
            <div className="nav-checkpoints">
              {checkpoints.map((c, i) => (
                <span key={i} className={`nav-cp${i <= stepIndex ? ' done' : ''}`}>
                  {i <= stepIndex ? <Check size={11} /> : '○'} {c.name}
                </span>
              ))}
            </div>
          )}
          <div className="nav-active-actions">
            <button
              className="primary-action-btn"
              onClick={onNextStep}
              disabled={stepIndex >= steps.length - 1}
              style={{ flex: 1 }}
            >
              <span>Next step</span>
            </button>
            <button className="secondary-action-btn" onClick={onEnd}>End</button>
          </div>
        </div>
      )}
    </div>
  );
}
