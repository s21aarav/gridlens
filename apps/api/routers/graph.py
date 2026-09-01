"""API router for Substation Knowledge Graph and topology querying."""
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from services.graph.repository import Neo4jGraphRepository

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])
graph_repo = Neo4jGraphRepository()


@router.get("/topology")
async def get_substation_topology():
    """Retrieves full Single-Line Diagram topology and equipment hierarchy for Substation OGS-01."""
    return await graph_repo.get_substation_topology()


@router.get("/feeder/{feeder_id}/protection-chain")
async def get_feeder_protection_chain(feeder_id: str):
    """Retrieves upstream bus, primary relay, breaker, sensors, and downstream loads for a feeder."""
    return await graph_repo.get_feeder_protection_chain(feeder_id)


@router.get("/equipment/{equipment_id}")
async def get_equipment_details(equipment_id: str):
    """Retrieves detailed relationships and parameters for any substation equipment."""
    res = await graph_repo.get_equipment_relationships(equipment_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
