const API = import.meta.env.VITE_API_URL || '';

export const api = {
  analyze: (repositoryUrl: string) =>
    fetch(`${API}/projects/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repository_url: repositoryUrl }),
    }).then(r => r.json()),

  getProject: (projectId: string) =>
    fetch(`${API}/projects/${projectId}`).then(r => r.json()),

  listProjects: () =>
    fetch(`${API}/projects/`).then(r => r.json()),

  getTree: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/tree`).then(r => r.json()),

  getTechnologies: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/technologies`).then(r => r.json()),

  getDependencies: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/dependencies`).then(r => r.json()),

  getArchitecture: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/architecture`).then(r => r.json()),

  getDatabase: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/database`).then(r => r.json()),

  // ── Contribution Agent (Phase 2) ──────────────────────────────────────────

  getIssues: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/contribute/issues`, { method: 'POST' })
      .then(r => r.json()),

  getPlan: (projectId: string, issueNumber: number) =>
    fetch(`${API}/projects/${projectId}/contribute/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ issue_number: issueNumber }),
    }).then(r => r.json()),

  executeContribution: (projectId: string, issueNumber: number, branchName: string) =>
    fetch(`${API}/projects/${projectId}/contribute/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ issue_number: issueNumber, branch_name: branchName }),
    }).then(r => r.json()),

  runTests: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/contribute/run-tests`, { method: 'POST' })
      .then(r => r.json()),

  getChangedFiles: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/contribute/changed-files`)
      .then(r => r.json()),

  getContributionStatus: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/contribute/status`).then(r => r.json()),

  getContributionDiff: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/contribute/diff`).then(r => r.json()),

  commitContribution: (projectId: string, message: string, files: string[] = []) =>
    fetch(`${API}/projects/${projectId}/contribute/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, files }),
    }).then(r => r.json()),

  getContributionSummary: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/contribute/summary`).then(r => r.json()),

  getPrDraft: (projectId: string) =>
    fetch(`${API}/projects/${projectId}/contribute/pr-draft`).then(r => r.json()),
};
