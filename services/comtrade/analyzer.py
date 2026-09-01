"""Deterministic signal analyzer for COMTRADE recordings (IEEE C37.111 / IEC 60255-24)."""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from domain.models.results import ComtradeAnalysisResult, ChannelMeasurement
from services.comtrade.parser import ComtradeRecord


class ComtradeSignalAnalyzer:
    """Deterministic, mathematical analysis of COMTRADE waveforms."""

    @classmethod
    def analyze_record(
        cls,
        record: ComtradeRecord,
        incident_id: str,
        pickup_threshold_a: float = 2500.0,
        nominal_freq: float = 50.0,
    ) -> ComtradeAnalysisResult:
        if not record.time_milliseconds or not record.analog_data:
            return ComtradeAnalysisResult(
                incident_id=incident_id,
                sample_rate_hz=record.header.sampling_rates[0][0] if record.header.sampling_rates else 4000.0,
                total_samples=len(record.sample_indices),
                duration_ms=0.0,
                is_truncated=True,
                analysis_notes=["Empty or corrupted waveform recording."],
            )

        t_ms = np.array(record.time_milliseconds)
        duration_ms = float(t_ms[-1] - t_ms[0]) if len(t_ms) > 1 else 0.0
        sample_rate = float(record.header.sampling_rates[0][0]) if record.header.sampling_rates else 4000.0
        samples_per_cycle = int(round(sample_rate / nominal_freq)) if nominal_freq > 0 else 80

        # Identify disturbance start and transition points from digital flags or derivative
        pickup_time_ms: Optional[float] = None
        trip_time_ms: Optional[float] = None
        breaker_open_ms: Optional[float] = None
        digital_transitions: List[Dict[str, Any]] = []

        # Parse digital channels for standard relay bit flags: 50P_PKP, 51P_TRIP, 52A_BRK, 52B_BRK
        for d_name, bits in record.digital_data.items():
            b_arr = np.array(bits)
            diffs = np.diff(b_arr)
            transitions = np.where(diffs != 0)[0]
            for idx in transitions:
                trans_time = float(t_ms[idx + 1])
                old_val = int(b_arr[idx])
                new_val = int(b_arr[idx + 1])
                digital_transitions.append({
                    "channel": d_name,
                    "time_ms": trans_time,
                    "old_val": old_val,
                    "new_val": new_val,
                })
                
                d_upper = d_name.upper()
                if "PKP" in d_upper or "PICKUP" in d_upper or "50P" in d_upper or "51P_PKP" in d_upper:
                    if new_val == 1 and pickup_time_ms is None:
                        pickup_time_ms = trans_time
                elif "TRIP" in d_upper or "51P_TRIP" in d_upper or "TRP" in d_upper:
                    if new_val == 1 and trip_time_ms is None:
                        trip_time_ms = trans_time
                elif "52A" in d_upper or "BREAKER" in d_upper or "BRK" in d_upper:
                    if new_val == 0 and breaker_open_ms is None:  # 52A transitions to 0 when breaker opens
                        breaker_open_ms = trans_time

        # Disturbance start: locate where pickup occurred or standard 40ms pre-fault split
        start_fault_idx = int(len(t_ms) * 0.20)  # Standard 40ms in a 200ms record
        if pickup_time_ms is not None:
            pkp_idxs = np.where(t_ms >= pickup_time_ms)[0]
            if len(pkp_idxs) > 0:
                # Inception is typically 10-15ms before pickup
                start_fault_idx = max(0, pkp_idxs[0] - int(samples_per_cycle * 0.5))

        end_fault_idx = len(t_ms)
        if breaker_open_ms is not None:
            brk_idxs = np.where(t_ms >= breaker_open_ms)[0]
            if len(brk_idxs) > 0:
                end_fault_idx = brk_idxs[0]

        analog_measurements: Dict[str, ChannelMeasurement] = {}
        max_fault_current = 0.0
        fault_phase_detected: Optional[str] = None
        pickup_exceeded = False

        for ch in record.header.analog_channels:
            raw_vals = np.array(record.analog_data.get(ch.name, []))
            if len(raw_vals) == 0:
                continue

            # Pure pre-fault window
            pre_window = raw_vals[:start_fault_idx] if start_fault_idx > 0 else raw_vals[:samples_per_cycle]
            pre_rms = cls._calculate_rms(pre_window)

            # Pure active fault window
            fault_window = raw_vals[start_fault_idx:end_fault_idx] if end_fault_idx > start_fault_idx else raw_vals[start_fault_idx:]
            fault_rms = cls._calculate_rms(fault_window) if len(fault_window) > 0 else pre_rms
            peak_val = float(np.max(np.abs(fault_window))) if len(fault_window) > 0 else float(np.max(np.abs(raw_vals)))
            delta_val = float(fault_rms - pre_rms)

            measurement = ChannelMeasurement(
                channel_name=ch.name,
                phase=ch.phase,
                pre_fault_rms=round(pre_rms, 2),
                fault_rms=round(fault_rms, 2),
                peak_value=round(peak_val, 2),
                delta_value=round(delta_val, 2),
                unit=ch.units,
            )
            analog_measurements[ch.name] = measurement

            # Check if this is a current channel and exceeds pickup
            if ch.units.upper() in ["A", "AMPS", "KA"] or ch.name.upper().startswith("I"):
                if fault_rms > max_fault_current:
                    max_fault_current = fault_rms
                    fault_phase_detected = ch.phase if ch.phase else ch.name

                if fault_rms >= pickup_threshold_a or peak_val >= (pickup_threshold_a * 1.414):
                    pickup_exceeded = True

        # Calculate clearing time
        total_clearing_time_ms: Optional[float] = None
        if pickup_time_ms is not None and breaker_open_ms is not None:
            # Net clearing time from fault inception / pickup
            total_clearing_time_ms = round(breaker_open_ms - float(t_ms[start_fault_idx]), 2)
        elif breaker_open_ms is not None and len(t_ms) > 0:
            total_clearing_time_ms = round(breaker_open_ms - float(t_ms[0]), 2)

        freq_est = cls._estimate_frequency(record, sample_rate)

        notes: List[str] = []
        if record.is_truncated:
            notes.append("WARNING: Waveform recording was truncated before full post-fault recovery.")
        if pickup_exceeded:
            notes.append(f"Overcurrent threshold ({pickup_threshold_a} A) exceeded on {fault_phase_detected} (Fault RMS: {round(max_fault_current, 1)} A).")
        if total_clearing_time_ms:
            notes.append(f"Fault cleared in {total_clearing_time_ms} ms (Breaker opened at {breaker_open_ms} ms).")

        return ComtradeAnalysisResult(
            incident_id=incident_id,
            sample_rate_hz=sample_rate,
            total_samples=len(record.sample_indices),
            duration_ms=round(duration_ms, 2),
            is_truncated=record.is_truncated,
            analog_measurements=analog_measurements,
            frequency_hz=round(freq_est, 2) if freq_est else None,
            fault_phase_detected=fault_phase_detected,
            pickup_threshold_a=pickup_threshold_a,
            pickup_exceeded=pickup_exceeded,
            pickup_time_ms=pickup_time_ms,
            trip_time_ms=trip_time_ms,
            breaker_open_time_ms=breaker_open_ms,
            total_clearing_time_ms=total_clearing_time_ms,
            digital_transitions=digital_transitions,
            analysis_notes=notes,
        )

    @staticmethod
    def _calculate_rms(signal: np.ndarray) -> float:
        if len(signal) == 0:
            return 0.0
        return float(np.sqrt(np.mean(signal ** 2)))

    @staticmethod
    def _estimate_frequency(record: ComtradeRecord, sample_rate: float) -> Optional[float]:
        for ch_name, data in record.analog_data.items():
            arr = np.array(data)
            if len(arr) < 100 or np.max(np.abs(arr)) < 1.0:
                continue
            zero_crossings = np.where(np.diff(np.sign(arr)))[0]
            if len(zero_crossings) >= 4:
                half_periods = np.diff(zero_crossings)
                avg_half_period = np.median(half_periods)
                if avg_half_period > 0:
                    period_samples = avg_half_period * 2
                    return float(sample_rate / period_samples)
        return 50.0
