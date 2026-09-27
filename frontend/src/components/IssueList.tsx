import type { IssueAnalysis } from '../types/knowledge';

interface Props {
  issues: IssueAnalysis[];
  onSelect: (issue: IssueAnalysis) => void;
  loading: boolean;
}

const SCOPE_COLOR: Record<string, string> = {
  small: 'var(--success)',
  medium: 'var(--warning)',
  large: 'var(--error)',
  unknown: 'var(--text-muted)',
};

const TYPE_LABEL: Record<string, string> = {
  bug: '🐛 Bug',
  docs: '📄 Docs',
  feature: '✨ Feature',
  refactor: '🔧 Refactor',
  unknown: 'Issue',
};

export default function IssueList({ issues, onSelect, loading }: Props) {
  if (loading) {
    return (
      <div className="panel-loading">
        <span className="spinner" /> Fetching GitHub issues…
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div className="contrib-empty">
        <p>No open issues found for this repository.</p>
        <p className="contrib-hint">Make sure the repository has open GitHub issues and your GITHUB_TOKEN is set if needed.</p>
      </div>
    );
  }

  return (
    <div className="issue-list">
      {issues.map(issue => (
        <button
          key={issue.issue_number}
          className="issue-card"
          onClick={() => onSelect(issue)}
          type="button"
        >
          <div className="issue-card-header">
            <span className="issue-number">#{issue.issue_number}</span>
            <span className="issue-type">{TYPE_LABEL[issue.type] ?? issue.type}</span>
            <span
              className="issue-scope"
              style={{ color: SCOPE_COLOR[issue.scope] ?? 'var(--text-muted)' }}
            >
              {issue.scope}
            </span>
          </div>
          <div className="issue-title">{issue.title}</div>
          <div className="issue-signals">
            {issue.reasons.slice(0, 2).map((r, i) => (
              <span key={i} className="issue-signal issue-signal--ok">✓ {r}</span>
            ))}
            {issue.concerns.slice(0, 1).map((c, i) => (
              <span key={i} className="issue-signal issue-signal--warn">⚠ {c}</span>
            ))}
          </div>
          {issue.labels.length > 0 && (
            <div className="issue-labels">
              {issue.labels.map(lbl => (
                <span key={lbl} className="issue-label">{lbl}</span>
              ))}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
