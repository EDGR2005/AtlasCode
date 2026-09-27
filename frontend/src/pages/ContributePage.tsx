import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/client';
import type {
  IssueAnalysis,
  ContributionPlan,
  SessionMetrics,
  ContributionSummary,
} from '../types/knowledge';
import IssueList from '../components/IssueList';
import ContributionPlanPanel from '../components/ContributionPlanPanel';
import VerificationLoop from '../components/VerificationLoop';
import DiffViewer from '../components/DiffViewer';
import ContributionSummaryPanel from '../components/ContributionSummaryPanel';
import GuidancePanel from '../components/GuidancePanel';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Stage =
  | 'idle'          // initial — show "Start" button
  | 'issues'        // fetching / showing issues
  | 'planning'      // generating plan for selected issue
  | 'plan'          // showing plan, waiting for user approval
  | 'guiding'       // wait for user changes
  | 'testing'       // running tests on demand
  | 'done'          // session DONE — show diff + commit + PR
  | 'failed';       // session FAILED

interface Props {
  projectId: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ContributePage({ projectId }: Props) {
  const [stage, setStage] = useState<Stage>('idle');
  const [error, setError] = useState<string | null>(null);

  const [issues, setIssues] = useState<IssueAnalysis[]>([]);
  const [selectedIssue, setSelectedIssue] = useState<IssueAnalysis | null>(null);
  const [plan, setPlan] = useState<ContributionPlan | null>(null);
  const [session, setSession] = useState<SessionMetrics | null>(null);
  const [summary, setSummary] = useState<ContributionSummary | null>(null);
  const [diff, setDiff] = useState<string>('');
  const [commitSha, setCommitSha] = useState<string | null>(null);

  const [loadingIssues, setLoadingIssues] = useState(false);
  const [loadingExecute, setLoadingExecute] = useState(false);
  const [committing, setCommitting] = useState(false);

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Stop polling on unmount
  useEffect(() => () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
  }, []);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleStart = useCallback(async () => {
    setError(null);
    setLoadingIssues(true);
    setStage('issues');
    try {
      const data: IssueAnalysis[] = await api.getIssues(projectId);
      setIssues(Array.isArray(data) ? data : []);
    } catch {
      setError('Failed to fetch issues. Check your GITHUB_TOKEN or network connection.');
      setStage('idle');
    } finally {
      setLoadingIssues(false);
    }
  }, [projectId]);

  const handleSelectIssue = useCallback(async (issue: IssueAnalysis) => {
    setSelectedIssue(issue);
    setStage('planning');
    try {
      const data: ContributionPlan = await api.getPlan(projectId, issue.issue_number);
      setPlan(data);
      setStage('plan');
    } catch {
      setError('Failed to generate contribution plan.');
      setStage('issues');
    }
  }, [projectId]);

  const handleApprovePlan = useCallback(async () => {
    if (!plan || !selectedIssue) return;
    setLoadingExecute(true);
    setStage('guiding'); // optimistically switch to guiding
    try {
      const s = await api.executeContribution(projectId, selectedIssue.issue_number, plan.branch_name);
      setSession(s);
      setStage('guiding');
    } catch {
      setError('Failed to start contribution execution.');
      setStage('plan');
    } finally {
      setLoadingExecute(false);
    }
  }, [plan, selectedIssue, projectId]);

  const handleRunTests = useCallback(async () => {
    setLoadingExecute(true);
    setStage('testing');
    try {
      const s = await api.runTests(projectId);
      setSession(s);
      if (s.state === 'DONE') {
        const [diffData, summaryData] = await Promise.all([
          api.getContributionDiff(projectId),
          api.getContributionSummary(projectId),
        ]);
        setDiff(diffData.diff ?? '');
        setSummary(summaryData);
        setStage('done');
      } else {
        setStage('guiding');
      }
    } catch {
      setError('Failed to run tests.');
      setStage('guiding');
    } finally {
      setLoadingExecute(false);
    }
  }, [projectId]);

  const handleShowSummary = useCallback(async () => {
    setLoadingExecute(true);
    try {
      const [diffData, summaryData] = await Promise.all([
        api.getContributionDiff(projectId),
        api.getContributionSummary(projectId), // We will probably have a backend error here if session state isn't DONE
      ]);
      setDiff(diffData.diff ?? '');
      setSummary(summaryData);
      setStage('done');
    } catch {
      setError('Failed to fetch summary (tests might not have run).');
    } finally {
      setLoadingExecute(false);
    }
  }, [projectId]);

  const handleCommit = useCallback(async (message: string, files: string[]) => {
    setCommitting(true);
    try {
      const data = await api.commitContribution(projectId, message, files);
      setCommitSha(data.sha ?? null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Commit failed.';
      setError(msg);
    } finally {
      setCommitting(false);
    }
  }, [projectId]);

  const handleBack = useCallback(() => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    setStage('issues');
    setSelectedIssue(null);
    setPlan(null);
    setSession(null);
    setSummary(null);
    setDiff('');
    setCommitSha(null);
    setError(null);
  }, []);

  const handleReset = useCallback(() => {
    if (pollTimer.current) clearInterval(pollTimer.current);
    setStage('idle');
    setIssues([]);
    setSelectedIssue(null);
    setPlan(null);
    setSession(null);
    setSummary(null);
    setDiff('');
    setCommitSha(null);
    setError(null);
  }, []);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="contrib-page">
      {/* Error banner */}
      {error && (
        <div className="dash-error-banner" style={{ marginBottom: 16 }}>
          {error}
          <button className="contrib-dismiss" onClick={() => setError(null)} type="button">✕</button>
        </div>
      )}

      {/* Breadcrumb */}
      {stage !== 'idle' && (
        <nav className="contrib-breadcrumb">
          <button className="contrib-crumb" onClick={handleReset} type="button">Contribute</button>
          {(stage === 'plan' || stage === 'planning' || stage === 'guiding' || stage === 'testing' || stage === 'done' || stage === 'failed') && selectedIssue && (
            <>
              <span className="contrib-crumb-sep">›</span>
              <button className="contrib-crumb" onClick={handleBack} type="button">
                #{selectedIssue.issue_number} {selectedIssue.title.slice(0, 40)}
              </button>
            </>
          )}
          {(stage === 'guiding' || stage === 'testing' || stage === 'done' || stage === 'failed') && (
            <>
              <span className="contrib-crumb-sep">›</span>
              <span className="contrib-crumb contrib-crumb--active">
                {stage === 'done' ? 'Results' : stage === 'failed' ? 'Failed' : stage === 'testing' ? 'Testing' : 'Guiding'}
              </span>
            </>
          )}
        </nav>
      )}

      {/* ── Stage: idle ── */}
      {stage === 'idle' && (
        <div className="contrib-start">
          <div className="contrib-start-icon">✦</div>
          <h2 className="contrib-start-title">Make your first contribution</h2>
          <p className="contrib-start-desc">
            AtlasCode will find open GitHub issues, identify the most approachable ones,
            map them to relevant code, and guide you through a complete contribution —
            from branch to pull request.
          </p>
          <button className="btn btn--primary btn--lg" onClick={handleStart} type="button">
            Find Issues
          </button>
        </div>
      )}

      {/* ── Stage: issues ── */}
      {(stage === 'issues' || stage === 'planning') && (
        <div className="contrib-section-wrap">
          <div className="contrib-section-header">
            <span className="section-title">Open issues</span>
            {!loadingIssues && issues.length > 0 && (
              <span className="contrib-hint">{issues.length} issue(s) — click one to generate a contribution plan</span>
            )}
          </div>
          <IssueList
            issues={issues}
            onSelect={handleSelectIssue}
            loading={loadingIssues || stage === 'planning'}
          />
        </div>
      )}

      {/* ── Stage: plan ── */}
      {stage === 'plan' && plan && (
        <ContributionPlanPanel
          plan={plan}
          loading={loadingExecute}
          onApprove={handleApprovePlan}
        />
      )}

      {/* ── Stage: guiding/testing ── */}
      {(stage === 'guiding' || stage === 'testing') && plan && (
        <div className="contrib-section-wrap">
          {session
            ? <GuidancePanel 
                projectId={projectId} 
                plan={plan} 
                session={session} 
                onRunTests={handleRunTests} 
                onShowSummary={handleShowSummary}
                loading={loadingExecute} 
              />
            : <div className="panel-loading"><span className="spinner" /> Loading guidance…</div>
          }
        </div>
      )}

      {/* ── Stage: done ── */}
      {stage === 'done' && summary && (
        <div className="contrib-section-wrap">
          <ContributionSummaryPanel
            summary={summary}
            onCommit={handleCommit}
            committing={committing}
            commitSha={commitSha}
          />
          <div className="contrib-section" style={{ marginTop: 24 }}>
            <div className="section-title">Diff</div>
            <DiffViewer diff={diff} />
          </div>
          {session && (
            <div className="contrib-section" style={{ marginTop: 24 }}>
              <div className="section-title">Verification details</div>
              <VerificationLoop session={session} />
            </div>
          )}
        </div>
      )}

      {/* ── Stage: failed ── */}
      {stage === 'failed' && (
        <div className="contrib-section-wrap">
          <div className="contrib-failed">
            <span className="contrib-failed-icon">✕</span>
            <div>
              <strong>Contribution loop failed</strong>
              <p>Tests did not pass after {session?.fix_attempts ?? 0} fix attempt(s).</p>
              {session && <VerificationLoop session={session} />}
            </div>
          </div>
          <button className="btn btn--secondary" onClick={handleBack} type="button" style={{ marginTop: 16 }}>
            ← Try another issue
          </button>
        </div>
      )}
    </div>
  );
}
