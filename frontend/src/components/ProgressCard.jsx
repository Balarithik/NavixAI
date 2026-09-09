import React from 'react';
import { Award, CheckCircle2, Circle, ChevronRight, Zap, ArrowUpDown } from 'lucide-react';

export default function ProgressCard({
  route,
  currentStepIndex,
  onStepNext,
  onResetProgress,
  onDestinationReached,
}) {
  if (!route || !route.checkpoints || route.checkpoints.length === 0) return null;

  const totalCheckpoints = route.checkpoints.length;
  const progressPercent = Math.min(
    100,
    Math.round(((currentStepIndex + 1) / totalCheckpoints) * 100)
  );

  const currentCp = route.checkpoints[currentStepIndex] || route.checkpoints[0];
  const distanceCompleted = currentCp.distance_from_start;
  const distanceRemaining = Math.max(0, Math.round(route.distanceMetres - distanceCompleted));

  const isComplete = currentStepIndex >= totalCheckpoints - 1;

  const handleNext = () => {
    if (currentStepIndex < totalCheckpoints - 1) {
      const nextIdx = currentStepIndex + 1;
      onStepNext(nextIdx);
      if (nextIdx === totalCheckpoints - 1) {
        onDestinationReached();
      }
    }
  };

  return (
    <div className="progress-card">
      <div className="progress-header">
        <div className="progress-title">
          <Award size={18} color="#2563EB" />
          <span>Navigation Progress</span>
        </div>
        <span className="progress-percent-badge">{progressPercent}%</span>
      </div>

      {/* Progress Track */}
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
      </div>

      {/* Distance Progress Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        <span>
          <strong style={{ color: 'var(--text-main)' }}>{distanceCompleted}m</strong> completed
        </span>
        <span>
          <strong style={{ color: 'var(--text-main)' }}>{distanceRemaining}m</strong> remaining
        </span>
      </div>

      {/* Checkpoint list timeline */}
      <div className="checkpoint-timeline">
        {route.checkpoints.map((cp, idx) => {
          const isPassed = idx < currentStepIndex;
          const isCurrent = idx === currentStepIndex;
          const isPending = idx > currentStepIndex;

          let rowClass = 'checkpoint-row ';
          if (isPassed) rowClass += 'passed';
          else if (isCurrent) rowClass += 'active';
          else rowClass += 'pending';

          return (
            <div key={`cp-${cp.node_id}-${idx}`} className={rowClass}>
              <div className="checkpoint-info">
                {isPassed ? (
                  <CheckCircle2 size={16} color="#10B981" />
                ) : isCurrent ? (
                  <Circle size={16} color="#2563EB" fill="#2563EB" />
                ) : (
                  <Circle size={16} color="#CBD5E1" />
                )}
                <span>
                  {cp.is_start ? 'Start: ' : cp.is_destination ? '🎯 Destination: ' : ''}
                  {cp.name}
                  <span style={{ fontSize: '0.72rem', opacity: 0.75, marginLeft: 4 }}>
                    (Floor {cp.floor})
                  </span>
                </span>
              </div>

              <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>
                {isPassed ? 'Passed' : isCurrent ? 'Here Now' : `${cp.distance_from_start}m`}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Simulator Controls */}
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        {!isComplete ? (
          <button
            className="primary-action-btn"
            onClick={handleNext}
            style={{ flex: 1, padding: '10px 14px', fontSize: '0.88rem' }}
          >
            <Zap size={16} />
            <span>Simulate Step Checkpoint</span>
            <ChevronRight size={16} />
          </button>
        ) : (
          <button
            className="secondary-action-btn"
            onClick={onResetProgress}
            style={{ flex: 1, padding: '10px 14px', fontSize: '0.88rem' }}
          >
            Restart Route
          </button>
        )}
      </div>
    </div>
  );
}
