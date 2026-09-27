import type { ContributionPlan } from '../types/knowledge';

interface Props {
  plan: ContributionPlan;
  loading: boolean;
  onApprove: () => void;
}

export default function ContributionPlanPanel({ plan, loading, onApprove }: Props) {
  return (
    <div className="contrib-plan">
      <div className="contrib-plan-meta">
        <div className="contrib-meta-item">
          <span className="contrib-meta-label">Issue</span>
          <span className="contrib-meta-value">#{plan.issue_number}</span>
        </div>
        <div className="contrib-meta-item">
          <span className="contrib-meta-label">Branch</span>
          <code className="contrib-branch">{plan.branch_name}</code>
        </div>
      </div>

      {plan.relevant_files.length > 0 && (
        <div className="contrib-section">
          <div className="section-title">Likely relevant files</div>
          <div className="contrib-files">
            {plan.relevant_files.map(f => (
              <div key={f.path} className="contrib-file">
                <span className="contrib-file-path">{f.path}</span>
                <span className="contrib-file-reason">{f.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="contrib-section">
        <div className="section-title">Contribution steps</div>
        <ol className="contrib-steps">
          {plan.steps.map(step => (
            <li key={step.index} className="contrib-step">
              <span className="contrib-step-num">{step.index}</span>
              <span className="contrib-step-desc">{step.description}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="contrib-approve-row">
        <button
          className="btn btn--primary"
          onClick={onApprove}
          disabled={loading}
          type="button"
        >
          {loading ? <><span className="spinner" /> Starting…</> : 'Create Branch & Begin'}
        </button>
        <span className="contrib-approve-hint">
          This will create the branch and start the guided contribution mode.
        </span>
      </div>
    </div>
  );
}
