import itertools
from collections import deque
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from typing import Any, TypeVar

import gitlab
import pytz
from gitlab.v4.objects import Project

from onyx.configs.app_configs import INDEX_BATCH_SIZE
from onyx.configs.constants import DocumentSource
from onyx.connectors.cross_connector_utils.git_indexable_files import (
    BRANCH_MODE_ALL,
    BRANCH_MODE_SINGLE,
    is_indexable_path,
)
from onyx.connectors.cross_connector_utils.miscellaneous_utils import time_str_to_utc
from onyx.connectors.interfaces import (
    GenerateDocumentsOutput,
    LoadConnector,
    PollConnector,
    SecondsSinceUnixEpoch,
)
from onyx.connectors.models import (
    BasicExpertInfo,
    ConnectorMissingCredentialError,
    Document,
    HierarchyNode,
    TextSection,
)
from onyx.utils.datetime import datetime_to_utc
from onyx.utils.logger import setup_logger

T = TypeVar("T")


logger = setup_logger()


def _batch_gitlab_objects(git_objs: Iterable[T], batch_size: int) -> Iterator[list[T]]:
    it = iter(git_objs)
    while True:
        batch = list(itertools.islice(it, batch_size))
        if not batch:
            break
        yield batch


def get_author(author: Any) -> BasicExpertInfo:
    # GitLab masks the `name` field as "****" for blocked users and as an
    # anti-scraping measure on free-tier public projects. Fall back to
    # `username` so we surface a usable identifier instead.
    name = author.get("name")
    if not name or name == "****":
        name = author.get("username")
    return BasicExpertInfo(
        display_name=name,
    )


def _gitlab_datetime_to_utc(value: Any) -> datetime | None:
    """Normalize a GitLab timestamp to tz-aware UTC.

    python-gitlab exposes REST attributes as raw JSON, so these arrive as
    ISO-8601 strings; handle datetime values defensively too. Uses the shared
    parser rather than a fixed format so whole-second timestamps (no fractional
    part) don't raise.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return datetime_to_utc(value)
    return time_str_to_utc(value)


def _convert_merge_request_to_document(mr: Any) -> Document:
    doc = Document(
        id=mr.web_url,
        sections=[TextSection(link=mr.web_url, text=mr.description or "")],
        source=DocumentSource.GITLAB,
        semantic_identifier=mr.title,
        doc_updated_at=_gitlab_datetime_to_utc(mr.updated_at),
        # NOTE: doc_created_at population not yet verified against live data
        doc_created_at=_gitlab_datetime_to_utc(mr.created_at),
        primary_owners=[get_author(mr.author)],
        metadata={"state": mr.state, "type": "MergeRequest"},
    )
    return doc


def _convert_issue_to_document(issue: Any) -> Document:
    doc = Document(
        id=issue.web_url,
        sections=[TextSection(link=issue.web_url, text=issue.description or "")],
        source=DocumentSource.GITLAB,
        semantic_identifier=issue.title,
        doc_updated_at=_gitlab_datetime_to_utc(issue.updated_at),
        # NOTE: doc_created_at population not yet verified against live data
        doc_created_at=_gitlab_datetime_to_utc(issue.created_at),
        primary_owners=[get_author(issue.author)],
        metadata={"state": issue.state, "type": issue.type or "Issue"},
    )
    return doc


def _convert_code_to_document(
    project: Project,
    file: Any,
    url: str,
    project_name: str,
    project_owner: str,
    branch: str,
) -> Document | None:
    """Build a Document from one blob at a branch tip. Skips non-text files."""
    size = file.get("size")
    path = file["path"]
    if not is_indexable_path(path, size if isinstance(size, int) else None):
        return None

    file_content_obj = project.files.get(file_path=path, ref=branch)
    try:
        file_content = file_content_obj.decode().decode("utf-8")
    except UnicodeDecodeError:
        file_content = file_content_obj.decode().decode("latin-1")

    file_url = f"{url}/{project_owner}/{project_name}/-/blob/{branch}/{path}"

    return Document(
        # Id includes the branch so the same path on two tips is two documents.
        id=file_url,
        sections=[TextSection(link=file_url, text=file_content)],
        source=DocumentSource.GITLAB,
        semantic_identifier=path,
        doc_updated_at=datetime.now().replace(tzinfo=timezone.utc),
        primary_owners=[],
        metadata={
            "type": "CodeFile",
            "object_type": "File",
            "path": path,
            "branch": branch,
        },
    )


class GitlabConnector(LoadConnector, PollConnector):
    def __init__(
        self,
        project_owner: str,
        project_name: str,
        batch_size: int = INDEX_BATCH_SIZE,
        state_filter: str = "all",
        include_mrs: bool = False,
        include_issues: bool = False,
        include_code_files: bool = True,
        branch_mode: str = BRANCH_MODE_SINGLE,
        branch: str | None = None,
    ) -> None:
        self.project_owner = project_owner
        self.project_name = project_name
        self.batch_size = batch_size
        self.state_filter = state_filter
        self.include_mrs = include_mrs
        self.include_issues = include_issues
        self.include_code_files = include_code_files
        mode = (branch_mode or BRANCH_MODE_SINGLE).strip().lower()
        self.branch_mode = (
            BRANCH_MODE_ALL if mode == BRANCH_MODE_ALL else BRANCH_MODE_SINGLE
        )
        self.branch = (branch or "").strip() or None
        self.gitlab_client: gitlab.Gitlab | None = None

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        self.gitlab_client = gitlab.Gitlab(
            credentials["gitlab_url"], private_token=credentials["gitlab_access_token"]
        )
        return None

    def _resolve_branches(self, project: Project) -> list[str]:
        if self.branch_mode == BRANCH_MODE_ALL:
            names = sorted(
                {branch.name for branch in project.branches.list(iterator=True)}
            )
            if names:
                return names
            return [project.default_branch] if project.default_branch else []
        return [self.branch or project.default_branch]

    def _fetch_code_files_for_branch(
        self, project: Project, branch: str
    ) -> GenerateDocumentsOutput:
        assert self.gitlab_client is not None
        # BFS: recursive repository_tree is slow on large projects.
        queue: deque[str] = deque([""])
        while queue:
            current_path = queue.popleft()
            files = project.repository_tree(
                path=current_path, ref=branch, all=True
            )
            for file_batch in _batch_gitlab_objects(files, self.batch_size):
                code_doc_batch: list[Document | HierarchyNode] = []
                for file in file_batch:
                    if file["type"] == "tree":
                        queue.append(file["path"])
                        continue
                    if file["type"] != "blob":
                        continue
                    doc = _convert_code_to_document(
                        project,
                        file,
                        self.gitlab_client.url,
                        self.project_name,
                        self.project_owner,
                        branch,
                    )
                    if doc is not None:
                        code_doc_batch.append(doc)
                if code_doc_batch:
                    yield code_doc_batch

    def _fetch_from_gitlab(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> GenerateDocumentsOutput:
        if self.gitlab_client is None:
            raise ConnectorMissingCredentialError("Gitlab")
        project: Project = self.gitlab_client.projects.get(
            f"{self.project_owner}/{self.project_name}"
        )

        if self.include_code_files:
            for branch in self._resolve_branches(project):
                logger.info(
                    "Indexing GitLab tip for %s/%s branch %s",
                    self.project_owner,
                    self.project_name,
                    branch,
                )
                yield from self._fetch_code_files_for_branch(project, branch)

        if self.include_mrs:
            merge_requests = project.mergerequests.list(
                state=self.state_filter,
                order_by="updated_at",
                sort="desc",
                iterator=True,
            )

            for mr_batch in _batch_gitlab_objects(merge_requests, self.batch_size):
                mr_doc_batch: list[Document | HierarchyNode] = []
                for mr in mr_batch:
                    mr.updated_at = datetime.strptime(
                        mr.updated_at, "%Y-%m-%dT%H:%M:%S.%f%z"
                    )
                    if start is not None and mr.updated_at < start.replace(
                        tzinfo=pytz.UTC
                    ):
                        yield mr_doc_batch
                        return
                    if end is not None and mr.updated_at > end.replace(tzinfo=pytz.UTC):
                        continue
                    mr_doc_batch.append(_convert_merge_request_to_document(mr))
                yield mr_doc_batch

        if self.include_issues:
            issues = project.issues.list(state=self.state_filter, iterator=True)

            for issue_batch in _batch_gitlab_objects(issues, self.batch_size):
                issue_doc_batch: list[Document | HierarchyNode] = []
                for issue in issue_batch:
                    issue.updated_at = datetime.strptime(
                        issue.updated_at, "%Y-%m-%dT%H:%M:%S.%f%z"
                    )
                    if start is not None:
                        start = start.replace(tzinfo=pytz.UTC)
                        if issue.updated_at < start:
                            yield issue_doc_batch
                            return
                    if end is not None:
                        end = end.replace(tzinfo=pytz.UTC)
                        if issue.updated_at > end:
                            continue
                    issue_doc_batch.append(_convert_issue_to_document(issue))
                yield issue_doc_batch

    def load_from_state(self) -> GenerateDocumentsOutput:
        return self._fetch_from_gitlab()

    def poll_source(
        self, start: SecondsSinceUnixEpoch, end: SecondsSinceUnixEpoch
    ) -> GenerateDocumentsOutput:
        start_datetime = datetime.fromtimestamp(start, tz=timezone.utc)
        end_datetime = datetime.fromtimestamp(end, tz=timezone.utc)
        return self._fetch_from_gitlab(start_datetime, end_datetime)


if __name__ == "__main__":
    import os

    connector = GitlabConnector(
        project_owner=os.environ["PROJECT_OWNER"],
        project_name=os.environ["PROJECT_NAME"],
        batch_size=10,
        state_filter="all",
        include_mrs=False,
        include_issues=False,
        include_code_files=True,
    )

    connector.load_credentials(
        {
            "gitlab_access_token": os.environ["GITLAB_ACCESS_TOKEN"],
            "gitlab_url": os.environ["GITLAB_URL"],
        }
    )
    document_batches = connector.load_from_state()
    print(next(document_batches))
