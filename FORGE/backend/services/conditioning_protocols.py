"""
conditioning_protocols.py — the sport-agnostic reference material from the
Combat Sports & Rugby Strength & Conditioning Manual that sits *around* the
lifting templates rather than inside them: what aerobic vs. lactic training
actually is (Part 2), the pick-one-of-these session menus for each (Part 6),
the pre-lift warm-up protocol (Part 9.1), and the two add-ons the manual
says apply "regardless of sport or split" (Part 1).

WHY THIS EXISTS
sport_profiles.py already encodes *why* an exercise transfers to a sport.
This module encodes the manual's own conditioning menus verbatim-in-
structure (not verbatim text — summarized/restructured as data) so the
Program Builder can hand back a concrete "pick one of these" aerobic/lactic
session alongside the lifting days, instead of only ever prescribing
barbell work. Kept separate from program_builder.py because none of this
is split-specific — the same menus apply no matter which of the 6 templates
a person is running.
"""

from typing import Dict, List

# Part 2 — plain-language definitions, surfaced by the API so a UI can show
# a "what is this?" tooltip without hardcoding the copy client-side.
ENERGY_SYSTEM_EXPLAINER: Dict[str, str] = {
    "aerobic": (
        "Steady, lower-intensity work (Zone 2, ~60-75% max heart rate) where the body "
        "uses oxygen to produce energy efficiently — think 25-45 minutes at a pace you "
        "could hold a conversation. Builds the baseline 'engine': more capillary density, "
        "a stronger heart, faster recovery between hard efforts. This is what lets a "
        "fighter recover between rounds or a rugby player recover between sprints."
    ),
    "lactic": (
        "High-intensity work (20 seconds-3 minutes, incomplete rest) hard enough that the "
        "body outruns its oxygen supply and switches to the glycolytic system — the "
        "burning, heavy-limb feeling of a hard sparring round or wrestling scramble. "
        "Trains the body to buffer and clear that burn faster, so output holds up deep "
        "into a match instead of collapsing."
    ),
}

# Part 6 — Aerobic (Zone 2) session menu. Pick 1 per prescribed aerobic
# session/week.
AEROBIC_SESSION_MENU: List[Dict] = [
    {"modality": "Steady run/jog", "duration": "30-45 min", "notes": "Conversational pace; nose-breathing pace is a good check."},
    {"modality": "Cycling / Assault bike", "duration": "35-45 min", "notes": "Easy, steady RPM/watt output."},
    {"modality": "Rowing", "duration": "30-40 min", "notes": "Steady stroke rate ~18-22 spm."},
    {"modality": "Ruck march (weighted walk)", "duration": "45-60 min", "notes": "Great for grapplers, Special Forces prep, rugby forwards."},
    {"modality": "Swimming", "duration": "30-40 min", "notes": "Low-impact option, easy on joints after hard sparring/practice."},
]

# Part 6 — Lactic (anaerobic interval) session menu. Pick 1-2 per week,
# matched to what the sport actually demands (round length, scramble
# duration, repeated-sprint pattern).
LACTIC_SESSION_MENU: List[Dict] = [
    {
        "protocol": "Round-based intervals", "structure": "3 min on / 1 min off x 3-6",
        "best_for": "Bike, bag work, sled push — matches competition round length.",
    },
    {
        "protocol": "Short max-effort intervals", "structure": "20-30s on / 60-90s off x 8-10",
        "best_for": "Sprint, bike sprint, sled sprint — wrestling/judo style.",
    },
    {
        "protocol": "Long lactic intervals", "structure": "60-90s on / 60s off x 6-8",
        "best_for": "Rower, bike, shuttle runs — grinding 'gas tank' work.",
    },
    {
        "protocol": "Repeated sprints", "structure": "10-15 x 30-40m sprint, 20-30s rest",
        "best_for": "Rugby/field-sport repeated-sprint ability.",
    },
    {
        "protocol": "Complex/sandbag circuit", "structure": "45s work / 15s transition x 5 stations, x2-3 rounds",
        "best_for": "Special Forces / general strength-endurance.",
    },
]

WEEKLY_FITTING_NOTE = (
    "Most sports do best with roughly 2-3 aerobic sessions + 1-2 lactic sessions per "
    "week, weighted per the sport's aerobic:lactic ratio. Hard skill practice "
    "(sparring, rolling, live drilling) already provides significant lactic "
    "conditioning — count it, don't just add on top of it."
)

# Part 9.1 — Warm-up protocol run before every lift session (5-8 minutes).
WARMUP_PROTOCOL: List[Dict] = [
    {
        "stage": "General warm-up", "time_or_volume": "3-5 min",
        "description": "Easy bike, row, or jump rope — just enough to raise body temperature and heart rate.",
    },
    {
        "stage": "Dynamic mobility", "time_or_volume": "5-8 reps each",
        "description": "Leg swings, walking lunge with rotation, band pull-aparts, arm circles, hip openers.",
    },
    {
        "stage": "Ramp-up sets for the main lift", "time_or_volume": "2-4 sets",
        "description": "e.g. empty bar x8, ~50% x5, ~70% x3, ~85% x1-2, then begin working sets.",
    },
]
WARMUP_NOTE = (
    "Skip static stretching (long held stretches) right before lifting or explosive "
    "work — save it for after training or on rest days, since it can temporarily "
    "reduce power output."
)

# Part 1 — universal add-ons the manual prescribes "regardless of sport or
# split", since almost every sport on the list involves clinching, gripping,
# or head contact.
UNIVERSAL_ADD_ONS: List[Dict] = [
    {"name": "Neck training", "frequency": "2x/week", "description": "Bridges, harness/manual resistance, all 4 directions."},
    {"name": "Grip / forearm work", "frequency": "2x/week (folded into pulling/carry days)", "description": "Crushing, pinching, wrist flexion/extension."},
]


def conditioning_reference() -> Dict:
    """Everything in this module, bundled for a single API response."""
    return {
        "energy_system_explainer": ENERGY_SYSTEM_EXPLAINER,
        "aerobic_session_menu": AEROBIC_SESSION_MENU,
        "lactic_session_menu": LACTIC_SESSION_MENU,
        "weekly_fitting_note": WEEKLY_FITTING_NOTE,
        "warmup_protocol": WARMUP_PROTOCOL,
        "warmup_note": WARMUP_NOTE,
        "universal_add_ons": UNIVERSAL_ADD_ONS,
    }
