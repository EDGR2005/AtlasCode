import type { Dependency } from '../types/knowledge';

interface Props {
  dependencies: Dependency[];
}

export default function DependenciesPanel({ dependencies }: Props) {
  if (dependencies.length === 0) {
    return <p className="empty-state">No dependencies detected.</p>;
  }

  // Group by ecosystem
  const groups = new Map<string, Dependency[]>();
  for (const dep of dependencies) {
    const list = groups.get(dep.ecosystem) ?? [];
    list.push(dep);
    groups.set(dep.ecosystem, list);
  }

  return (
    <div className="deps-panel">
      {Array.from(groups.entries()).map(([ecosystem, deps]) => (
        <section key={ecosystem} className="deps-group">
          <h3 className="deps-group-title">{ecosystem}</h3>
          <ul className="deps-list">
            {deps.map((dep, i) => (
              <li key={`${dep.name}-${i}`} className="deps-item">
                <span className="deps-name">{dep.name}</span>
                {dep.version && (
                  <span className="deps-version">@{dep.version}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
