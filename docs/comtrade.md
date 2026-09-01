# COMTRADE Standard (IEEE C37.111 / IEC 60255-24) Architecture

## 1. Supported Format Specification
GridLens supports ASCII `.CFG` and `.DAT` oscillography files conforming to the IEEE C37.111-2013 standard subset.

### Configuration (`.CFG`) Structure
```
Station_Name,Device_Name,2013
8,4A,4D
1,IA,A,BAY_F12,A,1.0,0.0,0.0,-50000,50000,1200,5,P
2,IB,B,BAY_F12,A,1.0,0.0,0.0,-50000,50000,1200,5,P
3,IC,C,BAY_F12,A,1.0,0.0,0.0,-50000,50000,1200,5,P
4,VA,A,BAY_F12,V,1.0,0.0,0.0,-50000,50000,11000,110,P
1,50P_PKP,,,0
2,51P_TRIP,,,0
3,52A_BRK,,,1
4,52B_BRK,,,0
50.0
1
4000.0,800
2026-09-02 14:32:16.960000
2026-09-02 14:32:17.000000
ASCII
1.0
```

---

## 2. Deterministic Signal Analysis Algorithms

The deterministic signal analyzer (`services/comtrade/analyzer.py`) computes:

1. **Discrete Fourier Transform (DFT) & Sliding-Window RMS**:
   $$I_{RMS} = \sqrt{\frac{1}{N} \sum_{k=1}^{N} i[k]^2}$$
   where $N = 80$ samples per cycle at $4000\text{ Hz}$ sampling rate on $50\text{ Hz}$ nominal grid.
2. **True Fault Clearing Time ($\Delta t$)**:
   $$\Delta t = t_{52a\_open} - t_{pickup}$$
   Evaluated strictly from the edge transition of auxiliary contact 52A and primary current collapse.
3. **Zero-Crossing Frequency Estimation**:
   $$f = \frac{f_s}{2 \cdot \text{median}(\Delta k_{zero})}$$
4. **Phase Disturbance Attribution**:
   Identifies the faulted phase deterministically by comparing active fault RMS current across all analog channels against nominal load current.
