"""Schema package - Pydantic models for request/response validation."""

from .search import QuerySection, SearchRequest, SearchResponse
from .search_augmented import AugmentedSearchResponse
from .search_image import ImageSearchRequest, ImageSearchResponse
from .search_multistage import (
    StageQuerySection,
    MultiStageSearchRequest,
    StageSearchResult,
    MultiStageSearchResponse,
)
from .chatbox import (
    SubmitAnswerRequest,
    SubmissionResponse,
    SubmitAnswerResponse,
    FetchSubmissionsResponse,
    UniqueQueriesResponse,
    DeleteSubmissionResponse,
)

__all__ = [
    "QuerySection",
    "SearchRequest",
    "SearchResponse",
    "AugmentedSearchResponse",
    "ImageSearchRequest",
    "ImageSearchResponse",
    "StageQuerySection",
    "MultiStageSearchRequest",
    "StageSearchResult",
    "MultiStageSearchResponse",
    "SubmitAnswerRequest",
    "SubmissionResponse",
    "SubmitAnswerResponse",
    "FetchSubmissionsResponse",
    "UniqueQueriesResponse",
    "DeleteSubmissionResponse",
]
