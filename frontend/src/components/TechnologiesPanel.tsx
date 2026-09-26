import type { TechnologyDetection } from '../types/knowledge';

interface Props {
  technologies: TechnologyDetection[];
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'var(--success)';
  if (confidence >= 0.7) return 'var(--warning)';
  return '#e07b39';
}

export default function TechnologiesPanel({ technologies }: Props) {
  if (technologies.length === 0) {
    return <p className="empty-state">No technologies detected.</p>;
  }

  return (
    <div className="tech-grid">
      {technologies.map((tech, i) => (
        <div key={`${tech.name}-${i}`} className="tech-card">
          <div className="tech-card-header">
            <span className="tech-name">{tech.name}</span>
            {tech.version ? (
              <span className="tech-version-badge">v{tech.version}</span>
            ) : (
              <span className="tech-version-badge tech-version-badge--unknown">version unknown</span>
            )}
          </div>
          <p className="tech-source">detected from <em>{tech.source}</em></p>
          <div className="confidence-bar-wrap" title={`Confidence: ${Math.round(tech.confidence * 100)}%`}>
            <div
              className="confidence-bar"
              style={{
                width: `${Math.round(tech.confidence * 100)}%`,
                background: confidenceColor(tech.confidence),
              }}
            />
          </div>
          <span className="confidence-label">{Math.round(tech.confidence * 100)}%</span>
        </div>
      ))}
    </div>
  );
}
