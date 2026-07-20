from fastapi import APIRouter

from app.modules.documents.api.v1.dependencies import DocumentServiceDep
from app.modules.documents.application.schemas import DocumentValidationResponse

router = APIRouter(prefix="/validation", tags=["Validation"])


@router.get("/{validation_code}", response_model=DocumentValidationResponse)
async def validate_document(validation_code: str, service: DocumentServiceDep) -> DocumentValidationResponse:
    """Public, unauthenticated lookup used by third parties to confirm a document's authenticity."""
    return await service.validate_code(validation_code)
