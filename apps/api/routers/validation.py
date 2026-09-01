"""API router for deterministic substation configuration validation."""
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from domain.models.results import ValidationResult
from services.validation.validator import ConfigurationValidator
from services.graph.repository import Neo4jGraphRepository
from services.safety.api_auth import require_api_key
from services.safety.rbac import SecurityContext

router = APIRouter(prefix="/validation", tags=["Configuration Validation"])
validator = ConfigurationValidator(Neo4jGraphRepository())


class ValidationRunRequest(BaseModel):
    bay_id: str = "BAY_F12"
    feeder_id: Optional[str] = "F12"
    ied_id: Optional[str] = "IED_12"
    custom_ct_mapping: Optional[Dict[str, str]] = None


@router.post("/run", response_model=ValidationResult)
async def run_configuration_validation(request: ValidationRunRequest, security: SecurityContext = Depends(require_api_key)):
    """Executes deterministic engineering rule validation against bay parameters and channel mappings."""
    result = await validator.validate_bay_configuration(
        bay_id=request.bay_id,
        feeder_id=request.feeder_id,
        ied_id=request.ied_id,
        custom_ied_mapping=request.custom_ct_mapping,
    )
    return result
