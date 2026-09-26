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
