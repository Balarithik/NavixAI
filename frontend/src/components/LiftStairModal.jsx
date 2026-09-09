import React from 'react';
import { ArrowUpDown, Footprints, Sparkles, X } from 'lucide-react';

export default function LiftStairModal({ isOpen, onClose, onSelectMode, currentMode }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content-card" style={{ maxWidth: 440 }}>
        <div className="modal-header">
          <div>
            <h3 style={{ fontSize: '1.15rem', color: 'var(--text-main)' }}>Choose Your Route</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 2 }}>
              Your route transitions between floors. Please choose your preferred transit method.
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div className="choice-cards-container">
            {/* LIFT CARD */}
            <div
              className={`choice-option-card ${currentMode === 'lift' ? 'selected' : ''}`}
              onClick={() => {
                onSelectMode('lift');
                onClose();
              }}
            >
              <div
                className="choice-icon"
                style={{ backgroundColor: '#EDE9FE', color: '#8B5CF6' }}
              >
                <ArrowUpDown size={28} />
              </div>
              <div className="choice-title" style={{ color: '#6D28D9' }}>
                🛗 LIFT
              </div>
              <div className="choice-tagline">
                Accessible & comfortable
              </div>
              <div style={{ marginTop: 8, fontSize: '0.72rem', color: '#7C3AED', fontWeight: 600 }}>
                Wheelchair Friendly
              </div>
            </div>

            {/* STAIRS CARD */}
            <div
              className={`choice-option-card ${currentMode === 'stairs' ? 'selected' : ''}`}
              onClick={() => {
                onSelectMode('stairs');
                onClose();
              }}
            >
              <div
                className="choice-icon"
                style={{ backgroundColor: '#FEF3C7', color: '#D97706' }}
              >
                <Footprints size={28} />
              </div>
              <div className="choice-title" style={{ color: '#B45309' }}>
                🪜 STAIRS
              </div>
              <div className="choice-tagline">
                Active route & exercise
              </div>
              <div style={{ marginTop: 8, fontSize: '0.72rem', color: '#D97706', fontWeight: 600 }}>
                May be faster
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button
            className="secondary-action-btn"
            onClick={() => {
              onSelectMode('any');
              onClose();
            }}
          >
            Fastest Route (Auto)
          </button>
        </div>
      </div>
    </div>
  );
}
