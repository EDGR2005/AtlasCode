import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import type {
  ProjectSummary,
  TechnologyDetection,
  Dependency,
  FileEntry,
  Component,
  Relationship,
  DatabaseSchema,
} from '../types/knowledge';
import OverviewPanel from '../components/OverviewPanel';
import TechnologiesPanel from '../components/TechnologiesPanel';
import DependenciesPanel from '../components/DependenciesPanel';
import RepositoryPanel from '../components/RepositoryPanel';
import ArchitectureGraph from '../components/ArchitectureGraph';
import DatabasePanel from '../components/DatabasePanel';

type Tab = 'overview' | 'technologies' | 'dependencies' | 'architecture' | 'repository' | 'database';

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'technologies', label: 'Technologies' },
  { id: 'dependencies', label: 'Dependencies' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'repository', label: 'Repository' },
  { id: 'database', label: 'Database' },
];

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [error, setError] = useState<string | null>(null);

  // Lazy per-tab data
  const [technologies, setTechnologies] = useState<TechnologyDetection[] | null>(null);
  const [dependencies, setDependencies] = useState<Dependency[] | null>(null);
  const [files, setFiles] = useState<FileEntry[] | null>(null);
  const [components, setComponents] = useState<Component[] | null>(null);
  const [relationships, setRelationships] = useState<Relationship[] | null>(null);
  const [dbSchema, setDbSchema] = useState<DatabaseSchema | null>(null);

  // Track which tabs have been fetched
  const fetched = useRef<Set<Tab>>(new Set());
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Polling until ready/error
  useEffect(() => {
    if (!projectId) return;

    async function poll() {
      try {
        const data: ProjectSummary = await api.getProject(projectId!);
        setSummary(data);
        if (data.status === 'ready' || data.status === 'error') {
          if (pollTimer.current) clearInterval(pollTimer.current);
          if (data.status === 'error') {
            setError(data.error_message ?? 'Analysis failed.');
          }
        }
      } catch {
        setError('Failed to fetch project status.');
        if (pollTimer.current) clearInterval(pollTimer.current);
      }
    }

    poll();
    pollTimer.current = setInterval(poll, 2000);
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [projectId]);

  // Lazy-fetch tab data when a tab is first activated (only when ready)
  useEffect(() => {
    if (!projectId || !summary || summary.status !== 'ready') return;
    if (fetched.current.has(activeTab)) return;
    fetched.current.add(activeTab);

    switch (activeTab) {
      case 'technologies':
        api.getTechnologies(projectId)
          .then((d: { technologies: TechnologyDetection[] }) => setTechnologies(d.technologies ?? []))
          .catch(() => setTechnologies([]));
        break;
      case 'dependencies':
        api.getDependencies(projectId)
          .then((d: { dependencies: Dependency[] }) => setDependencies(d.dependencies ?? []))
          .catch(() => setDependencies([]));
        break;
      case 'repository':
        api.getTree(projectId)
          .then((d: { files: FileEntry[] }) => setFiles(d.files ?? []))
          .catch(() => setFiles([]));
        break;
      case 'architecture':
        api.getArchitecture(projectId)
          .then((d: { components: Component[]; relationships: Relationship[] }) => {
            setComponents(d.components ?? []);
            setRelationships(d.relationships ?? []);
          })
          .catch(() => { setComponents([]); setRelationships([]); });
        break;
      case 'database':
        api.getDatabase(projectId)
          .then((d: DatabaseSchema) => setDbSchema(d))
          .catch(() => setDbSchema({ tables: [], relationships: [], detected: false }));
        break;
      case 'overview':
        // Also pre-fetch technologies for the overview chips
        if (!fetched.current.has('technologies')) {
          fetched.current.add('technologies');
          api.getTechnologies(projectId)
            .then((d: { technologies: TechnologyDetection[] }) => setTechnologies(d.technologies ?? []))
            .catch(() => setTechnologies([]));
        }
        break;
    }
  }, [activeTab, summary, projectId]);

  const isLoading = !summary || summary.status === 'pending' || summary.status === 'analyzing';

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dash-header">
        <Link to="/" className="dash-back">← CodeAtlas</Link>
        <div className="dash-title">
          <span className="dash-name">{summary?.name ?? projectId}</span>
          {summary && <StatusBadge status={summary.status} />}
        </div>
        {summary && (
          <a className="dash-repo-link" href={summary.repository_url} target="_blank" rel="noreferrer">
            {summary.repository_url}
          </a>
        )}
      </header>

      {/* Error banner */}
      {error && <div className="dash-error-banner">{error}</div>}

      {/* Loading state */}
      {isLoading && !error && (
        <div className="dash-loading">
          <span className="spinner spinner--lg" />
          <p>Analyzing repository…</p>
        </div>
      )}

      {/* Dashboard content */}
      {!isLoading && summary && (
        <>
          <nav className="dash-tabs">
            {TABS.map(tab => (
              <button
                key={tab.id}
                className={`dash-tab${activeTab === tab.id ? ' dash-tab--active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <main className="dash-content">
            {activeTab === 'overview' && (
              <OverviewPanel summary={summary} technologies={technologies ?? []} />
            )}
            {activeTab === 'technologies' && (
              technologies === null
                ? <div className="panel-loading"><span className="spinner" /> Loading…</div>
                : <TechnologiesPanel technologies={technologies} />
            )}
            {activeTab === 'dependencies' && (
              dependencies === null
                ? <div className="panel-loading"><span className="spinner" /> Loading…</div>
                : <DependenciesPanel dependencies={dependencies} />
            )}
            {activeTab === 'architecture' && (
              components === null || relationships === null
                ? <div className="panel-loading"><span className="spinner" /> Loading…</div>
                : <ArchitectureGraph components={components} relationships={relationships} />
            )}
            {activeTab === 'repository' && (
              files === null
                ? <div className="panel-loading"><span className="spinner" /> Loading…</div>
                : <RepositoryPanel files={files} />
            )}
            {activeTab === 'database' && (
              dbSchema === null
                ? <div className="panel-loading"><span className="spinner" /> Loading…</div>
                : <DatabasePanel schema={dbSchema} />
            )}
          </main>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: ProjectSummary['status'] }) {
  const colorMap: Record<ProjectSummary['status'], string> = {
    ready: 'var(--success)',
    analyzing: 'var(--warning)',
    pending: 'var(--warning)',
    error: 'var(--error)',
  };
  return (
    <span className="status-badge" style={{ color: colorMap[status], borderColor: colorMap[status] }}>
      {status}
    </span>
  );
}
