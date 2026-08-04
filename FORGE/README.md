# FORGE

A knowledge-graph-driven exercise prescription engine: a FastAPI backend that scores
and sequences exercises by sport, injury history, equipment, and readiness, with a
standalone HTML/CSS/JS web frontend on top.

## Project layout (Phase 1 restructure)

```
FORGE/
├── backend/
│   ├── core/
│   │   └── config.py          # Pydantic Settings — every path/host/port lives here now
│   ├── services/
│   │   ├── injury_taxonomy.py
│   │   ├── knowledge_graph.py
│   │   ├── programming_role.py
│   │   ├── sport_profiles.py
│   │   └── exercise_metadata.py
│   └── main.py                 # FastAPI app + ProgressionEngine
├── frontend/
│   └── web/
│       └── index.html          # Web UI (no build step, no Python deps)
├── data/
│   ├── exercises.json
│   └── *_backup.json
├── scripts/
│   ├── enrich_exercises.py     # metadata migration, re-runnable
│   └── generate_new_exercises.py
├── tests/
├── docs/
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # optional — defaults work out of the box
```

## Running

```bash
# backend
python -m backend.main
# or: uvicorn backend.main:app --reload
```

Then open the frontend — see "New Web UI" below.

## What changed from the original single-folder version

- All modules moved under `backend/services/` and `backend/main.py`; imports updated
  accordingly (`from backend.services.knowledge_graph import ...` etc).
- Every previously hardcoded value — the `exercises.json` path, API host/port, CORS
  origins, the frontend `API_BASE` URL, the metadata cache TTL — now comes from
  `backend/core/config.py` (`pydantic-settings`), overridable via `.env`.
- `scripts/` now resolve paths through the same config instead of assuming the
  current working directory is the project root.
- No behavior, endpoints, or business logic changed — this is a structural/config
  pass only (Phases 1 and 3 of the requested roadmap).

## Combat Sports & Rugby S&C Manual alignment (v5.7 pass — Part 7 / 7.7 gap closed)

The v5.6 pass above ported Parts 1, 2, 5, 6, and 9.1/9.3 of the manual but
explicitly left Part 7 (the Olympic-lift/jump/pull/kettlebell/landmine/GHD/
belt-squat variation library) and Part 7.7 (the injury-substitution table)
unported. Auditing `data/exercises.json` against Part 7 line-by-line found
that almost everything the manual names already existed under some name
(Hang Power Clean → "Barbell Hang Power Clean", Landmine Press/Row/Squat,
GHD Back/Hip Extension, Nordic Hamstring Curl, the Belt Squat family,
Kettlebell Swing/Clean & Press/Turkish Get-Up, box/broad/lateral/depth
jumps, Seal Row, Pendlay Row, Weighted Pull-Up/Dip, etc.) — so the README's
"not yet ported" note was itself out of date on that point. What was
genuinely missing:

- **5 new exercises** (`scripts/generate_batch5_manual_part7_gaps.py`,
  442 → 447 in `data/exercises.json`): **Band-Assisted Pull-Up** and
  **Band-Assisted Dip** (Part 7.3's named regression step, previously only
  Negative Pull-Up existed), **Landmine Anti-Rotation Press (Half-Kneeling)**
  (Part 7.5's core/prehab variant — Landmine Press/Rotation/Row/Squat existed
  but not this one), **Neutral-Grip Dumbbell Press** (Part 7.7's named
  shoulder-friendly bench/OHP substitute — "Neutral Grip Pull-Up" existed but
  no neutral-grip *press*), and **Fat-Grip Row** (Part 7.7's named
  elbow-friendly substitute for curls/strict pull-ups). Authored with the
  same hand-tagged base fields as batches 2-4, then run through the existing
  `enrich_exercise()` pipeline for the v4.0+ movement-analysis/athletic-
  quality fields; verified zero dangling progression/regression/alternative
  references and DAG acyclicity held after the merge (447 exercises, 447
  unique ids).
- **New `injury_taxonomy.PART7_SUBSTITUTION_TABLE`**: the manual's Part 7.7
  "issue → typical culprit → safer substitute(s)" table as real data, keyed
  to the same 8-tag joint vocabulary as the rest of the injury taxonomy
  (Lower Back, Shoulder, Knee, Wrist, Elbow, Hip), each substitute
  cross-checked against `exercises.json` by name. `part7_substitution_guidance(joint=None)`
  returns the table (optionally filtered to one joint);
  `part7_recommended_swap(exercise, all_exercises, joint)` matches a specific
  excluded exercise against the table's `typical_culprit` list and resolves
  its substitutes to real `{id, name}` pairs, so a Back Squat exclusion
  doesn't spuriously attach to every squat variant. `PART7_DISCLAIMER`
  carries the manual's own caveat verbatim-in-meaning ("persistent pain is a
  signal to see a professional, not just swap exercises").
- **`generate-workout`/`generate-program` excluded-exercise entries** now
  carry a `manual_guidance` field (`backend/main.py`) alongside the existing
  generic `alternatives` list, whenever the excluded exercise/joint pair
  matches a Part 7.7 row — e.g. excluding Barbell Back Squat for a Lower Back
  injury now also surfaces the manual's own Belt Squat / Trap Bar Deadlift /
  Single-Leg Hip Thrust / GHD Hip Extension guidance with its rationale, not
  just the engine's generic pattern-matched swap.
- **New `GET /api/v1/injury-substitutions`** endpoint (optional `?joint=`
  filter) returns the full Part 7.7 table on its own, each substitute
  resolved to a real exercise id/name, plus the manual's disclaimer — for a
  UI that wants to show this reference table independent of any specific
  excluded exercise.
- Verified end-to-end against the live database (not just unit-tested in
  isolation): Barbell Back Squat/Lower Back → Belt Squat, Trap Bar Deadlift,
  Single-Leg Hip Thrust, GHD Hip Extension; Flat Bench Press or Barbell
  Overhead Press/Shoulder → Landmine Press, Floor Press, Neutral-Grip
  Dumbbell Press; EZ Bar Curl or Weighted Pull-Up/Elbow → Neutral Grip
  Pull-Up, Fat-Grip Row; Speed Deadlift or Romanian Deadlift/Hip → Nordic
  Hamstring Curl, Dumbbell Goblet Squat, Belt Squat — all substitute names
  resolve to real ids, none silently dropped.

## Combat Sports & Rugby S&C Manual alignment (v5.6 pass)

Brings the Program Builder in line with the uploaded *Combat Sports & Rugby
Strength & Conditioning Manual* (6 splits, 11-sport aerobic:lactic guidance,
Part 9.3 periodization table, Part 6 conditioning menus).

- **New `backend/services/conditioning_protocols.py`**: the manual's
  sport-agnostic reference material as data - the aerobic-vs-lactic
  explainer (Part 2), the pick-one-of-these aerobic and lactic session
  menus (Part 6), the pre-lift warm-up protocol (Part 9.1), and the two
  add-ons the manual says apply "regardless of sport or split" (neck
  training, grip/forearm work - Part 1). Exposed via a new
  `GET /api/v1/conditioning-protocols` endpoint.
- **New `sport_profiles.SPORT_CONDITIONING_PROFILES`**: one row per sport
  the manual covers (MMA, BJJ, Wrestling, Judo, Boxing, Kickboxing, Muay
  Thai, Sanda, Sambo, Special Forces, Rugby) carrying its aerobic:lactic
  ratio, gym emphasis, weekly conditioning notes, and "time-saver" tip,
  straight out of Part 5's per-sport subsections. Surfaced on
  `GET /api/v1/sports/{sport}` (`conditioning_profile`) and on every
  `POST /api/v1/generate-program` response (`conditioning_guidance` -
  includes suggested aerobic/lactic sessions-per-week and the Part 6
  menus, weighted by that sport's ratio).
- **`SPLIT_TEMPLATES` now matches the manual's exact 6 splits**: Full Body
  gained 1-day support (`supported_days_per_week` `[2,3,4]` -> `[1,2,3,4]`,
  the manual's fight-camp maintenance template) and Upper/Lower gained
  2-day support (`[4,6]` -> `[2,4,6]`, the manual's time-crunched in-season
  option) - previously neither the 1-Day Full Body nor 2-Day Upper/Lower
  templates the manual specifies could actually be generated.
- **`SPORT_SPLIT_GUIDANCE` re-derived from the manual's Part 5
  Quick-Reference table** instead of generic S&C-writeup guidance: MMA,
  Kickboxing, Muay Thai, and Sanda now default to 3-Day Full Body (were
  4-Day Upper/Lower); Boxing now defaults to 2-Day Upper/Lower (was 4-Day
  Upper/Lower). Wrestling/Sambo/BJJ/Judo/Rugby/Special Forces already
  matched the manual and are unchanged; each sport's rationale text now
  also states its aerobic:lactic ratio.
- **New `ProgramRequest.training_phase`** (optional, `None` by default -
  every existing caller is unaffected) plus `program_builder.PHASE_GUIDANCE`,
  implementing Part 9.3's periodization table verbatim: Off-Season (4-Day
  U/L or 3-Day PPL, full volume), Pre-Season (3-Day Full Body, 90% volume),
  In-Season / Fight Camp (2-Day U/L or 1-Day Full Body, volume cut roughly
  in half), Fight Week (Full Body, minimal - 25% volume), Post-Competition
  (Full Body, 60% volume, easy). Setting `training_phase` overrides the
  days/goal/sport split heuristic with the phase's own candidate splits
  (still constrained to whatever `days_per_week` the caller actually asked
  for) and scales every prescription's set count via the new
  `_apply_phase_volume_scaling`. New `GET /api/v1/training-phases` lists
  the table; `GET /api/v1/metadata` now also reports `training_phases`.
  `generate_program()`'s response gained a `training_phase` block
  (phase, typical duration, lifting/conditioning focus, whether the split
  actually landed on that phase's own recommendation).
- **Web UI** (`frontend/web/index.html`): Program Builder form gained a
  "Training Phase (optional)" selector next to Preferred Split, and the
  program results view now surfaces the chosen phase's focus plus the
  sport's aerobic:lactic conditioning guidance and time-saver tip.
- Part 7/7.7 alignment (exercise-variation library, injury-substitution
  table) was completed in the v5.7 pass above.

## Bug fixes & data update (v5.5 pass — nonsensical "% 1RM" on bodyweight moves, redundant near-duplicate picks)

- **73 bodyweight-only exercises were prescribed a fabricated "% of 1RM"**:
  `_prescribe_volume` (`main.py`) treated any exercise in the six "loaded
  strength" categories (Horizontal/Vertical Push/Pull, Squat, Hinge) as
  barbell-style work, always producing a `reps @ X% 1RM` prescription -
  even for Push-Ups, Pull-Ups, Dips, Pistol Squats, Ring work, and
  calisthenics static holds (Front Lever, Planche, Passive Dead Hang, Wall
  Sit, Human Flag...) where no external load, and therefore no 1RM, exists
  at all. Reported concretely: "Negative Pull-Up: 3x6 reps @ 66% 1RM" and
  "Passive Dead Hang: 3x8 reps @ 60% 1RM" (a static hold prescribed in reps
  on top of the fake load). Fixed by gating the loaded-strength branch on
  equipment: Bodyweight/Pull-up Bar/Rings/Suspension Trainer/Parallel Bars
  now route to a genuine hold-time prescription (if `movement_pattern` is
  actually `"Isometric"`) or a reps-only bodyweight prescription (new
  `"strength_bodyweight"` type) - no invented load percentage either way.
  Genuinely loadable equipment (Barbell, Dumbbell, Kettlebell, machines,
  bands, etc.) is unaffected. `program_builder.py`'s week-to-week
  progression and power/hypertrophy bias were extended to handle the new
  type too (bodyweight work now progresses by adding reps across a
  mesocycle instead of silently getting no progression at all), and the
  web UI got a matching renderer ("reps (bodyweight)" instead of a fake
  "% 1RM" or falling through to a mislabeled "(technical)" line).
  "Passive Dead Hang" was also recategorized `Vertical Pull` → `Grip` so
  its session-role placement (Core/Grip-style accessory, not a loaded
  pulling movement) matches what it actually is.
- **Sessions could stack 3+ near-duplicate exercises while ignoring other
  movement patterns entirely**: once `_select_role_balanced`'s one-per-role
  pass filled the 7 role slots, any additional requested slots were filled
  purely by raw score across every leftover exercise, with no check for
  whether that exercise's movement pattern was already well represented.
  Reported concretely: a 7-exercise session came back with three separate
  explosive kettlebell drills (Windmill, Flip, Tactical Juggle - all "Full
  Body"/ballistic) while carrying zero squat, hinge, or horizontal-push
  work. Fixed with `_BACKFILL_MAX_PER_CATEGORY = 2`: the backfill pass now
  prefers candidates whose `category` isn't already stacked twice, only
  falling back to a 3rd+ repeat of the same category if literally nothing
  else qualifies for the remaining slots.

## Bug fixes & data update (v5.4 pass — wrong exercises per discipline, forced Special Forces default, beginner programming)

- **Sessions could force in a badly-mismatched exercise just to fill a role
  slot**: `_select_role_balanced` (`main.py`) picks one exercise per
  programming role (Primer, Skill, Power, Primary Strength, Accessory,
  Core, Conditioning) to keep a session looking like something a coach
  would actually run. It used to force *something* into every role as long
  as anything at all qualified - even the single worst-scoring exercise in
  the whole session. Reproduced concretely: a bodyweight-only Judo session
  had no grappling-relevant Conditioning finisher available, so the engine
  forced in "Shadow Boxing Rounds" (a Boxing drill, blended score ~25/100
  for Judo) ahead of exercises the same session had already picked at
  55-65+. Fixed with a quality floor (`_ROLE_FILL_ABS_FLOOR` /
  `_ROLE_FILL_RELATIVE_FLOOR`): a role only gets force-filled if its best
  candidate is actually competitive with the rest of the session; otherwise
  that slot goes to the normal score-ranked backfill instead, which still
  fills every requested slot, just with the next-genuinely-best exercise
  for this person's sport/equipment/level rather than the weakest thing
  that happened to be the lone option in one role bucket.
- **Two exercises were mistagged in a way that fed the bug above**: "Shadow
  Boxing Rounds" and "Heavy Bag Power Rounds" are boxing-specific striking
  skill drills - their own sibling exercises ("Heavy Bag Combinations",
  "Heavy Bag Knee Strikes", "Clinch Knee Drives") are correctly categorized
  `Sport Specific`, but these two were left under the generic `Conditioning`
  category. That meant they competed for every sport's generic Conditioning
  slot instead of being confined to striking sports, where they belong.
  Recategorized both to `Sport Specific` in `data/exercises.json` (now
  `v5.4.0`).
- **Discipline picker silently pre-selected "Special Forces"**: the setup
  wizard (`frontend/web/index.html`) auto-clicked the Special Forces card
  on load, before a person had looked at the discipline grid - easy to
  miss, and it produced a program for a sport nobody chose. The same bias
  existed in the Program Builder's own sport dropdown and in the Streamlit
  sidebar (`frontend/app.py`). All three now require an explicit choice
  (or fall back to the alphabetically-first sport for a dropdown that must
  show *something* selected) instead of defaulting to one specific
  discipline.
- **Beginners could get routed into body-part specialization splits**:
  `recommend_split` picked a split from days/week + goal only - a Beginner
  asking for 5-6 days/week (a perfectly normal amount of available time)
  landed on PHAT or an Arnold Split, the same as an Advanced lifter with
  the same schedule. That's backwards: a true beginner's limiting factor is
  neural adaptation/technique on compound lifts, not per-muscle volume -
  the entire premise behind the classic novice linear-progression programs
  this app already cites (Starting Strength, StrongLifts 5x5, GreySkull
  LP) is full-body work at high per-lift frequency, not specialization.
  Added `EXPERIENCE_SPLIT_ALLOWLIST` + `_apply_experience_ceiling`:
  Beginner is capped to Full Body / Upper-Lower, Novice adds Push/Pull/Legs;
  Intermediate and above are unrestricted. Applied as a ceiling on top of
  the existing days/goal/sport heuristic, so it only changes the result
  when the heuristic would have picked something above that person's
  stage. `generate-program`'s response now carries `experience_capped` /
  `experience_rationale` on the `split` object (same pattern as the
  existing `recommended_for_sport` / `sport_rationale`), and the web UI
  surfaces that rationale next to the split description when it applies.



- **Beginner/Advanced/Elite users all got the same exercise list**:
  `experience_level` on a `WorkoutRequest` only ever fed a ceiling check
  (`level_ok = ex_level_rank <= user_level_rank + LEVEL_STRETCH`) that
  excluded exercises *too far above* the user's level - it never boosted
  exercises that actually matched the user's level, so ranking/selection ran
  purely on `sport_priority_score`. In practice an Elite lifter and a
  Beginner asking for the same sport/equipment got an identical ranked
  list, because a Beginner-tier movement with a high sport-transfer score
  (e.g. a Push-Up scoring 85 for Boxing) would consistently out-rank
  Advanced/Elite-tier lifts with a merely-good sport score. Added
  `level_fit_multiplier` in `main.py`: discounts an exercise's score based
  on how many rungs its `experience_level` sits from the user's stated
  level, asymmetrically (15%/rung below the user's level, 5%/rung above -
  the existing ceiling already keeps "above" in check, so it only needs a
  light nudge; nothing previously stopped a trivially-easy exercise from
  dominating on sport score alone, so "below" needed the stronger
  discount). Applied alongside the existing sport/movement-emphasis
  multipliers everywhere `sport_priority_score` is computed, so it flows
  through unchanged into every sort/selection step downstream
  (`_select_role_balanced`, `_pick_with_variety`, the final response sort).
  Each prescribed exercise now also carries a plain-language
  `experience_level_fit` field (e.g. "Matched to your level", "A stretch
  above your level", "Well below your level") so the reasoning is visible
  in the API response, not just implied by ranking order.

## Bug fixes & data update (v5.2 pass — sport-specific recommendation logic)

- **Same exercises every time / every week**: `_select_role_balanced` always
  returned the single highest-scoring exercise per role, and
  `program_builder.generate_program` called the session engine with
  identical filters for every week of a mesocycle - so a 4-week program's
  "Push Day" was mechanically the same exercise list in week 4 as week 1.
  Fixed with `_pick_with_variety`: rotates among near-tied top candidates
  (within 12% of the top score - a coach's "interchangeable" band) using a
  seeded RNG, and the program builder now tracks per-day-label exercise
  history across weeks and feeds it back as `exclude_exercise_ids` with a
  rotating `variety_seed`. New optional `WorkoutRequest` fields:
  `exclude_exercise_ids`, `variety_seed` (both backward compatible - default
  behavior for existing callers is `variety_seed=0`, no exclusions).
- **Sport transfer ignored movement pattern (push vs. pull)**:
  `blended_transfer_score` only measured overlap against generic athletic-
  quality tags (Power, Grip Strength, etc.), which can't distinguish a press
  from a pull - a Boxing session and a Judo session could rank the same row
  identically. Added `SPORT_MOVEMENT_EMPHASIS` in `sport_profiles.py`: a
  per-sport multiplier on the exercise's own `category`/`movement_pattern`
  (Boxing/Muay Thai/Kickboxing/Sanda bias toward pressing + rotational
  output; Judo/Wrestling/Sambo/BJJ/Rock Climbing bias toward pulling +
  grip). Applied on top of the existing quality-overlap score in
  `generate_session`. New `GET /api/v1/sports/{sport}` exposes both signals
  directly (quality profile + movement emphasis + which patterns are
  prioritized/de-emphasized) so the reasoning is inspectable, not just
  implied by ranking order.
- **Injury alternatives ignored the person's own equipment**:
  `find_alternatives` ranked substitutes by movement-pattern match and
  difficulty only - it could suggest a Belt Squat swap to someone who
  doesn't have one while ranking it below a Sled drag they also don't have.
  Added an `equipment_tier` ranking (owned dedicated equipment > bodyweight
  fallback > equipment not owned) so, e.g., a lower-back-injury Farmer's
  Walk exclusion now surfaces an owned Belt Squat first instead of an
  unreachable Sled. `find_alternatives` takes an optional `user_equipment`
  param (backward compatible - omitting it behaves exactly as before).
  Excluded-exercise alternatives in the API response now also carry
  `equipment` and `equipment_available` fields.
- **Equipment browser was a flat alphabetical checkbox list**: added
  `build_equipment_catalog()` (`exercise_metadata.py`) grouping the ~65
  equipment strings into real sections (Free Weights, Machines, Strongman,
  Racks & Benches, Conditioning, Grip & Accessory, Combat Sport, Bodyweight)
  with an exercise count and the movement categories each item actually
  unlocks - e.g. Kettlebell now visibly covers push/pull/hinge/squat/carry/
  core, not just swings. New `GET /api/v1/equipment` endpoint; the web UI
  (`frontend/web/index.html`) now renders both equipment checklists (wizard
  step 3 and the Program Builder form) as these grouped sections with
  per-item exercise-count badges instead of one flat list, falling back to
  the old flat list if an older backend without this endpoint is in use.

## Bug fixes & data update (v5.1 pass)

- **Joint coverage gap in the knowledge graph**: `JOINT_STABILITY_TAG` (the
  joint -> athletic-quality-tag mapping used to build `/api/v1/knowledge-graph/{id}`'s
  joint nodes and to decide rehab candidacy) only covered 5 of the 8 joints
  `joint_stress` actually uses across exercises.json - Wrist, Elbow, and Lower
  Back had no stability tag at all. In practice this meant: (1) the exercise
  detail modal's "joints stressed" list silently dropped Wrist/Elbow/Lower
  Back for any exercise that stressed them (e.g. a push-up's Wrist and Elbow
  stress vanished, only Shoulder showed), and (2) no exercise could ever be
  flagged as a rehab pick for an injury on those three joints, no matter how
  appropriate it was. Fixed by adding `Wrist Stability`, `Elbow Stability`,
  and `Lower Back Stability` to `ATHLETIC_QUALITY_TAGS` and
  `JOINT_STABILITY_TAG` in `exercise_metadata.py`, making that dict the single
  source of truth (`knowledge_graph.py` previously kept its own hand-copied
  duplicate, which is exactly how the two drifted out of sync - it now
  imports the shared one instead), and re-running the enrichment pipeline
  over every exercise to backfill the 3 new tags.
- **`data/*_backup.json` files / `.gitignore`**: the previous changelog entry
  below claimed these were already done; they weren't actually in this
  archive. Both are done now - backups live in `data/backups/` (path
  configurable via the new `settings.BACKUP_DIR`), and `.gitignore` excludes
  that directory plus the usual Python/editor/env clutter.
- **New exercises**: added 34 exercises (227 -> 261) targeting the
  categories/equipment that were thin - Dumbbell (3 -> 17), Jump (2 -> 8),
  Power (1 -> 7), Grip (2 -> 6) - plus a few lower-difficulty Conditioning
  entry points. Generated through the same `enrich_exercise()` pipeline as
  the rest of the database, so derived fields follow the same rules; DAG
  acyclicity and zero dangling progression/regression/alternative references
  were verified after the merge. `data/exercises.json` is now `v5.1.1`.

## Bug fixes (previous pass)

- **CORS/credentials mismatch**: `allow_origins=["*"]` combined with
  `allow_credentials=True` is invalid per the CORS spec (browsers reject it).
  The app has no cookies/auth to protect, so `allow_credentials` is now `False`
  — `"*"` stays, since it's what lets `frontend/web/index.html` work when opened
  directly as a `file://` page (see `config.py`'s comment on `CORS_ORIGINS`).
- **`API_RELOAD` default**: was `True`, meaning autoreload was silently on for
  anyone running `python -m backend.main` without an explicit `.env`. Now
  defaults `False`; set `API_RELOAD=true` in `.env` for local dev.
- **Unhandled-exception detail leak**: `/api/v1/generate-workout`'s 500 handler
  used to return the raw exception message to the client. It's now logged
  server-side and only returned to the client when `settings.DEBUG` is on.
- **`custom_progressions.custom_name`** is now capped at 120 characters
  (`Field(max_length=120)`) — defense in depth, since this string round-trips
  into API responses the frontend renders (the frontend already HTML-escapes
  every exercise name it displays, so this closes the gap for other consumers
  of the API, not a live XSS in the bundled UI).
- **Repo hygiene**: removed committed `__pycache__/` directories, moved the two
  legacy `data/*_backup.json` files into `data/backups/`, and added `.gitignore`.

## New: injury filter/search browser (`frontend/web/index.html`)

The flat "pick from ~380 injury strings" checklist is replaced with a browsable,
searchable structure that mirrors how `backend/services/injury_taxonomy.py` is
actually organized:

- **Sections** — one per joint (Knee, Shoulder, Wrist, Elbow, Hip, Neck, Lower
  Back, Ankle), collapsible, each showing how many conditions and how many are
  currently selected.
- **Subsections** — named conditions within a joint (e.g. "ACL/Ligament Tear",
  "Meniscus Tear", "Patellar Tendinopathy").
- **Grades** — clickable chips for each severity variant of a condition (Grade
  I/II/III where the data has grades; Mild/Moderate/Severe otherwise), color-cued
  by severity.
- **Search** — filters live across joint, condition, tissue, region, and grade
  text; matching sections auto-expand and matches are highlighted.

This is generated at request time from `INJURY_TAXONOMY` itself via
`grouped_injury_taxonomy()` (new in `injury_taxonomy.py`), exposed both inline
in `/api/v1/metadata` (`injuries_grouped`) and as its own `/api/v1/injuries/grouped`
endpoint — so, same principle as `all_injuries` before it, this can never drift
out of sync with the taxonomy data. The frontend falls back to the old flat
list automatically if it's ever pointed at an older backend without this field.

## Roadmap status

This restructure covers **Phase 1 (project structure)** and **Phase 3
(configuration)** from the full production-readiness plan. The remaining phases
(API-route splitting, SQLite persistence layer, scored recommendation engine,
user profiles, adaptive programming, caching, structured logging, custom
exceptions, expanded API metadata, further web UI polish, test suite, and the
security/AI-extensibility groundwork) are each substantial pieces of work in
their own right and are best tackled one or two phases at a time in follow-up
passes, so each can be verified before the next one builds on it — see
`docs/ROADMAP.md`.

## Web UI (`frontend/web/index.html`)

A standalone, dependency-free HTML/CSS/JS frontend — same FastAPI backend, no new
endpoints, no Python frontend deps at all (the old Streamlit UI has been removed;
this is the only frontend now).

**Run it:**
1. Start the backend: `python -m backend.main` (serves on `http://127.0.0.1:8000`)
2. Open `frontend/web/index.html` directly in your browser (double-click it), or serve it:
   `python -m http.server 8080 --directory frontend/web` then visit `http://localhost:8080`

If your backend runs somewhere other than `http://127.0.0.1:8000`, open the page with
`?api=http://your-host:port` appended to the URL.

### v2 UI update — wizard flow, exercise detail modal, logging, history & calendar

`frontend/web/index.html` now also includes:
- A 5-step guided wizard (discipline → readiness → equipment/injuries → biometrics → review) instead of one long form, with a progress-dot bar.
- Click any exercise name in a compiled session to open a detail modal wired to the real `/api/v1/knowledge-graph/{id}` endpoint — progressions, regressions, equipment substitutes, joints stressed, rehab candidacy, and full sport-transfer breakdown.
- Inline set logging (weight × reps) per exercise, with automatic PR detection against everything you've logged before (stored in the browser's local storage, per-machine — nothing leaves your device and nothing touches the backend).
- "Finish & Save Session" writes the compiled session + your logged sets to a **History** tab (expandable list, PR counts, delete per session).
- A **Calendar** tab marking days you trained (green) or deloaded (blue); click a day to see what was prescribed.

None of this needed new backend endpoints — history/calendar/logging are pure client-side (localStorage), and the exercise modal uses an endpoint your backend already exposed but the old UI never called.
