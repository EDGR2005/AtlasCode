from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.knowledge.models import ProjectKnowledge, RepositoryInfo
from app.knowledge.storage import ProjectStorage
from app.analyzer import repository, files, technologies, dependencies, relationships, database


def run_pipeline(
    project_id: str, repo_url: str, storage: ProjectStorage
) -> ProjectKnowledge:
    """
    Full analysis pipeline:
    1. Update status to "analyzing"
    2. Clone/update repository
    3. Scan files
    4. Detect technologies
    5. Extract dependencies
    6. Detect relationships
    7. Build and save ProjectKnowledge
    8. Update status to "ready"
    Returns the completed ProjectKnowledge.
    On any exception: update status to "error", re-raise.
    """
    metadata = storage.get_project(project_id)
    if metadata is None:
        raise ValueError(f"Project {project_id!r} not found")

    try:
        # Step 1: mark as analyzing
        metadata.status = "analyzing"
        storage.update_project(metadata)

        # Step 2: clone repository
        clone_path = storage.get_clone_path(project_id)
        commit_sha = repository.clone_repository(repo_url, clone_path)

        # Step 3: scan files
        file_entries = files.scan_files(clone_path)

        # Step 4: detect technologies
        techs = technologies.detect_technologies(clone_path, file_entries)

        # Step 5: extract dependencies
        deps = dependencies.extract_dependencies(clone_path, file_entries)

        # Step 6: detect relationships
        rels = relationships.detect_relationships(clone_path, file_entries)

        # Step 7: detect database schema
        db_schema = database.detect_database_schema(clone_path, file_entries)

        # Step 8: build and save knowledge
        repo_info = RepositoryInfo(
            url=repo_url,
            commit_sha=commit_sha,
            clone_path=str(clone_path),
        )
        knowledge = ProjectKnowledge(
            metadata=metadata,
            repository=repo_info,
            technologies=techs,
            dependencies=deps,
            files=file_entries,
            relationships=rels,
            database=db_schema,
        )
        storage.save_knowledge(project_id, knowledge)

        # Step 9: mark as ready
        metadata.status = "ready"
        storage.update_project(metadata)

    except Exception as e:
        metadata.status = "error"
        metadata.error_message = str(e)
        storage.update_project(metadata)
        raise

    return knowledge
