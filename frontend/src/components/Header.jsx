import React from 'react';
import { Compass, QrCode, Building, Sparkles } from 'lucide-react';

export default function Header({ onOpenScanner, activeBuilding }) {
  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-icon">
          <Compass size={20} />
        </div>
        <div>
          <span className="brand-title">NavixAI</span>
          <span className="brand-badge" style={{ marginLeft: 8 }}>Indoor Navigation</span>
        </div>
      </div>

      <div className="header-actions">
        {activeBuilding && (
          <div className="secondary-action-btn" style={{ padding: '6px 12px', fontSize: '0.8rem', cursor: 'default' }}>
            <Building size={14} className="text-muted" />
            <span>{activeBuilding.name}</span>
          </div>
        )}

        <button
          className="primary-action-btn"
          onClick={onOpenScanner}
          style={{ padding: '8px 14px', fontSize: '0.88rem' }}
          title="Scan QR code at your current location"
        >
          <QrCode size={16} />
          <span>Scan Location</span>
        </button>
      </div>
    </header>
  );
}
