import type { SessionMetrics } from '../types/knowledge';

interface Props {
  session: SessionMetrics;
}

const STATE_LABEL: Record<string, string> = {
  IDLE: 'Idle',
  BRANCHING: 'Creating branch…',
  GUIDING: 'Waiting for your changes…',
  TESTING: 'Running tests…',
  DONE: 'Done',
  FAILED: 'Failed',
};

const STATE_COLOR: Record<string, string> = {
  IDLE: 'var(--text-muted)',
  BRANCHING: 'var(--warning)',
  GUIDING: 'var(--accent)',
  TESTING: 'var(--accent)',
  DONE: 'var(--success)',
  FAILED: 'var(--error)',
};

export default function VerificationLoop({ session }: Props) {
  const isRunning = !['DONE', 'FAILED', 'IDLE'].includes(session.state);

  return (
    <div className="verif-panel">
      <div className="verif-state" style={{ color: STATE_COLOR[session.state] }}>
        {isRunning && <span className="spinner" style={{ marginRight: 8 }} />}
        {STATE_LABEL[session.state] ?? session.state}
      </div>

      <div className="verif-metrics">
        <div className="verif-metric">
          <span className="verif-metric-val" style={{ color: 'var(--success)' }}>{session.tests_passed}</span>
          <span className="verif-metric-lbl">passed</span>
        </div>
        <div className="verif-metric">
          <span className="verif-metric-val" style={{ color: session.tests_failed > 0 ? 'var(--error)' : 'var(--text-muted)' }}>
            {session.tests_failed}
          </span>
          <span className="verif-metric-lbl">failed</span>
        </div>
        <div className="verif-metric">
          <span className="verif-metric-val">{session.fix_attempts}</span>
          <span className="verif-metric-lbl">fix attempts</span>
        </div>
      </div>

      {session.attempts.length > 0 && (
        <div className="verif-attempts">
          {session.attempts.map(att => (
            <div
              key={att.attempt}
              className={`verif-attempt ${att.result.failed === 0 && !att.result.timed_out ? 'verif-attempt--pass' : 'verif-attempt--fail'}`}
            >
              <div className="verif-attempt-header">
                <span>Attempt {att.attempt}</span>
                <span>
                  {att.result.timed_out
                    ? '⏱ timed out'
                    : `${att.result.passed} passed · ${att.result.failed} failed`}
                </span>
                <span className="verif-attempt-dur">{att.result.duration_seconds.toFixed(1)}s</span>
              </div>
              {att.result.output && (
                <pre className="verif-output">{att.result.output.slice(0, 1000)}</pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
