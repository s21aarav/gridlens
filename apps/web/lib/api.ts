/**
 * API client connecting Next.js frontend to FastAPI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function fetchIncidents() {
  const res = await fetch(`${API_BASE_URL}/incidents`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch incidents catalog');
  return res.json();
}

export async function fetchIncident(id: string) {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to fetch incident ${id}`);
  return res.json();
}

export async function fetchComtrade(id: string) {
  const res = await fetch(`${API_BASE_URL}/incidents/${id}/comtrade`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Failed to fetch COMTRADE oscillography for ${id}`);
  return res.json();
}

export async function fetchSubstationTopology() {
  const res = await fetch(`${API_BASE_URL}/graph/topology`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch substation topology');
  return res.json();
}

export async function runInvestigation(query: string, incidentId?: string, role: string = 'ENGINEER') {
  const res = await fetch(`${API_BASE_URL}/investigations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_query: query,
      incident_id: incidentId,
      user_role: role,
    }),
  });
  if (!res.ok) throw new Error('Investigation execution failed');
  return res.json();
}

export async function runValidation(bayId: string = 'BAY_F12', customMapping?: Record<string, string>) {
  const res = await fetch(`${API_BASE_URL}/validation/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bay_id: bayId,
      custom_ct_mapping: customMapping,
    }),
  });
  if (!res.ok) throw new Error('Validation run failed');
  return res.json();
}

export async function fetchEvaluationResults() {
  const res = await fetch(`${API_BASE_URL}/evaluation/results`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch evaluation benchmark results');
  return res.json();
}

export async function triggerEvaluationRun() {
  const res = await fetch(`${API_BASE_URL}/evaluation/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to execute evaluation run');
  return res.json();
}

export async function submitSimulatedAction(actionType: string, equipmentId: string, role: string, justification: string) {
  const res = await fetch(`${API_BASE_URL}/actions/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action_type: actionType,
      target_equipment_id: equipmentId,
      user_role: role,
      justification: justification,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Action submission failed');
  }
  return res.json();
}

export async function approveSimulatedAction(actionId: string, role: string = 'APPROVER') {
  const res = await fetch(`${API_BASE_URL}/actions/${actionId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      approver_role: role,
      approver_username: 'supervisor_bob',
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Approval failed');
  }
  return res.json();
}
