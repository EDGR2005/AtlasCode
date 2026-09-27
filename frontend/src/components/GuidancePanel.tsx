import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { ContributionPlan, SessionMetrics } from '../types/knowledge';

interface Props {
  projectId: string;
  plan: ContributionPlan;
  session: SessionMetrics;
  onRunTests: () => void;
  onShowSummary: () => void;
  loading: boolean;
}

export default function GuidancePanel({ projectId, plan, session, onRunTests, onShowSummary, loading }: Props) {
  const [changedFiles, setChangedFiles] = useState<string[]>(session.changed_files || []);
  const [refreshing, setRefreshing] = useState(false);
  const [checkedSteps, setCheckedSteps] = useState<Set<number>>(new Set([4])); // 4 is branch created

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const data = await api.getChangedFiles(projectId);
      setChangedFiles(data.changed_files || []);
    } catch (e) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    setChangedFiles(session.changed_files || []);
  }, [session.changed_files]);

  const toggleStep = (index: number) => {
    const next = new Set(checkedSteps);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setCheckedSteps(next);
  };

  const copyBranch = () => {
    navigator.clipboard.writeText(`git checkout ${plan.branch_name}`);
  };

  const lastAttempt = session.attempts[session.attempts.length - 1];

  return (
    <div className="guidance-panel">
      {/* Workspace Info */}
      <div className="contrib-section guidance-workspace">
        <div className="section-title">📁 Your workspace</div>
        <div className="guidance-workspace-info">
          <div><strong>Path:</strong> <code>{plan.repo_path}</code></div>
          <div><strong>Branch:</strong> <code>{plan.branch_name}</code></div>
          <button className="btn btn--secondary btn--sm" onClick={copyBranch} type="button" style={{ marginTop: 8 }}>
            Copy git checkout command
          </button>
        </div>
      </div>

      {/* Checklist */}
      <div className="contrib-section guidance-checklist">
        <div className="section-title">📋 Contribution Checklist</div>
        <div className="contrib-steps">
          {plan.steps.map(step => (
            <label key={step.index} className="guidance-step">
              <input 
                type="checkbox" 
                checked={checkedSteps.has(step.index)} 
                onChange={() => toggleStep(step.index)} 
              />
              <span className={`guidance-step-desc ${checkedSteps.has(step.index) ? 'guidance-step-done' : ''}`}>
                {step.index}. {step.description}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Relevant Files and Tests */}
      <div className="contrib-section guidance-files">
        <div className="section-title">📄 Files to edit</div>
        {plan.relevant_files.length > 0 ? (
          <ul className="guidance-file-list">
            {plan.relevant_files.map(f => (
              <li key={f.path}>
                <code>{f.path}</code> — <span className="contrib-file-reason">{f.reason}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="contrib-hint">No specific files identified.</div>
        )}
        
        <div className="section-title" style={{ marginTop: 16 }}>🧪 Where to put tests</div>
        <div className="guidance-test-info">
          <div><strong>Suggestion:</strong> <code>{plan.test_file_hint}</code></div>
          <div><strong>Command:</strong> <code>{plan.test_command}</code></div>
        </div>
      </div>

      {/* Changed Files */}
      <div className="contrib-section guidance-changes">
        <div className="section-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>✏️ Your changes so far</span>
          <button className="btn btn--secondary btn--sm" onClick={handleRefresh} disabled={refreshing} type="button">
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        {changedFiles.length > 0 ? (
          <ul className="guidance-file-list">
            {changedFiles.map(f => (
              <li key={f}><code>{f}</code></li>
            ))}
          </ul>
        ) : (
          <div className="contrib-hint">No changes detected yet in the working tree.</div>
        )}
      </div>

      {/* Test History */}
      {lastAttempt && (
        <div className="contrib-section guidance-test-history">
          <div className="section-title">
            📊 Previous test run (Attempt #{lastAttempt.attempt})
            <span style={{ marginLeft: 8, color: lastAttempt.result.failed === 0 ? 'var(--success)' : 'var(--error)' }}>
              {lastAttempt.result.failed === 0 ? '✓ Passed' : '✕ Failed'}
            </span>
          </div>
          <div className="contrib-hint">
            {lastAttempt.result.passed} passed · {lastAttempt.result.failed} failed · {lastAttempt.result.errors} errors
          </div>
          {lastAttempt.result.output && (
             <details style={{ marginTop: 8 }}>
               <summary style={{ cursor: 'pointer', color: 'var(--accent)' }}>Show output</summary>
               <pre className="verif-output">{lastAttempt.result.output}</pre>
             </details>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="guidance-actions" style={{ marginTop: 24, display: 'flex', gap: 16 }}>
        <button className="btn btn--primary" onClick={onRunTests} disabled={loading} type="button">
          {loading ? <><span className="spinner" /> Running...</> : '🧪 Run Tests'}
        </button>
        <button className="btn btn--secondary" onClick={onShowSummary} disabled={loading} type="button">
          📝 I'm Done, Show Summary
        </button>
      </div>
    </div>
  );
}
