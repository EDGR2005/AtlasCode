const API = '';

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
};
