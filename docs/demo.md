# Five-Minute Demonstration Script for Technical Interviewers

## 1. Demo Narrative Overview
This 5-minute demonstration walks through the three flagship incidents to prove that:
1. **Incident A**: High-confidence genuine overcurrent fault is grounded in deterministic COMTRADE math and graph facts.
2. **Incident B**: Conflicting cross-source evidence (relay text vs waveform vs secondary wiring) is discovered and resolved rather than blindly trusted.
3. **Incident C**: Incomplete/truncated evidence triggers the Contextual Sufficiency Gate, forcing explicit, safe abstention.

---

## 2. Step-by-Step Walkthrough

### Step 1: Open Grid Overview
- Navigate to `http://localhost:3000/`.
- Present the Single-Line Diagram for **Orion Grid Substation OGS-01**.
- Point out Bus A (33 kV), Power Transformer T1, Bus B (11 kV), and Feeder Bays F12 & F13.

### Step 2: Flagship Incident A (Genuine Overcurrent Trip)
- Click on **Incident INC-2026-001** (Feeder F12 Phase C Overcurrent Trip).
- Inspect the interactive COMTRADE waveform and compare the Phase C surge with the structured measurement of approximately $3748\text{ A}$ RMS.
- Click **"Start Agent Investigation"** with query: *"Why did feeder F12 trip at 14:32?"*.
- **Demonstrate**:
  - Top Hypothesis $H_1$ selected with the confidence shown by the current run.
  - Verified Claim Ledger: approximately $3748\text{ A}$ RMS current verified from COMTRADE, primary relay verified from the seeded topology repository.
  - Citations linking to `DOC-PROT-001` (ANSI 51 time-overcurrent curves).
  - Auditable 6-step Execution Trace.

### Step 3: Flagship Incident B (Cross-Source Contradiction Resolution)
- Select preset: **Incident B: Deceptive CT Inversion**.
- **Demonstrate**:
  - Relay event text reported Phase A overcurrent.
  - COMTRADE analyzer measured Phase A normal ($238\text{ A}$) and Phase C abnormal ($3450\text{ A}$).
  - Validator detected Rule `RULE-MAP-003` (CT Phase inversion).
  - Conflict Lifecycle transitioned from `CONFLICT_DETECTED` to `CONFLICT_RESOLVED`.
  - Top Hypothesis $H_3$ correctly identified secondary CT wiring swap.

### Step 4: Flagship Incident C (True Abstention under Missing Evidence)
- Select preset: **Incident C: Insufficient Evidence**.
- **Demonstrate**:
  - Waveform capture was truncated at $30\text{ ms}$; CT ratio setting was missing ($0/0$).
  - Sufficiency Policy Gate evaluated status: `INSUFFICIENT EVIDENCE (ABSTAINED)`.
  - The system refused to guess or hallucinate a root cause, itemizing the exact missing data required.

### Step 5: Benchmarking & Ablation Dashboard
- Navigate to `/evaluation`.
- Show the live benchmark results: 26 synthetic regression cases with metrics computed at runtime. The current seeded suite should not be presented as field accuracy.
