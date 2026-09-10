import React, { useState, useRef, useEffect } from 'react';
import { MapPin, X, Check } from 'lucide-react';

export default function LocationSelector({
  label = "From",
  selectedNode,
  onSelectNode,
  nodes = [],
  placeholder = "Search start location...",
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const wrapperRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredNodes = nodes.filter((n) => {
    const q = searchTerm.toLowerCase();
    return (
      n.name.toLowerCase().includes(q) ||
      n.type.toLowerCase().includes(q) ||
      `floor ${n.floor_number}`.includes(q)
    );
  });

  const handleSelect = (node) => {
    onSelectNode(node);
    setIsOpen(false);
    setSearchTerm('');
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onSelectNode(null);
    setSearchTerm('');
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative' }}>
      <div
        className="search-field-group"
        onClick={() => setIsOpen(true)}
        style={{ cursor: 'pointer' }}
      >
        <div className="location-marker-dot dot-start" />
        <div className="search-field-content">
          <span className="field-label">{label}</span>
          {isOpen ? (
            <input
              autoFocus
              type="text"
              className="field-input-value"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Type room, office, lab..."
            />
          ) : (
            <span
              className="field-input-value"
              style={{ color: selectedNode ? 'var(--text-main)' : 'var(--text-light)' }}
            >
              {selectedNode ? `${selectedNode.name} (F${selectedNode.floor_number || selectedNode.floor})` : placeholder}
            </span>
          )}
        </div>

        {selectedNode && (
          <button className="icon-btn" onClick={handleClear} style={{ width: 26, height: 26 }} title="Clear" aria-label="Clear start location">
            <X size={14} />
          </button>
        )}
      </div>

      {isOpen && (
        <div
          className="animate-slide-up"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            backgroundColor: '#FFFFFF',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-xl)',
            border: '1px solid var(--border-subtle)',
            maxHeight: 280,
            overflowY: 'auto',
            zIndex: 50,
            padding: '6px',
          }}
        >
          {filteredNodes.length === 0 ? (
            <div style={{ padding: '12px 14px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              No matching locations found
            </div>
          ) : (
            filteredNodes.map((node) => {
              const isSelected = selectedNode?.node_id === node.node_id;
              return (
                <div
                  key={node.node_id}
                  onClick={() => handleSelect(node)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    backgroundColor: isSelected ? 'var(--color-primary-subtle)' : 'transparent',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <MapPin size={16} color={isSelected ? 'var(--color-primary)' : 'var(--text-muted)'} />
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        {node.name}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Floor {node.floor_number} • {node.type}
                      </div>
                    </div>
                  </div>
                  {isSelected && <Check size={16} color="var(--color-primary)" />}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
