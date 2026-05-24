import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def _client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


@st.cache_data(ttl=300)
def get_exercises() -> list[dict]:
    return _client().table("exercises").select("*").order("name").execute().data


def add_exercise(name: str, muscle_group: str, category: str) -> None:
    _client().table("exercises").insert(
        {"name": name, "muscle_group": muscle_group, "category": category}
    ).execute()
    get_exercises.clear()


def start_session(day_type: str) -> int:
    result = _client().table("sessions").insert({"day_type": day_type}).execute()
    return result.data[0]["id"]


def log_set(
    session_id: int,
    exercise_id: int,
    weight_kg: float,
    reps: int,
    rir: int,
    unit: str = "kg",
) -> None:
    count = (
        _client()
        .table("sets")
        .select("id", count="exact")
        .eq("session_id", session_id)
        .eq("exercise_id", exercise_id)
        .execute()
        .count
        or 0
    )
    _client().table("sets").insert(
        {
            "session_id": session_id,
            "exercise_id": exercise_id,
            "set_number": count + 1,
            "weight_kg": weight_kg,
            "reps": reps,
            "rir": rir,
            "unit": unit,
        }
    ).execute()


def save_session_rating(session_id: int, rating: float) -> None:
    _client().table("sessions").update({"rating": rating}).eq("id", session_id).execute()


def get_last_session_sets(
    exercise_id: int, current_session_id: int | None = None
) -> tuple[list[dict], str | None]:
    """Returns (sets, date_string) for the most recent *other* session containing this exercise."""
    query = (
        _client()
        .table("sets")
        .select("session_id, logged_at")
        .eq("exercise_id", exercise_id)
    )
    if current_session_id is not None:
        query = query.neq("session_id", current_session_id)
    recent = query.order("logged_at", desc=True).limit(1).execute().data

    if not recent:
        return [], None

    last_session_id = recent[0]["session_id"]
    sets = (
        _client()
        .table("sets")
        .select("*, sessions(date)")
        .eq("session_id", last_session_id)
        .eq("exercise_id", exercise_id)
        .order("set_number")
        .execute()
        .data
    )
    date_str = sets[0]["sessions"]["date"] if sets else None
    return sets, date_str


def get_today_sets(session_id: int) -> list[dict]:
    return (
        _client()
        .table("sets")
        .select("*, exercises(name, muscle_group, category, sfr_rating)")
        .eq("session_id", session_id)
        .order("logged_at")
        .execute()
        .data
    )


def get_last_same_day_session(
    day_type: str, current_session_id: int | None = None
) -> tuple[dict | None, list[dict]]:
    """Returns (session_row, sets_with_exercise_names) for the most recent session of the same day type."""
    query = _client().table("sessions").select("*").eq("day_type", day_type)
    if current_session_id is not None:
        query = query.neq("id", current_session_id)
    sessions = query.order("date", desc=True).limit(1).execute().data
    if not sessions:
        return None, []
    session = sessions[0]
    sets = (
        _client()
        .table("sets")
        .select("*, exercises(name, muscle_group)")
        .eq("session_id", session["id"])
        .order("logged_at")
        .execute()
        .data
    )
    return session, sets


def get_recent_sessions(limit: int = 20) -> list[dict]:
    return (
        _client()
        .table("sessions")
        .select("*, sets(id)")
        .order("date", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def get_session_detail(session_id: int) -> list[dict]:
    return (
        _client()
        .table("sets")
        .select("*, exercises(name, muscle_group, category, sfr_rating)")
        .eq("session_id", session_id)
        .order("logged_at")
        .execute()
        .data
    )


# ── routines ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_routines() -> list[dict]:
    return _client().table("routines").select("*").order("name").execute().data


def get_routine_detail(routine_id: int) -> list[dict]:
    """Returns exercises for a routine with names, ordered by order_index."""
    return (
        _client()
        .table("routine_exercises")
        .select("*, exercises(name, muscle_group)")
        .eq("routine_id", routine_id)
        .order("order_index")
        .execute()
        .data
    )


def create_routine(name: str, day_type: str | None, exercise_ids: list[int]) -> None:
    result = _client().table("routines").insert(
        {"name": name, "day_type": day_type or None}
    ).execute()
    routine_id = result.data[0]["id"]
    if exercise_ids:
        _client().table("routine_exercises").insert([
            {"routine_id": routine_id, "exercise_id": eid, "order_index": i}
            for i, eid in enumerate(exercise_ids)
        ]).execute()
    get_routines.clear()


def delete_routine(routine_id: int) -> None:
    _client().table("routines").delete().eq("id", routine_id).execute()
    get_routines.clear()


# ── analytics ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def get_all_sets_for_analytics() -> list[dict]:
    """Returns every set with nested exercise + session data for analytics processing."""
    return (
        _client()
        .table("sets")
        .select("*, exercises(name, muscle_group, category, sfr_rating), sessions(date, day_type)")
        .order("logged_at")
        .execute()
        .data
    )


def update_exercise_sfr(exercise_id: int, sfr_rating: float) -> None:
    _client().table("exercises").update(
        {"sfr_rating": sfr_rating}
    ).eq("id", exercise_id).execute()
    get_exercises.clear()
    get_all_sets_for_analytics.clear()


# ── bodyweight ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def get_bodyweight_history() -> list[dict]:
    return (
        _client()
        .table("bodyweight")
        .select("*")
        .order("date")
        .execute()
        .data
    )


def log_bodyweight(weight_kg: float, date_str: str | None = None) -> None:
    row: dict = {"weight_kg": weight_kg}
    if date_str:
        row["date"] = date_str
    _client().table("bodyweight").upsert(row, on_conflict="date").execute()
    get_bodyweight_history.clear()
