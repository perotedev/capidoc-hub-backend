from typing import Protocol
from uuid import UUID

from app.modules.document_imports.domain.entities import DocumentImportEntity


class DocumentImportRepository(Protocol):
    async def get_by_id(self, import_id: UUID) -> DocumentImportEntity | None: ...

    async def create(self, document_import: DocumentImportEntity) -> DocumentImportEntity: ...

    async def update(self, document_import: DocumentImportEntity) -> DocumentImportEntity: ...
