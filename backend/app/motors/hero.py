"""Hero + supporting motor selection (Milestone 3.1.5)."""

from __future__ import annotations

from typing import Any

# Pack / type codes aligned with local Low Voltage Motors corpus.
HERO_MOTOR_CODE = "Low_Voltage_Motor-001"

SUPPORTING_MOTOR_CODES: tuple[str, ...] = (
    "Low_Voltage_Motor-002",
    "Low_Voltage_Motor-003",
    "Low_Voltage_Motor-004",
    "Low_Voltage_Motor-005",
)

# Spec enrichment hints for demo (catalog-driven fields when available).
HERO_SPEC_HINTS: dict[str, dict[str, Any]] = {
    HERO_MOTOR_CODE: {
        "frame_size": "160",
        "power_kw": 15.0,
        "voltage": "400V",
        "ie_class": "IE3",
        "poles": 4,
        "cooling": "IC411",
        "name": "M3BP 160MLA4 (Hero LV Motor)",
        "aliases": ["M3BP 160MLA4", "160MLA4", HERO_MOTOR_CODE],
    },
    "Low_Voltage_Motor-002": {
        "frame_size": "132",
        "power_kw": 7.5,
        "voltage": "400V",
        "ie_class": "IE3",
        "poles": 4,
        "name": "LV Motor Pack 002",
        "aliases": ["Low_Voltage_Motor-002"],
    },
    "Low_Voltage_Motor-003": {
        "frame_size": "180",
        "power_kw": 22.0,
        "voltage": "400V",
        "ie_class": "IE2",
        "poles": 4,
        "name": "LV Motor Pack 003",
        "aliases": ["Low_Voltage_Motor-003"],
    },
    "Low_Voltage_Motor-004": {
        "frame_size": "112",
        "power_kw": 5.5,
        "voltage": "400V",
        "ie_class": "IE3",
        "poles": 2,
        "name": "LV Motor Pack 004",
        "aliases": ["Low_Voltage_Motor-004"],
    },
    "Low_Voltage_Motor-005": {
        "frame_size": "200",
        "power_kw": 30.0,
        "voltage": "400V",
        "ie_class": "IE4",
        "poles": 4,
        "name": "LV Motor Pack 005",
        "aliases": ["Low_Voltage_Motor-005"],
    },
}

DEFAULT_FAMILY_CODE = "M3BP"
DEFAULT_FAMILY_NAME = "M3BP Process Performance"
