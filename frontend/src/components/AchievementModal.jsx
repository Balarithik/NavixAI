import React from 'react';
import { Trophy, CheckCircle2, Footprints, Clock, Sparkles, X, ArrowRight } from 'lucide-react';

export default function AchievementModal({ isOpen, onClose, destinationNode, route, xpEarned = 50, onNewRoute }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content-card" style={{ maxWidth: 420, textAlign: 'center' }}>
        <div style={{ padding: '28px 24px 18px 24px', position: 'relative' }}>
          <button
            className="icon-btn"
            onClick={onClose}
            style={{ position: 'absolute', top: 14, right: 14 }}
          >
            <X size={18} />
          </button>

          <div
            style={{
              width: 68,
              height: 68,
              borderRadius: 'var(--radius-full)',
              backgroundColor: '#FEF3C7',
              color: '#D97706',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto',
              boxShadow: '0 4px 14px rgba(245, 158, 11, 0.3)',
            }}
          >
            <Trophy size={36} />
          </div>

          <h2 style={{ fontSize: '1.4rem', color: 'var(--text-main)', marginBottom: 4 }}>
            Destination Reached 🎯
          </h2>
          <p style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--color-primary)' }}>
            {destinationNode?.name || route?.to?.name}
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: 2 }}>
            Floor {destinationNode?.floor_number || destinationNode?.floor || route?.to?.floor}
          </p>


          {/* Statistics Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 12,
              background: 'var(--bg-elevated)',
              padding: 14,
              borderRadius: 'var(--radius-md)',
              margin: '8px 0 20px 0',
            }}
          >
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)' }}>
                {route?.distanceMetres || 0} m
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Distance Walked</div>
            </div>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-main)' }}>
                {route?.durationMinutes || 1} min
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Time Elapsed</div>
            </div>
          </div>

          <button
            className="primary-action-btn"
            onClick={() => {
              onClose();
              if (onNewRoute) onNewRoute();
            }}
            style={{ width: '100%' }}
          >
            <span>Plan Next Route</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
