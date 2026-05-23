import datetime
import streamlit as st
from db import (
    get_exercises,
    add_exercise,
    start_session,
    log_set,
    get_last_session_sets,
    get_last_same_day_session,
    get_today_sets,
    get_recent_sessions,
    get_session_detail,
)

st.set_page_config(
    page_title="FitnessBuddy",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── global styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── typography ── */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                 "Segoe UI", Roboto, sans-serif;
}
h1 { font-weight: 800; letter-spacing: -0.5px; }
h2 { font-weight: 700; }
h3 { font-weight: 600; }

/* ── section label ── */
.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #999;
    margin: 20px 0 8px 0;
}

/* ── exercise group header ── */
.ex-header {
    font-size: 17px;
    font-weight: 700;
    color: #1a1a2e;
    padding: 14px 0 6px 0;
    border-bottom: 2px solid #FF4B4B;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── set card ── */
.set-card {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #f7f8fc;
    border-radius: 10px;
    padding: 10px 14px;
    margin: 5px 0;
}
.set-num {
    background: #FF4B4B;
    color: white;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    font-size: 11px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.set-weight {
    font-size: 17px;
    font-weight: 800;
    color: #1a1a2e;
}
.set-x {
    color: #bbb;
    font-size: 14px;
    font-weight: 600;
}
.set-reps {
    font-size: 17px;
    font-weight: 700;
    color: #444;
}
.set-reps span { font-size: 12px; font-weight: 500; color: #888; }
.set-rir {
    margin-left: auto;
    background: #eaf6ea;
    color: #2d862d;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 700;
}

/* ── session banner ── */
.session-banner {
    background: linear-gradient(135deg, #FF4B4B 0%, #ff7b55 100%);
    border-radius: 14px;
    padding: 16px 20px;
    color: white;
    margin-bottom: 4px;
}
.session-banner .day-type {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
    line-height: 1.1;
}
.session-banner .day-date {
    font-size: 14px;
    opacity: 0.85;
    margin-top: 4px;
    font-weight: 500;
}

/* ── prev-session info box ── */
.prev-box {
    background: #f0f4ff;
    border-left: 4px solid #4B7BFF;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 14px;
    color: #333;
}
.prev-box .prev-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #4B7BFF;
    margin-bottom: 6px;
}

/* ── history card ── */
.hist-date {
    font-size: 15px;
    font-weight: 700;
    color: #1a1a2e;
}
.hist-meta {
    font-size: 13px;
    color: #888;
    margin-top: 2px;
}

/* ── exercise library row ── */
.lib-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;
}
.lib-name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.lib-tag {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 20px;
    background: #f0f2f6;
    color: #666;
}
</style>
""", unsafe_allow_html=True)


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


def _set_card_html(i: int, s: dict) -> str:
    rir_html = (
        f'<span class="set-rir">RIR {s["rir"]}</span>'
        if s.get("rir") is not None else ""
    )
    return (
        f'<div class="set-card">'
        f'<div class="set-num">{i}</div>'
        f'<span class="set-weight">{s["weight_kg"]} kg</span>'
        f'<span class="set-x">×</span>'
        f'<span class="set-reps">{s["reps"]}<span> reps</span></span>'
        f'{rir_html}'
        f'</div>'
    )


def _render_session_sets(sets: list[dict]) -> None:
    order: list[str] = []
    grouped: dict[str, list] = {}
    for s in sets:
        name = s["exercises"]["name"]
        if name not in grouped:
            order.append(name)
            grouped[name] = []
        grouped[name].append(s)

    for name in order:
        st.markdown(f'<div class="ex-header">{name}</div>', unsafe_allow_html=True)
        cards = "".join(
            _set_card_html(i, s) for i, s in enumerate(grouped[name], 1)
        )
        st.markdown(cards, unsafe_allow_html=True)


# ── tab layout ─────────────────────────────────────────────────────────────────

tab_log, tab_history, tab_exercises = st.tabs(["🏋️ Log", "📅 History", "📋 Exercises"])


# ══════════════════════════════════════════════════════════════════════════════
# LOG TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_log:
    exercises = get_exercises()

    # ── no active session: start screen ───────────────────────────────────────
    if st.session_state.session_id is None:
        st.markdown("# 💪 FitnessBuddy")
        st.markdown(
            '<p style="font-size:17px;color:#555;margin-top:-10px;margin-bottom:24px;">'
            "Track every set. See every gain.</p>",
            unsafe_allow_html=True,
        )
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
        today_date = datetime.date.today().strftime("%A, %d %B %Y")
        col_banner, col_end = st.columns([5, 1])
        with col_banner:
            st.markdown(
                f'<div class="session-banner">'
                f'<div class="day-type">{st.session_state.day_type} Day</div>'
                f'<div class="day-date">{today_date}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_end:
            st.write("")
            st.write("")
            if st.button("End ✓", use_container_width=True):
                st.session_state.session_id = None
                st.session_state.last_exercise_id = None
                st.session_state.last_sets_cache = []
                st.session_state.last_set_logged = None
                st.rerun()

        # ── last same-day session summary ─────────────────────────────────────
        prev_session, prev_sets = get_last_same_day_session(
            st.session_state.day_type, st.session_state.session_id
        )
        if prev_session:
            prev_date = prev_session.get("date", "")
            with st.expander(f"Last {st.session_state.day_type} Day — {prev_date}"):
                _render_session_sets(prev_sets)

        st.divider()

        # ── exercise selector ─────────────────────────────────────────────────
        st.markdown('<div class="section-label">Exercise</div>', unsafe_allow_html=True)
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
            label_visibility="collapsed",
        )
        current_exercise_id = emap.get(st.session_state.get("exercise_label", labels[0]))

        if current_exercise_id and st.session_state.last_exercise_id != current_exercise_id:
            _load_last_sets(current_exercise_id)

        # ── last session for this exercise ────────────────────────────────────
        if st.session_state.last_sets_cache:
            date_label = st.session_state.last_date_cache or "last session"
            rows_html = "".join(
                _set_card_html(s["set_number"], s)
                for s in st.session_state.last_sets_cache
            )
            st.markdown(
                f'<div class="prev-box">'
                f'<div class="prev-title">Last session — {date_label}</div>'
                f'{rows_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No previous data for this exercise.")

        st.divider()

        # ── weight input with quick-increment buttons ─────────────────────────
        st.markdown('<div class="section-label">Weight (kg)</div>', unsafe_allow_html=True)
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

        col_reps, col_rir = st.columns(2)
        with col_reps:
            st.markdown('<div class="section-label">Reps</div>', unsafe_allow_html=True)
            st.number_input("Reps", min_value=1, max_value=100, step=1, key="reps", label_visibility="collapsed")
        with col_rir:
            st.markdown('<div class="section-label">RIR</div>', unsafe_allow_html=True)
            st.number_input("RIR", min_value=0, max_value=10, step=1, key="rir", label_visibility="collapsed")

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
            if st.button("Duplicate ⧉", use_container_width=True, disabled=not has_last):
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
            st.markdown('<div class="section-label">Today\'s Log</div>', unsafe_allow_html=True)
            _render_session_sets(today)
        else:
            st.markdown(
                '<p style="color:#aaa;font-size:15px;text-align:center;padding:20px 0;">'
                "No sets yet — pick an exercise and add your first set."
                "</p>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### Session History")
    sessions = get_recent_sessions(limit=20)
    if not sessions:
        st.markdown(
            '<p style="color:#aaa;font-size:15px;text-align:center;padding:30px 0;">'
            "No sessions logged yet."
            "</p>",
            unsafe_allow_html=True,
        )
    else:
        for session in sessions:
            set_count = len(session.get("sets", []))
            sets_label = f"{set_count} set{'s' if set_count != 1 else ''}"
            label = f"**{session['date']}** — {session['day_type']}  ·  {sets_label}"
            with st.expander(label):
                detail = get_session_detail(session["id"])
                if detail:
                    _render_session_sets(detail)
                else:
                    st.caption("No sets recorded.")


# ══════════════════════════════════════════════════════════════════════════════
# EXERCISES TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_exercises:
    st.markdown("### Exercise Library")

    exercises_all = get_exercises()
    muscle_groups = sorted(
        {e["muscle_group"] for e in exercises_all if e.get("muscle_group")}
    )
    filter_mg = st.selectbox("Filter by muscle group", ["All"] + muscle_groups)

    filtered = (
        exercises_all
        if filter_mg == "All"
        else [e for e in exercises_all if e.get("muscle_group") == filter_mg]
    )

    rows_html = "".join(
        f'<div class="lib-row">'
        f'<span class="lib-name">{e["name"]}</span>'
        f'<span class="lib-tag">{e.get("muscle_group", "—")}  ·  {e.get("category", "—")}</span>'
        f'</div>'
        for e in filtered
    )
    st.markdown(rows_html, unsafe_allow_html=True)

    st.divider()
    st.markdown("### Add Exercise")

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
