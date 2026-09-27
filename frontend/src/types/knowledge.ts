export interface TechnologyDetection {
  name: string;
  version: string | null;
  source: string;
  confidence: number;
}

export interface Dependency {
  name: string;
  version: string | null;
  ecosystem: string;
  source: string;
}

export interface FileEntry {
  path: string;
  size_bytes: number;
  extension: string;
  is_important: boolean;
}

export interface Component {
  name: string;
  path: string;
  type: string;
}

export interface Relationship {
  from_component: string;
  to_component: string;
  type: string;
  confidence: number;
  inferred: boolean;
}

export interface ProjectSummary {
  project_id: string;
  name: string;
  status: 'pending' | 'analyzing' | 'ready' | 'error';
  repository_url: string;
  created_at: string;
  technology_count: number;
  dependency_count: number;
  file_count: number;
  error_message: string | null;
}

// ── Contribution Agent types (Phase 2) ──────────────────────────────────────

export interface IssueAnalysis {
  issue_number: number;
  title: string;
  type: 'bug' | 'docs' | 'feature' | 'refactor' | 'unknown';
  scope: 'small' | 'medium' | 'large' | 'unknown';
  reasons: string[];
  concerns: string[];
  labels: string[];
  url: string;
}

export interface RelevantFile {
  path: string;
  reason: string;
  inferred: boolean;
}

export interface ContributionStep {
  index: number;
  description: string;
}

export interface ContributionPlan {
  issue_number: number;
  branch_name: string;
  relevant_files: RelevantFile[];
  steps: ContributionStep[];
  approved: boolean;
  repo_path: string;
  test_command: string;
  test_file_hint: string;
}

export interface SuiteResult {
  passed: number;
  failed: number;
  errors: number;
  output: string;
  duration_seconds: number;
  timed_out: boolean;
}

export interface VerificationAttempt {
  attempt: number;
  result: SuiteResult;
}

export interface SessionMetrics {
  project_id: string;
  issue_number: number;
  branch_name: string;
  state: 'IDLE' | 'BRANCHING' | 'GUIDING' | 'TESTING' | 'DONE' | 'FAILED';
  files_analyzed: number;
  files_modified: number;
  changed_files: string[];
  tests_run: number;
  tests_passed: number;
  tests_failed: number;
  fix_attempts: number;
  test_runs: number;
  attempts: VerificationAttempt[];
  started_at: string;
  finished_at: string | null;
}

export interface ContributionSummary {
  issue_number: number;
  issue_title: string;
  branch_name: string;
  commit_sha: string | null;
  diff_stat: string;
  pr_draft: string;
  metrics: SessionMetrics | null;
}

// ── Database schema types ────────────────────────────────────────────────────

export interface DbColumn {
  name: string;
  data_type: string | null;
  primary_key: boolean;
  foreign_key: string | null;
  nullable: boolean;
  unique: boolean;
  default: string | null;
  source: string;
}

export interface DbTable {
  name: string;
  columns: DbColumn[];
  source: string;
  source_type: string;
  confidence: number;
}

export interface DbRelationship {
  from_table: string;
  from_column: string | null;
  to_table: string;
  to_column: string | null;
  relationship_type: string;
  source: string;
  inferred: boolean;
}

export interface DatabaseSchema {
  tables: DbTable[];
  relationships: DbRelationship[];
  detected: boolean;
}
