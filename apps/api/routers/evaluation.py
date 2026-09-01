"""API router for benchmark evaluation suite and ablation comparison."""
from fastapi import APIRouter, Depends
from services.evaluation.evaluator import SystemEvaluator
from services.safety.api_auth import require_api_key
from services.safety.rbac import SecurityContext

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])


@router.get("/results")
async def get_evaluation_results():
    """Retrieves comparative benchmark results between Baseline, Full GridLens, and 6 Ablations."""
    return await SystemEvaluator.get_comparative_benchmark()


@router.post("/run")
async def trigger_evaluation_run(security: SecurityContext = Depends(require_api_key)):
    """Runs the full golden test suite dynamically and updates benchmark scores."""
    report = await SystemEvaluator.evaluate_full_gridlens()
    return report
