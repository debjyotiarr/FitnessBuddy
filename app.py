import streamlit as st
from db import (
    get_exercises,
    add_exercise,
    start_session,
    log_set,
    get_last_session_sets,
    get_today_sets,
)

st.set_page_config(
    page_title="FitnessBuddy",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── session state defaults ─────────────────────────────────────────────────────
_defaults: dict = {
    "session_id": None,
    "day_type": None,
    "weight": 20.0,
    "reps": 10,
    "rir": 2,
    "last_exercise_id": None,
    "last_sets_cache": [],
    "last_date_cache": None,
    "last_set_logged": None,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── helpers ────────────────────────────────────────────────────────────────────

def _exercise_map(exercises: list[dict]) -> dict[str, int]:
    return {f"{e['name']}  ·  {e['muscle_group']}": e["id"] for e in exercises}


def _load_last_sets(exercise_id: int) -> None:
    sets, date = get_last_session_sets(exercise_id, st.session_state.session_id)
    st.session_state.last_sets_cache = sets
    st.session_state.last_date_cache = date
    if sets:
        st.session_state.weight = float(sets[-1]["weight_kg"])
    st.session_state.last_exercise_id = exercise_id


# ── tab layout ─────────────────────────────────────────────────────────────────

tab_log, tab_exercises = st.tabs(["🏋️ Log", "📋 Exercises"])


# ══════════════════════════════════════════════════════════════════════════════
# LOG TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_log:
    exercises = get_exercises()

    # ── no active session: start screen ───────────────────────────────────────
    if st.session_state.session_id is None:
        st.title("💪 FitnessBuddy")
        day_type = st.selectbox(
            "What are you training today?",
            ["Push", "Pull", "Legs", "Upper", "Lower", "Full Body", "Custom"],
        )
        if st.button("Start Session", type="primary", use_container_width=True):
            st.session_state.session_id = start_session(day_type)
            st.session_state.day_type = day_type
            st.session_state.last_exercise_id = None
            st.session_state.last_sets_cache = []
            st.session_state.last_set_logged = None
            st.rerun()

    # ── active session ────────────────────────────────────────────────────────
    else:
        col_title, col_end = st.columns([4, 1])
        with col_title:
            st.subheader(f"💪 {st.session_state.day_type} Day")
        with col_end:
            if st.button("End ✓", use_container_width=True):
                st.session_state.session_id = None
                st.session_state.last_exercise_id = None
                st.session_state.last_sets_cache = []
                st.session_state.last_set_logged = None
                st.rerun()

        st.divider()

        # ── exercise selector ─────────────────────────────────────────────────
        emap = _exercise_map(exercises)
        labels = list(emap.keys())

        def _on_exercise_change() -> None:
            ex_id = emap.get(st.session_state.exercise_label)
            if ex_id is not None:
                _load_last_sets(ex_id)

        st.selectbox(
            "Exercise",
            labels,
            key="exercise_label",
            on_change=_on_exercise_change,
        )
        current_exercise_id = emap.get(st.session_state.get("exercise_label", labels[0]))

        # Populate on first render / if exercise changed outside the callback
        if current_exercise_id and st.session_state.last_exercise_id != current_exercise_id:
            _load_last_sets(current_exercise_id)

        # ── last session display ──────────────────────────────────────────────
        if st.session_state.last_sets_cache:
            date_label = st.session_state.last_date_cache or "last session"
            lines = "\n\n".join(
                f"Set {s['set_number']}: **{s['weight_kg']} kg × {s['reps']}**"
                + (f"  (RIR {s['rir']})" if s["rir"] is not None else "")
                for s in st.session_state.last_sets_cache
            )
            st.info(f"**Last session — {date_label}**\n\n{lines}")
        else:
            st.caption("No previous session found for this exercise.")

        st.divider()

        # ── weight input with quick-increment buttons ─────────────────────────
        st.write("**Weight (kg)**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("−2.5", use_container_width=True):
                st.session_state.weight = max(0.0, st.session_state.weight - 2.5)
        with c2:
            if st.button("−1.25", use_container_width=True):
                st.session_state.weight = max(0.0, st.session_state.weight - 1.25)
        with c3:
            if st.button("+1.25", use_container_width=True):
                st.session_state.weight += 1.25
        with c4:
            if st.button("+2.5", use_container_width=True):
                st.session_state.weight += 2.5

        st.number_input(
            "Weight",
            min_value=0.0,
            step=0.5,
            key="weight",
            label_visibility="collapsed",
        )
        st.number_input("Reps", min_value=1, max_value=100, step=1, key="reps")
        st.number_input("RIR (reps left in tank)", min_value=0, max_value=10, step=1, key="rir")

        # ── action buttons ────────────────────────────────────────────────────
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Add Set ✚", type="primary", use_container_width=True):
                log_set(
                    st.session_state.session_id,
                    current_exercise_id,
                    st.session_state.weight,
                    st.session_state.reps,
                    st.session_state.rir,
                )
                st.session_state.last_set_logged = {
                    "weight_kg": st.session_state.weight,
                    "reps": st.session_state.reps,
                    "rir": st.session_state.rir,
                }
                st.rerun()

        with btn_col2:
            has_last = st.session_state.last_set_logged is not None
            if st.button(
                "Duplicate ⧉", use_container_width=True, disabled=not has_last
            ):
                last = st.session_state.last_set_logged
                log_set(
                    st.session_state.session_id,
                    current_exercise_id,
                    last["weight_kg"],
                    last["reps"],
                    last["rir"],
                )
                st.rerun()

        st.divider()

        # ── today's running log ───────────────────────────────────────────────
        today = get_today_sets(st.session_state.session_id)
        if today:
            st.subheader("Today's Log")
            # Group preserving the order exercises were first done
            order: list[str] = []
            grouped: dict[str, list] = {}
            for s in today:
                name = s["exercises"]["name"]
                if name not in grouped:
                    order.append(name)
                    grouped[name] = []
                grouped[name].append(s)

            for name in order:
                st.write(f"**{name}**")
                for i, s in enumerate(grouped[name], 1):
                    rir_txt = f"  ·  RIR {s['rir']}" if s["rir"] is not None else ""
                    st.write(f" {i}. {s['weight_kg']} kg × {s['reps']}{rir_txt}")
        else:
            st.info("No sets logged yet — pick an exercise above and hit Add Set.")


# ══════════════════════════════════════════════════════════════════════════════
# EXERCISES TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_exercises:
    st.subheader("Exercise Library")

    exercises_all = get_exercises()
    muscle_groups = sorted(
        {e["muscle_group"] for e in exercises_all if e.get("muscle_group")}
    )
    filter_mg = st.selectbox("Filter", ["All"] + muscle_groups)

    filtered = (
        exercises_all
        if filter_mg == "All"
        else [e for e in exercises_all if e.get("muscle_group") == filter_mg]
    )

    for e in filtered:
        cat = e.get("category", "")
        st.write(f"**{e['name']}** — {e.get('muscle_group', '—')}  ·  *{cat}*")

    st.divider()
    st.subheader("Add Exercise")

    with st.form("add_exercise_form", clear_on_submit=True):
        new_name = st.text_input("Name")
        new_muscle = st.selectbox(
            "Muscle group",
            ["Back", "Chest", "Shoulders", "Arms", "Legs", "Core", "Other"],
        )
        new_cat = st.selectbox("Category", ["compound", "isolation"])
        submitted = st.form_submit_button("Add Exercise", use_container_width=True)

    if submitted:
        if new_name.strip():
            add_exercise(new_name.strip(), new_muscle, new_cat)
            st.success(f"Added '{new_name.strip()}'")
            st.rerun()
        else:
            st.warning("Please enter a name.")
