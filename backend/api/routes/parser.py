from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db, get_parser_service
from backend.core.parser.service import ParserService
from backend.database.repositories import RepositoryRepository
from backend.schemas.parser import (
    ClassDetail,
    FileDetailResponse,
    FunctionDetail,
    ImportDetail,
    ParseResponse,
    RepositoryStructureResponse,
    StructureCodeFile,
    StructureFunction,
    StructureImport,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["parser"])


@router.post("/{repository_id}/parse", response_model=ParseResponse)
async def parse_repository(
    repository_id: str,
    parser_service: ParserService = Depends(get_parser_service),
) -> ParseResponse:
    """Parse every supported source file in an already-ingested repository.

    Extracts classes, functions, methods, imports, decorators, docstrings,
    line numbers, and class inheritance from all supported source files.
    """
    try:
        files_parsed = await parser_service.parse_repository(repository_id)
        return ParseResponse(
            repository_id=repository_id,
            files_parsed=files_parsed,
            status="completed",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{repository_id}/structure", response_model=RepositoryStructureResponse)
async def get_repository_structure(
    repository_id: str,
    session: AsyncSession = Depends(get_db),
    parser_service: ParserService = Depends(get_parser_service),
) -> RepositoryStructureResponse:
    """Return the full parse structure for a repository.

    Returns all files, classes, functions, methods, and imports that were
    extracted during parsing.
    """
    repo_repo = RepositoryRepository(session)

    try:
        repo = await repo_repo.get_by_id(repository_id)
        if repo is None:
            raise ValueError("Repository not found")

        code_files = await parser_service.get_repository_structure(repository_id)

        files = []
        for cf in code_files:
            classes = []
            for cls in cf.classes:
                methods = [
                    StructureFunction(
                        id=m.id,
                        name=m.name,
                        line_start=m.line_start,
                        line_end=m.line_end,
                        is_async=m.is_async,
                        docstring=m.docstring,
                        decorators=m.decorators,
                    )
                    for m in cls.methods
                ]
                classes.append(
                    ClassDetail(
                        id=cls.id,
                        name=cls.name,
                        line_start=cls.line_start,
                        line_end=cls.line_end,
                        docstring=cls.docstring,
                        decorators=cls.decorators,
                        bases=cls.bases,
                        methods=methods,
                    )
                )

            functions = [
                StructureFunction(
                    id=f.id,
                    name=f.name,
                    line_start=f.line_start,
                    line_end=f.line_end,
                    is_async=f.is_async,
                    docstring=f.docstring,
                    decorators=f.decorators,
                )
                for f in cf.functions
            ]

            imports = [
                StructureImport(
                    id=imp.id,
                    module=imp.module,
                    imported_name=imp.imported_name,
                    alias=imp.alias,
                )
                for imp in cf.imports
            ]

            files.append(
                StructureCodeFile(
                    id=cf.id,
                    path=cf.path,
                    language=cf.language,
                    classes=classes,
                    functions=functions,
                    imports=imports,
                )
            )

        return RepositoryStructureResponse(
            repository_id=repo.id,
            repository_name=repo.name,
            repository_owner=repo.owner,
            total_files=len(files),
            files=files,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{repository_id}/files/{file_id}", response_model=FileDetailResponse)
async def get_parsed_file_detail(
    repository_id: str,
    file_id: str,
    parser_service: ParserService = Depends(get_parser_service),
) -> FileDetailResponse:
    """Return detailed structural information for a single parsed file."""
    try:
        code_file = await parser_service.get_parsed_file(file_id)
        if code_file is None or code_file.repository_id != repository_id:
            raise ValueError(
                f"File {file_id} not found in repository {repository_id}"
            )

        classes = []
        for cls in code_file.classes:
            methods = [
                StructureFunction(
                    id=m.id,
                    name=m.name,
                    line_start=m.line_start,
                    line_end=m.line_end,
                    is_async=m.is_async,
                    docstring=m.docstring,
                    decorators=m.decorators,
                )
                for m in cls.methods
            ]
            classes.append(
                ClassDetail(
                    id=cls.id,
                    name=cls.name,
                    line_start=cls.line_start,
                    line_end=cls.line_end,
                    docstring=cls.docstring,
                    decorators=cls.decorators,
                    bases=cls.bases,
                    methods=methods,
                )
            )

        functions = [
            FunctionDetail(
                id=f.id,
                name=f.name,
                line_start=f.line_start,
                line_end=f.line_end,
                is_async=f.is_async,
                docstring=f.docstring,
                decorators=f.decorators,
            )
            for f in code_file.functions
        ]

        imports = [
            ImportDetail(
                id=imp.id,
                module=imp.module,
                imported_name=imp.imported_name,
                alias=imp.alias,
            )
            for imp in code_file.imports
        ]

        return FileDetailResponse(
            id=code_file.id,
            path=code_file.path,
            language=code_file.language,
            classes=classes,
            functions=functions,
            imports=imports,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc