import { useState } from 'react';
import type { ContributionSummary } from '../types/knowledge';

interface Props {
  summary: ContributionSummary;
  onCommit: (message: string, files: string[]) => void;
  committing: boolean;
  commitSha: string | null;
}

export default function ContributionSummaryPanel({ summary, onCommit, committing, commitSha }: Props) {
  const metrics = summary.metrics;
  const [commitMsg, setCommitMsg] = useState(
    `fix: address issue #${summary.issue_number} — ${summary.issue_title || 'contribution'}\n\nCloses #${summary.issue_number}`
  );
  const [showPr, setShowPr] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(
    new Set(metrics?.changed_files || [])
  );

  const toggleFile = (f: string) => {
    const next = new Set(selectedFiles);
    if (next.has(f)) next.delete(f);
    else next.add(f);
    setSelectedFiles(next);
  };

  const copyPrDraft = () => {
    navigator.clipboard.writeText(summary.pr_draft);
  };

  return (
    <div className="summary-panel">
      <div className="summary-header">
        <span className="summary-title">Contribution ready for review</span>
        <span className="summary-badge summary-badge--done">DONE</span>
      </div>

      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-card-label">Issue</div>
          <div className="summary-card-val">#{summary.issue_number} {summary.issue_title}</div>
        </div>
        <div className="summary-card">
          <div className="summary-card-label">Branch</div>
          <code className="contrib-branch">{summary.branch_name}</code>
        </div>
        <div className="summary-card">
          <div className="summary-card-label">Changes</div>
          <div className="summary-card-val">{summary.diff_stat || '—'}</div>
        </div>
        {metrics && (
          <>
            <div className="summary-card">
              <div className="summary-card-label">Tests passed</div>
              <div className="summary-card-val" style={{ color: 'var(--success)' }}>{metrics.tests_passed}</div>
            </div>
            <div className="summary-card">
              <div className="summary-card-label">Tests failed</div>
              <div className="summary-card-val" style={{ color: metrics.tests_failed > 0 ? 'var(--error)' : 'var(--text-muted)' }}>
                {metrics.tests_failed}
              </div>
            </div>
            <div className="summary-card">
              <div className="summary-card-label">Test runs</div>
              <div className="summary-card-val">{metrics.test_runs}</div>
            </div>
          </>
        )}
      </div>

      {/* Commit section */}
      {!commitSha ? (
        <div className="contrib-section">
          <div className="section-title">Files to commit</div>
          {metrics?.changed_files && metrics.changed_files.length > 0 ? (
            <div className="contrib-files" style={{ marginBottom: 16 }}>
              {metrics.changed_files.map(f => (
                <label key={f} className="guidance-step" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedFiles.has(f)}
                    onChange={() => toggleFile(f)}
                  />
                  <code>{f}</code>
                </label>
              ))}
            </div>
          ) : (
            <div className="contrib-hint" style={{ marginBottom: 16 }}>No changed files detected.</div>
          )}
          
          <div className="section-title">Commit message</div>
          <textarea
            className="commit-msg-input"
            value={commitMsg}
            onChange={e => setCommitMsg(e.target.value)}
            rows={4}
          />
          <div className="contrib-approve-row">
            <button
              className="btn btn--primary"
              onClick={() => onCommit(commitMsg, Array.from(selectedFiles))}
              disabled={committing || !commitMsg.trim() || selectedFiles.size === 0}
              type="button"
            >
              {committing ? <><span className="spinner" /> Committing…</> : 'Commit Changes'}
            </button>
            <span className="contrib-approve-hint">Commits locally only — nothing is pushed.</span>
          </div>
        </div>
      ) : (
        <div className="contrib-section">
          <div className="summary-commit-done">
            ✓ Committed: <code>{commitSha.slice(0, 7)}</code>
          </div>
          <div style={{ marginTop: 16 }}>
            <div className="section-title">Next steps</div>
            <p>Push your branch to the remote repository:</p>
            <pre className="pr-draft-pre">
              git push -u origin {summary.branch_name}
            </pre>
          </div>
        </div>
      )}

      {/* PR Draft section */}
      <div className="contrib-section">
        <div style={{ display: 'flex', gap: 16 }}>
          <button
            className="btn btn--secondary"
            onClick={() => setShowPr(v => !v)}
            type="button"
          >
            {showPr ? 'Hide PR Draft' : 'View PR Draft'}
          </button>
          {showPr && (
            <button
              className="btn btn--secondary"
              onClick={copyPrDraft}
              type="button"
            >
              Copy to Clipboard
            </button>
          )}
        </div>
        {showPr && (
          <pre className="pr-draft-pre">{summary.pr_draft}</pre>
        )}
      </div>
    </div>
  );
}
