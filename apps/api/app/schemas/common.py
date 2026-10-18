from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    """The list envelope used by every list endpoint: {items, total, page, limit}."""

    items: list[T]
    total: int
    page: int
    limit: int