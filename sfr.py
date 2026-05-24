"""
Stimulus / Fatigue scoring.

Per-set stimulus and fatigue are computed from data already tracked:
  - weight_kg, reps, RIR          (logged per set)
  - exercise category              (compound → more fatigue; isolation → targeted stimulus)
  - muscle group size              (Legs/Back cost more systemically than Arms/Core)
  - sfr_rating (1–5, default 3)   (per-exercise override; e.g. deadlifts are notoriously low-SFR)

SFR (stimulus-to-fatigue ratio) = total_stimulus / total_fatigue
  > 1.1  → productive session (stimulus well exceeds recovery cost)
  0.85–1.1 → balanced
  < 0.85 → high fatigue relative to stimulus (consider deload)

Absolute stimulus / fatigue numbers are not biologically meaningful on their own;
they are useful as relative comparisons across sessions.
"""

_MUSCLE_FATIGUE: dict[str, float] = {
    "Legs":      1.8,
    "Back":      1.5,
    "Chest":     1.2,
    "Shoulders": 1.1,
    "Arms":      0.8,
    "Core":      0.7,
}
_DEFAULT_MUSCLE_FATIGUE = 1.0


def _ptf(rir: int | float | None) -> float:
    """Proximity to failure.  RIR 0 → 2.0,  RIR 2 → 0.40,  RIR 5 → 0.18."""
    r = float(rir) if rir is not None else 2.0
    return 1.0 / (r + 0.5)


def set_stimulus(
    weight_kg: float,
    reps: int,
    rir: int | None,
    category: str | None,
    sfr_rating: float = 3.0,
) -> float:
    isolation_bonus = 1.2 if category == "isolation" else 1.0
    sfr_mult = sfr_rating / 3.0       # rating 3 = no adjustment; 5 = ×1.67; 1 = ×0.33
    return weight_kg * reps * _ptf(rir) * isolation_bonus * sfr_mult


def set_fatigue(
    weight_kg: float,
    reps: int,
    rir: int | None,
    muscle_group: str | None,
    category: str | None,
) -> float:
    mw = _MUSCLE_FATIGUE.get(muscle_group or "", _DEFAULT_MUSCLE_FATIGUE)
    cp = 1.5 if category == "compound" else 0.9
    return weight_kg * reps * _ptf(rir) * mw * cp


def sfr_color(sfr: float) -> str:
    """Returns a hex colour for the SFR value."""
    if sfr >= 1.1:
        return "#16a34a"   # green
    if sfr >= 0.85:
        return "#f59e0b"   # amber
    return "#dc2626"       # red


def score_sets(sets: list[dict]) -> tuple[float, float, float]:
    """
    Compute (stimulus, fatigue, sfr) for a list of set rows.

    Each row is expected to have:
      weight_kg, reps, rir, unit
      exercises: { muscle_group, category, sfr_rating }
    """
    total_s = total_f = 0.0
    for s in sets:
        ex    = s.get("exercises") or {}
        w_raw = float(s.get("weight_kg") or 0)
        unit  = s.get("unit", "kg")
        w_kg  = w_raw * 0.453592 if unit == "lbs" else w_raw
        r     = int(s.get("reps") or 0)
        rir   = s.get("rir")
        cat   = ex.get("category")
        mg    = ex.get("muscle_group")
        sfr_r = float(ex.get("sfr_rating") or 3.0)
        total_s += set_stimulus(w_kg, r, rir, cat, sfr_r)
        total_f += set_fatigue(w_kg, r, rir, mg, cat)
    ratio = total_s / total_f if total_f > 0 else 0.0
    return round(total_s, 1), round(total_f, 1), round(ratio, 2)
