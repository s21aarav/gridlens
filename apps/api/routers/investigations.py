"""API router for running and retrieving agentic investigations."""
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from domain.investigation.models import InvestigationRequest, InvestigationResult
from services.agent.graph import GridLensInvestigationWorkflow
from services.safety.api_auth import require_api_key
from services.safety.rbac import SecurityContext
from services.config import INCIDENTS_FILE

router = APIRouter(prefix="/investigations", tags=["Investigations"])

# In-memory investigation storage for live review
_INVESTIGATION_CACHE: Dict[str, InvestigationResult] = {}
workflow = GridLensInvestigationWorkflow()
logger = logging.getLogger(__name__)


@router.post("", response_model=InvestigationResult)
async def run_investigation(request: InvestigationRequest, security: SecurityContext = Depends(require_api_key)):
    """Executes a stateful investigation with deterministic tool orchestration and claim verification."""
    try:
        # Load incident seed data if incident_id is passed
        incident_data = None
        if request.incident_id:
            with INCIDENTS_FILE.open("r", encoding="utf-8") as f:
                inc_list = json.load(f)
            for inc in inc_list:
                if inc["incident_id"] == request.incident_id:
                    incident_data = inc
                    break

        request.user_role = security.role.value
        result = await workflow.run_investigation(request, incident_data=incident_data)
        _INVESTIGATION_CACHE[result.investigation_id] = result
        return result
    except Exception:
        logger.exception("Investigation execution failed")
        raise HTTPException(status_code=500, detail="Investigation execution failed.")


@router.get("/{investigation_id}", response_model=InvestigationResult)
async def get_investigation(investigation_id: str):
    """Retrieves an existing investigation result."""
    if investigation_id in _INVESTIGATION_CACHE:
        return _INVESTIGATION_CACHE[investigation_id]
    raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found.")


@router.get("/{investigation_id}/trace")
async def get_investigation_trace(investigation_id: str):
    """Retrieves the full auditable execution trace for an investigation."""
    if investigation_id in _INVESTIGATION_CACHE:
        res = _INVESTIGATION_CACHE[investigation_id]
        return {
            "investigation_id": res.investigation_id,
            "investigation_type": res.investigation_type,
            "created_at": res.created_at,
            "duration_ms": res.duration_ms,
            "execution_trace": res.execution_trace,
        }
    raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found.")
