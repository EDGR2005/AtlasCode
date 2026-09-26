import { useState } from 'react';
import type { FileEntry } from '../types/knowledge';

interface Props {
  files: FileEntry[];
}

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: Map<string, TreeNode>;
  file?: FileEntry;
}

function buildTree(files: FileEntry[]): TreeNode {
  const root: TreeNode = { name: '', path: '', isDir: true, children: new Map() };
  for (const file of files) {
    const parts = file.path.replace(/^\//, '').split('/');
    let node = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const currentPath = parts.slice(0, i + 1).join('/');
      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part,
          path: currentPath,
          isDir: i < parts.length - 1,
          children: new Map(),
        });
      }
      node = node.children.get(part)!;
    }
    node.file = file;
    node.isDir = false;
  }
  return root;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function TreeNodeView({ node, depth }: { node: TreeNode; depth: number }) {
  const [open, setOpen] = useState(depth < 2);
  const indent = depth * 16;

  if (node.isDir) {
    const children = Array.from(node.children.values()).sort((a, b) => {
      // dirs first, then files
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    return (
      <div>
        <button
          className="tree-dir"
          style={{ paddingLeft: indent }}
          onClick={() => setOpen(o => !o)}
          type="button"
        >
          <span className="tree-toggle">{open ? '▾' : '▸'}</span>
          <span className="tree-dir-name">{node.name}</span>
        </button>
        {open && (
          <div>
            {children.map(child => (
              <TreeNodeView key={child.path} node={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }

  const file = node.file;
  return (
    <div className={`tree-file${file?.is_important ? ' tree-file--important' : ''}`} style={{ paddingLeft: indent }}>
      <span className="tree-file-name">
        {file?.is_important && <span className="tree-important-badge">★</span>}
        {node.name}
      </span>
      {file && (
        <span className="tree-file-size">{formatSize(file.size_bytes)}</span>
      )}
    </div>
  );
}

export default function RepositoryPanel({ files }: Props) {
  if (files.length === 0) {
    return <p className="empty-state">No files detected.</p>;
  }

  const root = buildTree(files);
  const topLevel = Array.from(root.children.values()).sort((a, b) => {
    if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="repo-panel">
      {topLevel.map(node => (
        <TreeNodeView key={node.path} node={node} depth={0} />
      ))}
    </div>
  );
}
