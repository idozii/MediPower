"""Exact allowlist for public, fictional MediPower research examples.

Keep in sync with web/lib/demo-presets.mjs. This is input minimization
for a demonstration, not patient-data identification or security certification.
"""
DEMO_SCENARIOS = frozenset({
    ("fever, cough, body aches, sore throat", "Melbourne", 5),
    ("recurring throbbing headache with sensitivity to light", "Sydney CBD", 5),
    ("lower abdominal pain with nausea", "Brisbane", 5),
})


def is_public_demo_request(text: str, location: str | None, top_k: int,
                           lat: float | None, lon: float | None) -> bool:
    if lat is not None or lon is not None or not isinstance(location, str):
        return False
    return (text, location, int(top_k)) in DEMO_SCENARIOS
