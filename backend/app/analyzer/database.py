"""
Database schema analyzer.

Detects table/model definitions from:
  - Raw SQL files (.sql)
  - SQLAlchemy (Python)
  - Django ORM (Python models.py)
  - Prisma schema files (schema.prisma)
  - Common migration files (Alembic, Django migrations)

All detected facts include a source file path and confidence score.
No information is invented — only what can be parsed from the files.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from app.knowledge.models import (
    ColumnInfo,
    DatabaseSchema,
    DbRelationship,
    FileEntry,
    TableSchema,
)


def _balanced_parens(text: str, start: int) -> int:
    """
    Given text[start] == '(', return the index of the matching ')'.
    Returns -1 if not found.
    """
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv",
    "dist", "build", "__pycache__", ".tox",
}


def _is_skipped(path_str: str) -> bool:
    parts = path_str.replace("\\", "/").split("/")
    return any(part in _SKIP_DIRS for part in parts)


def _read(repo_path: Path, rel_path: str) -> str | None:
    try:
        return (repo_path / rel_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _normalise_type(raw: str) -> str:
    """Upper-case and strip length/precision to get a canonical SQL type."""
    return re.split(r"[(\s]", raw.strip().upper())[0]


# ---------------------------------------------------------------------------
# SQL file parser  (.sql)
# ---------------------------------------------------------------------------

# Matches: CREATE TABLE [IF NOT EXISTS] `name` ( ... );
_SQL_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(\w+)[`\"]?\s*\(",
    re.IGNORECASE,
)

# Column-level PRIMARY KEY inline definition
_SQL_INLINE_PK = re.compile(r"\bPRIMARY\s+KEY\b", re.IGNORECASE)

# REFERENCES table(column) — FK inline
_SQL_REFERENCES = re.compile(
    r"REFERENCES\s+[`\"]?(\w+)[`\"]?\s*\(\s*[`\"]?(\w+)[`\"]?\s*\)",
    re.IGNORECASE,
)

# NOT NULL
_SQL_NOT_NULL = re.compile(r"\bNOT\s+NULL\b", re.IGNORECASE)

# UNIQUE
_SQL_UNIQUE = re.compile(r"\bUNIQUE\b", re.IGNORECASE)

# DEFAULT value
_SQL_DEFAULT = re.compile(r"\bDEFAULT\s+(\S+)", re.IGNORECASE)

# Table-level FOREIGN KEY constraint
_SQL_TABLE_FK = re.compile(
    r"FOREIGN\s+KEY\s*\(\s*[`\"]?(\w+)[`\"]?\s*\)\s+REFERENCES\s+[`\"]?(\w+)[`\"]?\s*\(\s*[`\"]?(\w+)[`\"]?\s*\)",
    re.IGNORECASE,
)


def _parse_sql_column_line(line: str, source: str) -> ColumnInfo | None:
    """
    Parse a single column definition line inside CREATE TABLE.
    Returns None for constraint lines (PRIMARY KEY, FOREIGN KEY, INDEX, KEY, UNIQUE KEY, CHECK).
    """
    stripped = line.strip().rstrip(",")
    if not stripped:
        return None
    upper = stripped.upper()
    # Skip table-level constraint lines
    if re.match(
        r"(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE\s+KEY|INDEX|KEY\s+|CHECK\s*\(|CONSTRAINT\s+)",
        upper,
    ):
        return None

    # Column name + type: `name` TYPE [modifiers...]
    m = re.match(r"[`\"]?(\w+)[`\"]?\s+(\w+)", stripped)
    if not m:
        return None

    col_name = m.group(1)
    col_type = _normalise_type(m.group(2))

    # Skip SQL keywords that look like column names (e.g. "UNIQUE", "INDEX")
    if col_name.upper() in (
        "PRIMARY", "FOREIGN", "UNIQUE", "INDEX", "KEY", "CONSTRAINT", "CHECK",
    ):
        return None

    pk = bool(_SQL_INLINE_PK.search(stripped))
    nullable = not bool(_SQL_NOT_NULL.search(stripped)) and not pk
    unique = bool(_SQL_UNIQUE.search(stripped))
    default_m = _SQL_DEFAULT.search(stripped)
    default = default_m.group(1) if default_m else None

    fk: str | None = None
    ref_m = _SQL_REFERENCES.search(stripped)
    if ref_m:
        fk = f"{ref_m.group(1)}.{ref_m.group(2)}"

    return ColumnInfo(
        name=col_name,
        data_type=col_type,
        primary_key=pk,
        foreign_key=fk,
        nullable=nullable,
        unique=unique,
        default=default,
        source=source,
    )


def _parse_sql(content: str, source: str) -> tuple[list[TableSchema], list[DbRelationship]]:
    """Parse raw SQL content for CREATE TABLE statements."""
    tables: list[TableSchema] = []
    rels: list[DbRelationship] = []

    # Find each CREATE TABLE block
    for match in _SQL_CREATE_TABLE.finditer(content):
        table_name = match.group(1)
        start = match.end()
        # Find the matching closing paren — track depth
        depth = 1
        pos = start
        while pos < len(content) and depth > 0:
            if content[pos] == "(":
                depth += 1
            elif content[pos] == ")":
                depth -= 1
            pos += 1
        body = content[start : pos - 1]

        columns: list[ColumnInfo] = []
        # Parse table-level FK constraints first to collect relationships
        for fk_m in _SQL_TABLE_FK.finditer(body):
            col_name = fk_m.group(1)
            ref_table = fk_m.group(2)
            ref_col = fk_m.group(3)
            rels.append(
                DbRelationship(
                    from_table=table_name,
                    from_column=col_name,
                    to_table=ref_table,
                    to_column=ref_col,
                    relationship_type="one_to_many",
                    source=source,
                    inferred=False,
                )
            )

        for raw_line in body.split("\n"):
            col = _parse_sql_column_line(raw_line, source)
            if col:
                # Promote inline FK to relationship
                if col.foreign_key:
                    parts = col.foreign_key.split(".")
                    ref_table = parts[0]
                    ref_col = parts[1] if len(parts) > 1 else None
                    rels.append(
                        DbRelationship(
                            from_table=table_name,
                            from_column=col.name,
                            to_table=ref_table,
                            to_column=ref_col,
                            relationship_type="one_to_many",
                            source=source,
                            inferred=False,
                        )
                    )
                columns.append(col)

        if table_name and (columns or body.strip()):
            tables.append(
                TableSchema(
                    name=table_name,
                    columns=columns,
                    source=source,
                    source_type="sql",
                    confidence=1.0,
                )
            )
    return tables, rels


# ---------------------------------------------------------------------------
# SQLAlchemy parser (Python)
# ---------------------------------------------------------------------------

# class Foo(Base): or class Foo(db.Model):
_SA_MODEL_CLASS = re.compile(
    r"^class\s+(\w+)\s*\(.*(?:Base|db\.Model|DeclarativeBase|Model).*\)\s*:",
    re.MULTILINE,
)

# __tablename__ = "foo"
_SA_TABLENAME = re.compile(r"""__tablename__\s*=\s*['"](\w+)['"]""")

# Matches start of Column/mapped_column assignment — args extracted with balanced-paren helper
_SA_COLUMN_START = re.compile(
    r"""(\w+)\s*(?::\s*Mapped\[.*?\])?\s*=\s*(?:mapped_column|Column)\s*\(""",
    re.DOTALL,
)

_SA_FK = re.compile(r"""ForeignKey\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_SA_RELATIONSHIP = re.compile(
    r"""(\w+)\s*=\s*relationship\s*\(\s*['"](\w+)['"]""",
)


def _sa_column_info(field_name: str, args_str: str, source: str) -> ColumnInfo:
    """Parse Column()/mapped_column() argument string into ColumnInfo."""
    # First positional arg is often the type
    first_arg_m = re.match(r"\s*(\w+)", args_str)
    col_type = _normalise_type(first_arg_m.group(1)) if first_arg_m else None

    pk = bool(re.search(r"primary_key\s*=\s*True", args_str))
    nullable_m = re.search(r"nullable\s*=\s*(True|False)", args_str)
    if nullable_m:
        nullable = nullable_m.group(1) == "True"
    else:
        nullable = not pk

    unique = bool(re.search(r"unique\s*=\s*True", args_str))
    default_m = re.search(r"default\s*=\s*(\S+?)(?:[,)])", args_str)
    default = default_m.group(1) if default_m else None

    fk: str | None = None
    fk_m = _SA_FK.search(args_str)
    if fk_m:
        fk = fk_m.group(1)  # e.g. "users.id"

    return ColumnInfo(
        name=field_name,
        data_type=col_type,
        primary_key=pk,
        foreign_key=fk,
        nullable=nullable,
        unique=unique,
        default=default,
        source=source,
    )


def _parse_sqlalchemy(content: str, source: str) -> tuple[list[TableSchema], list[DbRelationship]]:
    tables: list[TableSchema] = []
    rels: list[DbRelationship] = []

    for cls_m in _SA_MODEL_CLASS.finditer(content):
        class_name = cls_m.group(1)
        class_start = cls_m.end()
        # Collect the class body until next non-indented line
        class_body_lines: list[str] = []
        for line in content[class_start:].split("\n"):
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            class_body_lines.append(line)
        class_body = "\n".join(class_body_lines)

        # Table name
        tn_m = _SA_TABLENAME.search(class_body)
        table_name = tn_m.group(1) if tn_m else class_name.lower()

        columns: list[ColumnInfo] = []
        for col_m in _SA_COLUMN_START.finditer(class_body):
            field_name = col_m.group(1)
            # col_m.end()-1 is the position of the '(' — find balanced close
            open_pos = col_m.end() - 1
            close_pos = _balanced_parens(class_body, open_pos)
            if close_pos == -1:
                continue
            args_str = class_body[open_pos + 1 : close_pos]
            if field_name.startswith("_"):
                continue
            col = _sa_column_info(field_name, args_str, source)
            if col.foreign_key:
                parts = col.foreign_key.split(".")
                rels.append(
                    DbRelationship(
                        from_table=table_name,
                        from_column=field_name,
                        to_table=parts[0],
                        to_column=parts[1] if len(parts) > 1 else None,
                        relationship_type="one_to_many",
                        source=source,
                        inferred=False,
                    )
                )
            columns.append(col)

        # relationship() declarations
        for rel_m in _SA_RELATIONSHIP.finditer(class_body):
            rels.append(
                DbRelationship(
                    from_table=table_name,
                    from_column=rel_m.group(1),
                    to_table=rel_m.group(2).lower(),
                    relationship_type="unknown",
                    source=source,
                    inferred=True,
                )
            )

        if columns:
            tables.append(
                TableSchema(
                    name=table_name,
                    columns=columns,
                    source=source,
                    source_type="sqlalchemy",
                    confidence=0.9,
                )
            )
    return tables, rels


# ---------------------------------------------------------------------------
# Django ORM parser (Python models.py)
# ---------------------------------------------------------------------------

_DJ_MODEL_CLASS = re.compile(
    r"^class\s+(\w+)\s*\(\s*(?:models\.Model|Model)\s*\)\s*:",
    re.MULTILINE,
)

# field = models.CharField(...) / models.ForeignKey(OtherModel, ...) etc.
_DJ_FIELD = re.compile(
    r"""(\w+)\s*=\s*models\.(\w+)\s*\(([^)]*)\)"""
)

_DJ_VERBOSE_NAME = re.compile(r"""verbose_name\s*=\s*['"]([^'"]+)['"]""")

_DJ_FIELD_TYPE_MAP = {
    "AutoField": "INTEGER",
    "BigAutoField": "BIGINT",
    "IntegerField": "INTEGER",
    "BigIntegerField": "BIGINT",
    "SmallIntegerField": "SMALLINT",
    "FloatField": "FLOAT",
    "DecimalField": "DECIMAL",
    "CharField": "VARCHAR",
    "TextField": "TEXT",
    "BooleanField": "BOOLEAN",
    "DateField": "DATE",
    "DateTimeField": "DATETIME",
    "TimeField": "TIME",
    "UUIDField": "UUID",
    "EmailField": "VARCHAR",
    "URLField": "VARCHAR",
    "SlugField": "VARCHAR",
    "JSONField": "JSON",
    "BinaryField": "BLOB",
    "ForeignKey": "INTEGER",
    "OneToOneField": "INTEGER",
    "ManyToManyField": None,  # junction table, not a direct column
}

_DJ_CARDINALITY_MAP = {
    "ForeignKey": "one_to_many",
    "OneToOneField": "one_to_one",
    "ManyToManyField": "many_to_many",
}


def _parse_django(content: str, source: str) -> tuple[list[TableSchema], list[DbRelationship]]:
    tables: list[TableSchema] = []
    rels: list[DbRelationship] = []

    for cls_m in _DJ_MODEL_CLASS.finditer(content):
        class_name = cls_m.group(1)
        class_start = cls_m.end()
        class_body_lines: list[str] = []
        for line in content[class_start:].split("\n"):
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            class_body_lines.append(line)
        class_body = "\n".join(class_body_lines)

        # Django table name default: app_modelname — we can't know the app,
        # so use class_name.lower() as the table name.
        table_name = class_name.lower()
        # Check for Meta.db_table
        meta_m = re.search(r"db_table\s*=\s*['\"](\w+)['\"]", class_body)
        if meta_m:
            table_name = meta_m.group(1)

        columns: list[ColumnInfo] = []
        for field_m in _DJ_FIELD.finditer(class_body):
            field_name = field_m.group(1)
            field_type_name = field_m.group(2)
            field_args = field_m.group(3)

            if field_name in ("Meta", "objects") or field_name.startswith("_"):
                continue

            sql_type = _DJ_FIELD_TYPE_MAP.get(field_type_name)
            if sql_type is None and field_type_name not in _DJ_CARDINALITY_MAP:
                # Unknown field type — include with no type info
                sql_type = field_type_name.upper()

            nullable = bool(re.search(r"null\s*=\s*True", field_args))
            unique = bool(re.search(r"unique\s*=\s*True", field_args))
            pk = field_type_name in ("AutoField", "BigAutoField")
            blank = bool(re.search(r"blank\s*=\s*True", field_args))
            _ = blank  # recorded but not stored on ColumnInfo for now

            fk: str | None = None
            rel_type = _DJ_CARDINALITY_MAP.get(field_type_name)
            if rel_type:
                # First positional arg is the related model
                first_arg_m = re.match(r"\s*['\"]?(\w+)['\"]?", field_args)
                if first_arg_m:
                    related_model = first_arg_m.group(1)
                    if related_model not in ("self", "'self'"):
                        rels.append(
                            DbRelationship(
                                from_table=table_name,
                                from_column=field_name,
                                to_table=related_model.lower(),
                                relationship_type=rel_type,
                                source=source,
                                inferred=False,
                            )
                        )
                        fk = related_model.lower()
                if rel_type == "many_to_many":
                    continue  # no column added for M2M

            if sql_type is not None:
                columns.append(
                    ColumnInfo(
                        name=field_name,
                        data_type=sql_type,
                        primary_key=pk,
                        foreign_key=fk,
                        nullable=nullable,
                        unique=unique,
                        source=source,
                    )
                )

        if columns:
            tables.append(
                TableSchema(
                    name=table_name,
                    columns=columns,
                    source=source,
                    source_type="django",
                    confidence=0.9,
                )
            )
    return tables, rels


# ---------------------------------------------------------------------------
# Prisma schema parser (schema.prisma)
# ---------------------------------------------------------------------------

_PRISMA_MODEL = re.compile(r"^model\s+(\w+)\s*\{", re.MULTILINE)
_PRISMA_FIELD = re.compile(
    r"""^[^\S\n]+(\w+)[^\S\n]+(\w+)(\??)[^\S\n]*(.*)$""", re.MULTILINE
)
_PRISMA_RELATION = re.compile(
    r"""@relation\s*\(.*?references:\s*\[(\w+)\].*?\)""",
    re.DOTALL,
)
_PRISMA_RELATION_FIELDS = re.compile(
    r"""@relation\s*\(.*?fields:\s*\[(\w+)\].*?references:\s*\[(\w+)\].*?name:.*?['"](\w*)['"]""",
    re.DOTALL,
)

_PRISMA_TYPE_MAP = {
    "String": "VARCHAR",
    "Int": "INTEGER",
    "BigInt": "BIGINT",
    "Float": "FLOAT",
    "Decimal": "DECIMAL",
    "Boolean": "BOOLEAN",
    "DateTime": "DATETIME",
    "Json": "JSON",
    "Bytes": "BLOB",
}


def _parse_prisma(content: str, source: str) -> tuple[list[TableSchema], list[DbRelationship]]:
    tables: list[TableSchema] = []
    rels: list[DbRelationship] = []

    # Find each model block
    for model_m in _PRISMA_MODEL.finditer(content):
        model_name = model_m.group(1)
        block_start = model_m.end()
        # Find closing brace, tracking depth
        depth = 1
        pos = block_start
        while pos < len(content) and depth > 0:
            if content[pos] == "{":
                depth += 1
            elif content[pos] == "}":
                depth -= 1
            pos += 1
        block = content[block_start : pos - 1]

        columns: list[ColumnInfo] = []
        for field_m in _PRISMA_FIELD.finditer(block):
            field_name = field_m.group(1)
            field_type = field_m.group(2)
            optional = field_m.group(3) == "?"
            modifiers = field_m.group(4)

            # Skip relation fields (they reference other models by name)
            if field_type[0].isupper() and field_type not in _PRISMA_TYPE_MAP:
                # This is a relation field — record relationship
                if "@relation" in modifiers:
                    fields_m = re.search(
                        r"fields:\s*\[(\w+)\].*?references:\s*\[(\w+)\]",
                        modifiers, re.DOTALL,
                    )
                    if fields_m:
                        rels.append(
                            DbRelationship(
                                from_table=model_name.lower(),
                                from_column=fields_m.group(1),
                                to_table=field_type.lower(),
                                to_column=fields_m.group(2),
                                relationship_type="one_to_many",
                                source=source,
                                inferred=False,
                            )
                        )
                continue

            sql_type = _PRISMA_TYPE_MAP.get(field_type, field_type.upper())
            pk = "@id" in modifiers
            unique = "@unique" in modifiers
            default_m = re.search(r"@default\(([^)]+)\)", modifiers)
            default = default_m.group(1) if default_m else None

            columns.append(
                ColumnInfo(
                    name=field_name,
                    data_type=sql_type,
                    primary_key=pk,
                    nullable=optional,
                    unique=unique,
                    default=default,
                    source=source,
                )
            )

        if columns:
            tables.append(
                TableSchema(
                    name=model_name.lower(),
                    columns=columns,
                    source=source,
                    source_type="prisma",
                    confidence=1.0,
                )
            )
    return tables, rels


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def detect_database_schema(
    repo_path: Path, file_entries: list[FileEntry]
) -> DatabaseSchema:
    """
    Run all database schema parsers over the repository.
    Returns a DatabaseSchema with detected=False when no schema evidence found.
    Never invents tables or relationships.
    """
    repo_path = repo_path.resolve()
    all_tables: list[TableSchema] = []
    all_rels: list[DbRelationship] = []

    # Deduplicate table names: keep highest-confidence entry
    seen_tables: dict[str, TableSchema] = {}

    def _add_tables(tables: list[TableSchema], new_rels: list[DbRelationship]) -> None:
        for t in tables:
            existing = seen_tables.get(t.name)
            if existing is None or t.confidence > existing.confidence:
                seen_tables[t.name] = t
        all_rels.extend(new_rels)

    for entry in file_entries:
        if _is_skipped(entry.path):
            continue

        path_lower = entry.path.replace("\\", "/").lower()
        content = _read(repo_path, entry.path)
        if content is None:
            continue

        # SQL files
        if entry.extension in (".sql",):
            t, r = _parse_sql(content, entry.path)
            _add_tables(t, r)
            continue

        # Prisma schema
        if path_lower.endswith("schema.prisma"):
            t, r = _parse_prisma(content, entry.path)
            _add_tables(t, r)
            continue

        # Python files — check for SQLAlchemy or Django ORM
        if entry.extension == ".py":
            # SQLAlchemy: any file that imports Base/DeclarativeBase/mapped_column
            if re.search(
                r"(?:from\s+sqlalchemy|import\s+sqlalchemy|declarative_base|DeclarativeBase|mapped_column)",
                content,
            ):
                t, r = _parse_sqlalchemy(content, entry.path)
                _add_tables(t, r)

            # Django: files that import django.db.models
            if re.search(r"from\s+django\.db\s+import\s+models", content):
                t, r = _parse_django(content, entry.path)
                _add_tables(t, r)

    all_tables = list(seen_tables.values())

    # Deduplicate relationships
    seen_rel_keys: set[tuple] = set()
    unique_rels: list[DbRelationship] = []
    for r in all_rels:
        key = (r.from_table, r.from_column, r.to_table, r.to_column)
        if key not in seen_rel_keys:
            seen_rel_keys.add(key)
            unique_rels.append(r)

    detected = len(all_tables) > 0
    return DatabaseSchema(
        tables=all_tables,
        relationships=unique_rels,
        detected=detected,
    )
