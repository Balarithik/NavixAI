import React from 'react';
import { Footprints, Clock, Layers, ArrowUpDown, CornerDownRight, CheckCircle2, MapPin } from 'lucide-react';

export default function RouteSteps({ route }) {
  if (!route) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Route Summary KPI Bar */}
      <div className="route-summary-bar" style={{ borderRadius: 'var(--radius-md)', margin: '0 0 4px 0' }}>
        <div className="route-stat-item">
          <div className="stat-icon-wrap">
            <Footprints size={16} />
          </div>
          <div>
            <div className="stat-value">{route.distanceMetres} m</div>
            <div className="stat-label">Total Distance</div>
          </div>
        </div>

        <div className="route-stat-item">
          <div className="stat-icon-wrap" style={{ background: '#FEF3C7', color: '#D97706' }}>
            <Clock size={16} />
          </div>
          <div>
            <div className="stat-value">{route.durationMinutes} min</div>
            <div className="stat-label">Estimated Time</div>
          </div>
        </div>

        {route.floorsCrossed > 0 && (
          <div className="route-stat-item">
            <div className="stat-icon-wrap" style={{ background: '#EDE9FE', color: '#7C3AED' }}>
              <ArrowUpDown size={16} />
            </div>
            <div>
              <div className="stat-value">F{route.floorsVisited?.join(' → F')}</div>
              <div className="stat-label">{route.verticalMode.toUpperCase()} TRANSIT</div>
            </div>
          </div>
        )}
      </div>

      {/* Step-by-Step Instructions */}
      <div>
        <div className="section-subtitle" style={{ marginBottom: 12 }}>
          <span>Turn-by-Turn Directions</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 500 }}>{route.instructions?.length} steps</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {route.instructions?.map((stepText, idx) => {
            const isStart = idx === 0;
            const isEnd = idx === route.instructions.length - 1;
            const isTransition = stepText.toLowerCase().includes('lift') || stepText.toLowerCase().includes('stairs');

            return (
              <div key={`step-${idx}`} className="step-instruction-item">
                <div
                  className="step-number-bubble"
                  style={{
                    backgroundColor: isStart
                      ? '#DCFCE7'
                      : isEnd
                      ? '#FEE2E2'
                      : isTransition
                      ? '#EDE9FE'
                      : 'var(--bg-elevated)',
                    borderColor: isStart
                      ? '#10B981'
                      : isEnd
                      ? '#EF4444'
                      : isTransition
                      ? '#8B5CF6'
                      : 'var(--border-medium)',
                    color: isStart
                      ? '#15803D'
                      : isEnd
                      ? '#B91C1C'
                      : isTransition
                      ? '#6D28D9'
                      : 'var(--text-muted)',
                  }}
                >
                  {isStart ? (
                    <MapPin size={14} />
                  ) : isEnd ? (
                    <CheckCircle2 size={14} />
                  ) : isTransition ? (
                    <ArrowUpDown size={14} />
                  ) : (
                    idx + 1
                  )}
                </div>
                <div className="step-text" style={{ paddingTop: 4 }}>
                  {stepText}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
