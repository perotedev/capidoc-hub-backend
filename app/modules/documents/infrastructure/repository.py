from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.domain.entities import DocStatus, DocumentEntity, DocumentTemplateEntity
from app.modules.documents.infrastructure.models import DocumentModel, DocumentTemplateModel


def _document_to_entity(model: DocumentModel) -> DocumentEntity:
    return DocumentEntity(
        id=model.id,
        attendance_id=model.attendance_id,
        form_id=model.form_id,
        form_name=model.form_name,
        operator_id=model.operator_id,
        operator_name=model.operator_name,
        project_id=model.project_id,
        template_id=model.template_id,
        template_name=model.template_name,
        status=DocStatus(model.status),
        validation_code=model.validation_code,
        pdf_file_key=model.pdf_file_key,
        generated_at=model.generated_at,
        revoked_at=model.revoked_at,
        revoked_by=model.revoked_by,
        revoke_reason=model.revoke_reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _template_to_entity(model: DocumentTemplateModel) -> DocumentTemplateEntity:
    return DocumentTemplateEntity(
        id=model.id,
        name=model.name,
        description=model.description,
        project_id=model.project_id,
        header_logo_key=model.header_logo_key,
        footer_text=model.footer_text,
        active=model.active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyDocumentRepository:
    """Postgres-backed implementation of `DocumentRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: UUID) -> DocumentEntity | None:
        model = await self._session.get(DocumentModel, document_id)
        return _document_to_entity(model) if model else None

    async def get_by_validation_code(self, validation_code: str) -> DocumentEntity | None:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.validation_code == validation_code)
        )
        model = result.scalar_one_or_none()
        return _document_to_entity(model) if model else None

    async def get_by_attendance_id(self, attendance_id: str) -> DocumentEntity | None:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.attendance_id == attendance_id)
        )
        model = result.scalar_one_or_none()
        return _document_to_entity(model) if model else None

    async def search(
        self, query: str | None, status: DocStatus | None, project_id: UUID | None
    ) -> list[DocumentEntity]:
        statement = select(DocumentModel)
        if status is not None:
            statement = statement.where(DocumentModel.status == status.value)
        if project_id is not None:
            statement = statement.where(DocumentModel.project_id == project_id)
        if query:
            like_pattern = f"%{query}%"
            statement = statement.where(
                or_(
                    DocumentModel.form_name.ilike(like_pattern),
                    DocumentModel.operator_name.ilike(like_pattern),
                    DocumentModel.validation_code.ilike(like_pattern),
                )
            )
        result = await self._session.execute(statement.order_by(DocumentModel.created_at.desc()))
        return [_document_to_entity(model) for model in result.scalars().all()]

    async def create(self, document: DocumentEntity) -> DocumentEntity:
        model = DocumentModel(
            id=document.id,
            attendance_id=document.attendance_id,
            form_id=document.form_id,
            form_name=document.form_name,
            operator_id=document.operator_id,
            operator_name=document.operator_name,
            project_id=document.project_id,
            template_id=document.template_id,
            template_name=document.template_name,
            status=document.status.value,
            validation_code=document.validation_code,
            pdf_file_key=document.pdf_file_key,
            generated_at=document.generated_at,
            revoked_at=document.revoked_at,
            revoked_by=document.revoked_by,
            revoke_reason=document.revoke_reason,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _document_to_entity(model)

    async def update(self, document: DocumentEntity) -> DocumentEntity:
        model = await self._session.get(DocumentModel, document.id)
        if model is None:
            raise ValueError(f"Document {document.id} not found")
        model.template_id = document.template_id
        model.template_name = document.template_name
        model.status = document.status.value
        model.pdf_file_key = document.pdf_file_key
        model.generated_at = document.generated_at
        model.revoked_at = document.revoked_at
        model.revoked_by = document.revoked_by
        model.revoke_reason = document.revoke_reason
        await self._session.commit()
        await self._session.refresh(model)
        return _document_to_entity(model)


class SqlAlchemyDocumentTemplateRepository:
    """Postgres-backed implementation of `DocumentTemplateRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, template_id: UUID) -> DocumentTemplateEntity | None:
        model = await self._session.get(DocumentTemplateModel, template_id)
        return _template_to_entity(model) if model else None

    async def list_by_project(self, project_id: UUID) -> list[DocumentTemplateEntity]:
        result = await self._session.execute(
            select(DocumentTemplateModel)
            .where(DocumentTemplateModel.project_id == project_id)
            .order_by(DocumentTemplateModel.name)
        )
        return [_template_to_entity(model) for model in result.scalars().all()]

    async def create(self, template: DocumentTemplateEntity) -> DocumentTemplateEntity:
        model = DocumentTemplateModel(
            id=template.id,
            name=template.name,
            description=template.description,
            project_id=template.project_id,
            header_logo_key=template.header_logo_key,
            footer_text=template.footer_text,
            active=template.active,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _template_to_entity(model)

    async def update(self, template: DocumentTemplateEntity) -> DocumentTemplateEntity:
        model = await self._session.get(DocumentTemplateModel, template.id)
        if model is None:
            raise ValueError(f"Document template {template.id} not found")
        model.name = template.name
        model.description = template.description
        model.header_logo_key = template.header_logo_key
        model.footer_text = template.footer_text
        model.active = template.active
        await self._session.commit()
        await self._session.refresh(model)
        return _template_to_entity(model)

    async def delete(self, template_id: UUID) -> None:
        model = await self._session.get(DocumentTemplateModel, template_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
