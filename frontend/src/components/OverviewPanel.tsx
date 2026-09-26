import type { ProjectSummary, TechnologyDetection } from '../types/knowledge';

interface Props {
  summary: ProjectSummary;
  technologies: TechnologyDetection[];
}

export default function OverviewPanel({ summary, technologies }: Props) {
  const uniqueTechs = Array.from(new Map(technologies.map(t => [t.name, t])).values());

  return (
    <div className="overview-panel">
      <div className="overview-header">
        <h2 className="overview-name">{summary.name}</h2>
        <a href={summary.repository_url} target="_blank" rel="noreferrer" className="overview-url">
          {summary.repository_url}
        </a>
      </div>

      <div className="stats-grid">
        <StatCard label="Files" value={summary.file_count} />
        <StatCard label="Dependencies" value={summary.dependency_count} />
        <StatCard label="Technologies" value={summary.technology_count} />
      </div>

      {uniqueTechs.length > 0 && (
        <div className="overview-section">
          <h3 className="section-title">Languages &amp; Frameworks</h3>
          <div className="chip-list">
            {uniqueTechs.map(t => (
              <span key={t.name} className="chip">{t.name}</span>
            ))}
          </div>
        </div>
      )}

      <div className="overview-section">
        <h3 className="section-title">Details</h3>
        <dl className="detail-list">
          <dt>Status</dt>
          <dd>{summary.status}</dd>
          <dt>Created</dt>
          <dd>{new Date(summary.created_at).toLocaleString()}</dd>
          <dt>Project ID</dt>
          <dd><code>{summary.project_id}</code></dd>
        </dl>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat-card">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
