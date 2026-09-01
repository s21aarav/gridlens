"""Unit tests for COMTRADE parser and deterministic signal analyzer."""
import pytest
import os
from services.comtrade.parser import ComtradeParser
from services.comtrade.analyzer import ComtradeSignalAnalyzer


def test_parse_and_analyze_incident_a():
    cfg_path = "data/comtrade/INC-2026-001.CFG"
    dat_path = "data/comtrade/INC-2026-001.DAT"
    assert os.path.exists(cfg_path), "Incident A CFG file must exist."
    assert os.path.exists(dat_path), "Incident A DAT file must exist."

    record = ComtradeParser.parse_files(cfg_path, dat_path)
    assert record.header.station_name == "OGS-01"
    assert record.header.num_analog == 4
    assert record.header.num_digital == 4
    assert len(record.sample_indices) > 0
    assert not record.is_truncated

    analysis = ComtradeSignalAnalyzer.analyze_record(record, incident_id="INC-2026-001")
    assert analysis.pickup_exceeded is True
    assert analysis.fault_phase_detected in ["C", "IC"]
    assert analysis.analog_measurements["IC"].fault_rms > 3500.0
    assert analysis.analog_measurements["IA"].fault_rms < 300.0
    assert analysis.total_clearing_time_ms is not None
    assert 40.0 <= analysis.total_clearing_time_ms <= 70.0


def test_incident_c_truncation_detection():
    cfg_path = "data/comtrade/INC-2026-003.CFG"
    dat_path = "data/comtrade/INC-2026-003.DAT"
    assert os.path.exists(cfg_path)

    record = ComtradeParser.parse_files(cfg_path, dat_path)
    assert record.is_truncated is True

    analysis = ComtradeSignalAnalyzer.analyze_record(record, incident_id="INC-2026-003")
    assert analysis.is_truncated is True
    assert any("truncated" in note.lower() for note in analysis.analysis_notes)
