"""COMTRADE (IEEE C37.111 / IEC 60255-24) parser for ASCII CFG and DAT files."""
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field


class AnalogChannelHeader(BaseModel):
    index: int
    name: str
    phase: str
    circuit_component: str
    units: str
    multiplier: float
    offset: float
    skew: float
    min_val: float
    max_val: float
    primary_ratio: float
    secondary_ratio: float
    scaling_type: str = "P"  # "P" for primary, "S" for secondary


class DigitalChannelHeader(BaseModel):
    index: int
    name: str
    phase: str
    circuit_component: str
    normal_state: int = 0


class ComtradeHeader(BaseModel):
    station_name: str
    device_name: str
    version_year: str = "2013"
    total_channels: int
    num_analog: int
    num_digital: int
    analog_channels: List[AnalogChannelHeader] = Field(default_factory=list)
    digital_channels: List[DigitalChannelHeader] = Field(default_factory=list)
    nominal_frequency: float = 50.0
    sampling_rates: List[Tuple[float, int]] = Field(default_factory=list)  # (rate_hz, end_sample)
    start_timestamp: str = ""
    trigger_timestamp: str = ""
    data_format: str = "ASCII"
    timestamp_multiplier: float = 1.0  # Microseconds


class ComtradeRecord(BaseModel):
    header: ComtradeHeader
    sample_indices: List[int] = Field(default_factory=list)
    time_microseconds: List[float] = Field(default_factory=list)
    time_milliseconds: List[float] = Field(default_factory=list)
    analog_data: Dict[str, List[float]] = Field(default_factory=dict)  # Channel Name -> list of primary values
    digital_data: Dict[str, List[int]] = Field(default_factory=dict)   # Channel Name -> list of 0/1 bits
    is_truncated: bool = False


class ComtradeParser:
    """Deterministic parser for IEEE C37.111 COMTRADE CFG and DAT files."""

    @classmethod
    def parse_files(cls, cfg_path: str, dat_path: str) -> ComtradeRecord:
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"COMTRADE CFG file not found at: {cfg_path}")
        if not os.path.exists(dat_path):
            raise FileNotFoundError(f"COMTRADE DAT file not found at: {dat_path}")

        with open(cfg_path, "r", encoding="utf-8", errors="replace") as f:
            cfg_content = f.read()

        with open(dat_path, "r", encoding="utf-8", errors="replace") as f:
            dat_content = f.read()

        header = cls.parse_cfg(cfg_content)
        record = cls.parse_dat(dat_content, header)
        return record

    @classmethod
    def parse_cfg(cls, cfg_text: str) -> ComtradeHeader:
        lines = [line.strip() for line in cfg_text.strip().splitlines() if line.strip()]
        if len(lines) < 5:
            raise ValueError(f"Malformed COMTRADE CFG file. Expected at least 5 lines, got {len(lines)}")

        # Line 1: Station, Device, Version
        line1 = [p.strip() for p in lines[0].split(",")]
        station_name = line1[0] if len(line1) > 0 else "UNKNOWN"
        device_name = line1[1] if len(line1) > 1 else "RELAY"
        version_year = line1[2] if len(line1) > 2 else "2013"

        # Line 2: Total channels, num analog (A), num digital (D)
        line2 = [p.strip() for p in lines[1].split(",")]
        total_ch = int(line2[0])
        num_analog = int(line2[1].rstrip("A").strip())
        num_digital = int(line2[2].rstrip("D").strip())

        curr_line = 2
        analog_channels: List[AnalogChannelHeader] = []
        for i in range(num_analog):
            parts = [p.strip() for p in lines[curr_line].split(",")]
            ch = AnalogChannelHeader(
                index=int(parts[0]),
                name=parts[1],
                phase=parts[2] if len(parts) > 2 else "",
                circuit_component=parts[3] if len(parts) > 3 else "",
                units=parts[4] if len(parts) > 4 else "A",
                multiplier=float(parts[5]) if len(parts) > 5 else 1.0,
                offset=float(parts[6]) if len(parts) > 6 else 0.0,
                skew=float(parts[7]) if len(parts) > 7 else 0.0,
                min_val=float(parts[8]) if len(parts) > 8 else -99999.0,
                max_val=float(parts[9]) if len(parts) > 9 else 99999.0,
                primary_ratio=float(parts[10]) if len(parts) > 10 else 1.0,
                secondary_ratio=float(parts[11]) if len(parts) > 11 else 1.0,
                scaling_type=parts[12] if len(parts) > 12 else "P",
            )
            analog_channels.append(ch)
            curr_line += 1

        digital_channels: List[DigitalChannelHeader] = []
        for i in range(num_digital):
            parts = [p.strip() for p in lines[curr_line].split(",")]
            d_ch = DigitalChannelHeader(
                index=int(parts[0]),
                name=parts[1],
                phase=parts[2] if len(parts) > 2 else "",
                circuit_component=parts[3] if len(parts) > 3 else "",
                normal_state=int(parts[4]) if len(parts) > 4 else 0,
            )
            digital_channels.append(d_ch)
            curr_line += 1

        # Nominal frequency
        nominal_freq = float(lines[curr_line].split(",")[0])
        curr_line += 1

        # Sampling rates
        num_rates = int(lines[curr_line].split(",")[0])
        curr_line += 1
        sampling_rates = []
        for _ in range(num_rates):
            parts = [p.strip() for p in lines[curr_line].split(",")]
            sampling_rates.append((float(parts[0]), int(parts[1])))
            curr_line += 1

        # Timestamps
        start_ts = lines[curr_line] if curr_line < len(lines) else ""
        curr_line += 1
        trigger_ts = lines[curr_line] if curr_line < len(lines) else ""
        curr_line += 1

        # Format and multiplier
        data_format = lines[curr_line] if curr_line < len(lines) else "ASCII"
        curr_line += 1
        time_mult = float(lines[curr_line]) if curr_line < len(lines) else 1.0

        return ComtradeHeader(
            station_name=station_name,
            device_name=device_name,
            version_year=version_year,
            total_channels=total_ch,
            num_analog=num_analog,
            num_digital=num_digital,
            analog_channels=analog_channels,
            digital_channels=digital_channels,
            nominal_frequency=nominal_freq,
            sampling_rates=sampling_rates,
            start_timestamp=start_ts,
            trigger_timestamp=trigger_ts,
            data_format=data_format,
            timestamp_multiplier=time_mult,
        )

    @classmethod
    def parse_dat(cls, dat_text: str, header: ComtradeHeader) -> ComtradeRecord:
        lines = [line.strip() for line in dat_text.strip().splitlines() if line.strip()]
        
        sample_indices: List[int] = []
        time_us: List[float] = []
        time_ms: List[float] = []
        
        analog_data: Dict[str, List[float]] = {ch.name: [] for ch in header.analog_channels}
        digital_data: Dict[str, List[int]] = {d.name: [] for d in header.digital_channels}

        for line_idx, line in enumerate(lines):
            tokens = [t.strip() for t in line.split(",")]
            expected_tokens = 2 + header.num_analog + header.num_digital
            if len(tokens) < expected_tokens:
                # Truncated or incomplete line
                continue
            
            s_idx = int(tokens[0])
            t_val = float(tokens[1]) * header.timestamp_multiplier
            sample_indices.append(s_idx)
            time_us.append(t_val)
            time_ms.append(t_val / 1000.0)

            # Parse analog values
            ptr = 2
            for ch in header.analog_channels:
                raw_val = float(tokens[ptr])
                # Physical value = a * raw + b
                scaled_val = (ch.multiplier * raw_val) + ch.offset
                analog_data[ch.name].append(scaled_val)
                ptr += 1

            # Parse digital bits
            for d_ch in header.digital_channels:
                bit_val = int(tokens[ptr])
                digital_data[d_ch.name].append(bit_val)
                ptr += 1

        # Detect truncation: if total recorded samples < expected end sample
        expected_samples = header.sampling_rates[0][1] if header.sampling_rates else 800
        is_truncated = len(sample_indices) < (expected_samples * 0.5)

        return ComtradeRecord(
            header=header,
            sample_indices=sample_indices,
            time_microseconds=time_us,
            time_milliseconds=time_ms,
            analog_data=analog_data,
            digital_data=digital_data,
            is_truncated=is_truncated,
        )
