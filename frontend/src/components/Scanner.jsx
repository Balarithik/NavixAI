import React, { useEffect, useRef, useState } from 'react';
import { BrowserQRCodeReader } from '@zxing/browser';
import { Camera, X, AlertCircle, RefreshCw, CheckCircle2, Search } from 'lucide-react';
import { api } from '../services/api';

export default function Scanner({ isOpen, onClose, onLocationDetected, allNodes = [] }) {
  const [hasCamera, setHasCamera] = useState(true);
  const [cameraError, setCameraError] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [manualCode, setManualCode] = useState('');
  const [processing, setProcessing] = useState(false);
  const videoRef = useRef(null);
  const controlsRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      stopCamera();
      return;
    }

    startCamera();

    return () => {
      stopCamera();
    };
  }, [isOpen]);

  const startCamera = async () => {
    setCameraError(null);
    setScanning(true);
    try {
      const codeReader = new BrowserQRCodeReader();
      const videoInputDevices = await BrowserQRCodeReader.listVideoInputDevices();

      if (!videoInputDevices || videoInputDevices.length === 0) {
        setHasCamera(false);
        setCameraError('No camera found on this device. Use manual QR selection below.');
        setScanning(false);
        return;
      }

      setHasCamera(true);
      const selectedDeviceId = videoInputDevices[0].deviceId;

      if (videoRef.current) {
        const controls = await codeReader.decodeFromVideoDevice(
          selectedDeviceId,
          videoRef.current,
          (result, error) => {
            if (result) {
              handlePayload(result.getText());
            }
          }
        );
        controlsRef.current = controls;
      }
    } catch (err) {
      console.warn('Camera access error:', err);
      setHasCamera(false);
      setCameraError('Camera access denied or unavailable. Use the simulator or manual code below.');
      setScanning(false);
    }
  };

  const stopCamera = () => {
    if (controlsRef.current) {
      try {
        controlsRef.current.stop();
      } catch (e) {
        // ignore
      }
      controlsRef.current = null;
    }
    setScanning(false);
  };

  const handlePayload = async (payload) => {
    if (!payload || processing) return;
    setProcessing(true);
    try {
      const data = await api.scanQRCode(payload);
      if (data.valid) {
        stopCamera();
        onLocationDetected(data);
        onClose();
      } else {
        alert(data.error || 'Invalid QR code');
      }
    } catch (err) {
      alert(err.message || 'Could not validate QR code');
    } finally {
      setProcessing(false);
    }
  };

  const handleSimulatedScan = () => {
    if (!selectedNodeId) return;
    const node = allNodes.find((n) => n.node_id === selectedNodeId);
    if (node) {
      handlePayload(node.qr_code || `NAVIXAI:${node.node_id}`);
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (manualCode.trim()) {
      handlePayload(manualCode.trim());
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content-card" style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Camera size={20} className="text-primary" />
            <h3 style={{ fontSize: '1.1rem' }}>Scan Location QR</h3>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '75vh', overflowY: 'auto' }}>
          {/* Camera Viewfinder */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: 220,
              backgroundColor: '#0F172A',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {hasCamera ? (
              <video
                ref={videoRef}
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                muted
                playsInline
              />
            ) : null}

            {/* Target Reticle Overlay */}
            <div
              style={{
                position: 'absolute',
                width: 140,
                height: 140,
                border: '2px dashed rgba(59, 130, 246, 0.8)',
                borderRadius: 'var(--radius-md)',
                pointerEvents: 'none',
                boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.45)',
              }}
            />

            {cameraError && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundColor: 'rgba(15, 23, 42, 0.85)',
                  color: '#CBD5E1',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 16,
                  textAlign: 'center',
                  fontSize: '0.84rem',
                  gap: 8,
                }}
              >
                <AlertCircle size={24} color="#F59E0B" />
                <span>{cameraError}</span>
              </div>
            )}
          </div>

          {/* Quick Simulator Picker (Ideal for laptops & instant testing) */}
          <div
            style={{
              padding: 14,
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                TEST SIMULATOR (SELECT ANY LOCATION)
              </span>
              <span className="brand-badge" style={{ fontSize: '0.65rem' }}>Instant Test</span>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={selectedNodeId}
                onChange={(e) => setSelectedNodeId(e.target.value)}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-medium)',
                  background: '#FFFFFF',
                  fontSize: '0.88rem',
                }}
              >
                <option value="">-- Choose a location to simulate scan --</option>
                {allNodes.map((n) => (
                  <option key={n.node_id} value={n.node_id}>
                    Floor {n.floor_number}: {n.name} ({n.type})
                  </option>
                ))}
              </select>

              <button
                className="primary-action-btn"
                onClick={handleSimulatedScan}
                disabled={!selectedNodeId || processing}
                style={{ padding: '8px 14px', fontSize: '0.85rem' }}
              >
                {processing ? <RefreshCw className="animate-spin" size={14} /> : <CheckCircle2 size={14} />}
                <span>Simulate</span>
              </button>
            </div>
          </div>

          {/* Manual text code input */}
          <form onSubmit={handleManualSubmit} style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              placeholder="Or enter QR code payload (e.g. CAMPUSNAV:F1_N01)"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.85rem',
                background: 'var(--bg-elevated)',
              }}
            />
            <button
              type="submit"
              className="secondary-action-btn"
              disabled={!manualCode.trim() || processing}
            >
              Verify
            </button>
          </form>
        </div>

        <div className="modal-footer">
          <button className="secondary-action-btn" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
