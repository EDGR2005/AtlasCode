interface Props {
  diff: string;
}

export default function DiffViewer({ diff }: Props) {
  if (!diff) {
    return (
      <div className="diff-empty">
        <p>No changes detected in the working tree.</p>
      </div>
    );
  }

  const lines = diff.split('\n');

  return (
    <div className="diff-viewer">
      <div className="diff-stat">
        {lines.filter(l => l.startsWith('diff --git')).length} file(s) changed
      </div>
      <pre className="diff-pre">
        {lines.map((line, i) => {
          let cls = 'diff-line';
          if (line.startsWith('+') && !line.startsWith('+++')) cls += ' diff-line--add';
          else if (line.startsWith('-') && !line.startsWith('---')) cls += ' diff-line--del';
          else if (line.startsWith('@@')) cls += ' diff-line--hunk';
          else if (line.startsWith('diff ') || line.startsWith('index ') || line.startsWith('---') || line.startsWith('+++')) cls += ' diff-line--meta';
          return (
            <span key={i} className={cls}>{line}{'\n'}</span>
          );
        })}
      </pre>
    </div>
  );
}
