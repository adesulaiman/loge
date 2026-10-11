"""Shared path filters for indexing a git repository tip (GitHub, GitLab)."""

from __future__ import annotations

import os

# Prose docs plus common source / config text. Binary and build output stay out
# via PATH_DENYLIST and MAX_FILE_SIZE_BYTES.
INDEXABLE_FILE_EXTENSIONS = {
    ".md",
    ".mdx",
    ".markdown",
    ".rst",
    ".txt",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".php",
    ".sh",
    ".bash",
    ".sql",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".html",
    ".css",
    ".vue",
    ".c",
    ".h",
    ".cpp",
    ".cs",
    ".swift",
}

INDEXABLE_FILENAMES = {
    "readme",
    "license",
    "licence",
    "changelog",
    "contributing",
    "authors",
    "notice",
    "copying",
    "install",
    "maintainers",
    "codeowners",
    "security",
    "support",
}

PATH_DENYLIST = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "__pycache__",
}

MAX_FILE_SIZE_BYTES = 1_000_000

BRANCH_MODE_SINGLE = "single"
BRANCH_MODE_ALL = "all"


def is_indexable_path(path: str, size: int | None) -> bool:
    """Whether a path at a branch tip should be indexed as text knowledge."""
    if size is not None and size > MAX_FILE_SIZE_BYTES:
        return False

    segments = set(path.split("/"))
    if segments & PATH_DENYLIST:
        return False

    basename = path.rsplit("/", 1)[-1]
    _, extension = os.path.splitext(basename)
    if extension.lower() in INDEXABLE_FILE_EXTENSIONS:
        return True

    if not extension and basename.lower() in INDEXABLE_FILENAMES:
        return True

    return False
