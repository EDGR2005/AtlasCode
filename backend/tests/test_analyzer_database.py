"""Tests for the database schema analyzer using the sample-db-project fixture."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.analyzer.database import (
    detect_database_schema,
    _parse_sql,
    _parse_sqlalchemy,
    _parse_django,
    _parse_prisma,
)
from app.knowledge.models import FileEntry

FIXTURE = Path(__file__).parent.parent.parent / "examples/fixtures/sample-db-project"


# ---------------------------------------------------------------------------
# SQL parser
# ---------------------------------------------------------------------------

class TestSqlParser:
    def _sql(self) -> str:
        return (FIXTURE / "schema.sql").read_text()

    def test_detects_users_table(self):
        tables, _ = _parse_sql(self._sql(), "schema.sql")
        names = {t.name for t in tables}
        assert "users" in names

    def test_detects_posts_table(self):
        tables, _ = _parse_sql(self._sql(), "schema.sql")
        names = {t.name for t in tables}
        assert "posts" in names

    def test_users_primary_key(self):
        tables, _ = _parse_sql(self._sql(), "schema.sql")
        users = next(t for t in tables if t.name == "users")
        pk_cols = [c for c in users.columns if c.primary_key]
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "id"

    def test_users_unique_column(self):
        tables, _ = _parse_sql(self._sql(), "schema.sql")
        users = next(t for t in tables if t.name == "users")
        usernames = [c for c in users.columns if c.name == "username"]
        assert len(usernames) == 1
        assert usernames[0].unique is True

    def test_inline_fk_produces_relationship(self):
        tables, rels = _parse_sql(self._sql(), "schema.sql")
        # posts.author_id REFERENCES users(id)
        fk_rels = [r for r in rels if r.from_table == "posts" and r.to_table == "users"]
        assert len(fk_rels) >= 1

    def test_table_level_fk_produces_relationship(self):
        tables, rels = _parse_sql(self._sql(), "schema.sql")
        # comments has FOREIGN KEY (post_id) REFERENCES posts(id)
        fk_rels = [r for r in rels if r.from_table == "comments" and r.to_table == "posts"]
        assert len(fk_rels) >= 1

    def test_source_type_is_sql(self):
        tables, _ = _parse_sql(self._sql(), "schema.sql")
        for t in tables:
            assert t.source_type == "sql"

    def test_no_tables_invented(self):
        tables, _ = _parse_sql("SELECT 1;", "empty.sql")
        assert tables == []


# ---------------------------------------------------------------------------
# SQLAlchemy parser
# ---------------------------------------------------------------------------

class TestSqlAlchemyParser:
    def _sa(self) -> str:
        return (FIXTURE / "app/models_sa.py").read_text()

    def test_detects_user_model(self):
        tables, _ = _parse_sqlalchemy(self._sa(), "app/models_sa.py")
        names = {t.name for t in tables}
        assert "users" in names

    def test_detects_post_model(self):
        tables, _ = _parse_sqlalchemy(self._sa(), "app/models_sa.py")
        names = {t.name for t in tables}
        assert "posts" in names

    def test_user_pk_column(self):
        tables, _ = _parse_sqlalchemy(self._sa(), "app/models_sa.py")
        users = next(t for t in tables if t.name == "users")
        pk_cols = [c for c in users.columns if c.primary_key]
        assert len(pk_cols) >= 1

    def test_fk_column_produces_relationship(self):
        tables, rels = _parse_sqlalchemy(self._sa(), "app/models_sa.py")
        fk_rels = [r for r in rels if r.from_table == "posts" and r.to_table == "users"]
        assert len(fk_rels) >= 1

    def test_source_type_is_sqlalchemy(self):
        tables, _ = _parse_sqlalchemy(self._sa(), "app/models_sa.py")
        for t in tables:
            assert t.source_type == "sqlalchemy"

    def test_no_tables_invented_for_plain_python(self):
        tables, _ = _parse_sqlalchemy("def foo(): pass\n", "plain.py")
        assert tables == []


# ---------------------------------------------------------------------------
# Django parser
# ---------------------------------------------------------------------------

class TestDjangoParser:
    def _dj(self) -> str:
        return (FIXTURE / "app/models_django.py").read_text()

    def test_detects_category_model(self):
        tables, _ = _parse_django(self._dj(), "app/models_django.py")
        names = {t.name for t in tables}
        assert "categories" in names  # Meta.db_table = "categories"

    def test_detects_article_model(self):
        tables, _ = _parse_django(self._dj(), "app/models_django.py")
        names = {t.name for t in tables}
        assert "articles" in names

    def test_fk_produces_relationship(self):
        tables, rels = _parse_django(self._dj(), "app/models_django.py")
        fk_rels = [r for r in rels if r.from_table == "articles" and r.to_table == "category"]
        assert len(fk_rels) >= 1

    def test_source_type_is_django(self):
        tables, _ = _parse_django(self._dj(), "app/models_django.py")
        for t in tables:
            assert t.source_type == "django"

    def test_no_tables_invented_for_plain_python(self):
        tables, _ = _parse_django("x = 1\n", "plain.py")
        assert tables == []


# ---------------------------------------------------------------------------
# Prisma parser
# ---------------------------------------------------------------------------

class TestPrismaParser:
    def _pr(self) -> str:
        return (FIXTURE / "schema.prisma").read_text()

    def test_detects_product_model(self):
        tables, _ = _parse_prisma(self._pr(), "schema.prisma")
        names = {t.name for t in tables}
        assert "product" in names

    def test_detects_order_model(self):
        tables, _ = _parse_prisma(self._pr(), "schema.prisma")
        names = {t.name for t in tables}
        assert "order" in names

    def test_product_pk(self):
        tables, _ = _parse_prisma(self._pr(), "schema.prisma")
        product = next(t for t in tables if t.name == "product")
        pk_cols = [c for c in product.columns if c.primary_key]
        assert len(pk_cols) >= 1

    def test_relation_produces_db_relationship(self):
        tables, rels = _parse_prisma(self._pr(), "schema.prisma")
        # Product has @relation to Category via categoryId -> id
        prod_rels = [r for r in rels if r.from_table == "product"]
        assert len(prod_rels) >= 1

    def test_source_type_is_prisma(self):
        tables, _ = _parse_prisma(self._pr(), "schema.prisma")
        for t in tables:
            assert t.source_type == "prisma"

    def test_no_tables_invented_for_empty_prisma(self):
        tables, _ = _parse_prisma("generator client { provider = \"prisma-client-js\" }\n", "empty.prisma")
        assert tables == []


# ---------------------------------------------------------------------------
# detect_database_schema integration
# ---------------------------------------------------------------------------

class TestDetectDatabaseSchema:
    def test_detects_schema_in_fixture(self):
        entries = [
            FileEntry(path="schema.sql", size_bytes=100, extension=".sql", is_important=True),
            FileEntry(path="schema.prisma", size_bytes=100, extension=".prisma", is_important=True),
            FileEntry(path="app/models_sa.py", size_bytes=100, extension=".py", is_important=False),
            FileEntry(path="app/models_django.py", size_bytes=100, extension=".py", is_important=False),
        ]
        schema = detect_database_schema(FIXTURE, entries)
        assert schema.detected is True
        assert len(schema.tables) > 0

    def test_no_schema_for_empty_project(self, tmp_path):
        (tmp_path / "README.md").write_text("# hello")
        entries = [FileEntry(path="README.md", size_bytes=10, extension=".md", is_important=False)]
        schema = detect_database_schema(tmp_path, entries)
        assert schema.detected is False
        assert schema.tables == []
        assert schema.relationships == []

    def test_no_paths_escape_repo_root(self, tmp_path):
        """All detected source paths must be relative — no absolute paths."""
        (tmp_path / "schema.sql").write_text(
            "CREATE TABLE foo (id INTEGER NOT NULL PRIMARY KEY);"
        )
        entries = [FileEntry(path="schema.sql", size_bytes=50, extension=".sql", is_important=True)]
        schema = detect_database_schema(tmp_path, entries)
        for table in schema.tables:
            assert not table.source.startswith("/"), f"Absolute source path: {table.source!r}"

    def test_skips_git_directory(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "schema.sql").write_text(
            "CREATE TABLE secret (id INTEGER PRIMARY KEY);"
        )
        entries = [FileEntry(path=".git/schema.sql", size_bytes=50, extension=".sql", is_important=False)]
        schema = detect_database_schema(tmp_path, entries)
        assert schema.detected is False

    def test_deduplicates_tables(self, tmp_path):
        """Same table defined in both SQL and SQLAlchemy — only one entry kept."""
        sql = "CREATE TABLE users (id INTEGER NOT NULL PRIMARY KEY, name VARCHAR(64) NOT NULL);\n"
        (tmp_path / "schema.sql").write_text(sql)
        sa = (
            "from sqlalchemy.orm import declarative_base\n"
            "from sqlalchemy import Column, Integer, String\n"
            "Base = declarative_base()\n"
            "class User(Base):\n"
            "    __tablename__ = 'users'\n"
            "    id = Column(Integer, primary_key=True)\n"
            "    name = Column(String)\n"
        )
        (tmp_path / "models.py").write_text(sa)
        entries = [
            FileEntry(path="schema.sql", size_bytes=len(sql), extension=".sql", is_important=True),
            FileEntry(path="models.py", size_bytes=len(sa), extension=".py", is_important=False),
        ]
        schema = detect_database_schema(tmp_path, entries)
        user_tables = [t for t in schema.tables if t.name == "users"]
        assert len(user_tables) == 1  # deduplicated
