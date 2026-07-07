from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ParseResponse(BaseModel):
    """Response returned after parsing a repository."""

    repository_id: str
    files_parsed: int
    status: str = "completed"


class StructureImport(BaseModel):
    """An import statement in the structure view."""

    id: str
    module: str
    imported_name: str
    alias: str | None = None

    model_config = {"from_attributes": True}


class StructureFunction(BaseModel):
    """A function or method in the structure view."""

    id: str
    name: str
    line_start: int
    line_end: int
    is_async: bool = False
    docstring: str | None = None
    decorators: str | None = None

    model_config = {"from_attributes": True}


class StructureCodeFile(BaseModel):
    """A parsed code file in the structure view."""

    id: str
    path: str
    language: str
    classes: list[ClassDetail] = Field(default_factory=list)
    functions: list[StructureFunction] = Field(default_factory=list)
    imports: list[StructureImport] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ClassDetail(BaseModel):
    """A class with its methods in the structure view."""

    id: str
    name: str
    line_start: int
    line_end: int
    docstring: str | None = None
    decorators: str | None = None
    bases: str | None = None
    methods: list[StructureFunction] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RepositoryStructureResponse(BaseModel):
    """Full parse structure for a repository."""

    repository_id: str
    repository_name: str
    repository_owner: str
    total_files: int
    files: list[StructureCodeFile]


class FileStructureItem(BaseModel):
    """A compact structure item for the per-file view."""

    file_id: str
    path: str
    language: str


class FileDetailResponse(BaseModel):
    """Detailed information for a single parsed file."""

    id: str
    path: str
    language: str
    classes: list[ClassDetail] = Field(default_factory=list)
    functions: list[FunctionDetail] = Field(default_factory=list)
    imports: list[ImportDetail] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class FunctionDetail(BaseModel):
    """Detailed function information."""

    id: str
    name: str
    line_start: int
    line_end: int
    is_async: bool = False
    docstring: str | None = None
    decorators: str | None = None

    model_config = {"from_attributes": True}


class ImportDetail(BaseModel):
    """Detailed import information."""

    id: str
    module: str
    imported_name: str
    alias: str | None = None

    model_config = {"from_attributes": True}