import datetime
import streamlit as st
import streamlit.components.v1 as components
from db import (
    get_exercises,
    add_exercise,
    start_session,
    log_set,
    save_session_rating,
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

# ── constants ──────────────────────────────────────────────────────────────────
_HEADER_H = 88   # px — shared height for banner and timer

_ENERGY_OPTS   = ["Drained",      "Tired",     "OK",      "Good",  "Energised"]
_FATIGUE_OPTS  = ["Overtrained",  "Very Sore", "Normal",  "Mild",  "Fresh"]
_PERFORM_OPTS  = ["Poor",         "Below Par", "Average", "Good",  "Excellent"]

# ── global styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400&display=swap');

html, body, [class*="css"] {
    font-family: 'Lora', Georgia, 'Times New Roman', serif;
}

/* ── professional tab bar ── */
div[role="tablist"] {
    border-bottom: 1px solid #e5e7eb;
    gap: 0;
    background: transparent;
}
button[role="tab"] {
    font-family: 'Lora', Georgia, serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #6b7280 !important;
    padding: 10px 22px !important;
    border-radius: 0 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    letter-spacing: 0.02em !important;
    margin-bottom: -1px !important;
}
button[role="tab"]:hover {
    color: #374151 !important;
    background: #f9fafb !important;
}
button[role="tab"][aria-selected="true"] {
    color: #2563EB !important;
    border-bottom: 2px solid #2563EB !important;
    font-weight: 700 !important;
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── section label ── */
.section-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #9ca3af;
    margin: 16px 0 5px 0;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── exercise group header ── */
.ex-header {
    font-size: 16px;
    font-weight: 700;
    color: #1e3a5f;
    padding: 12px 0 5px 0;
    border-bottom: 2px solid #2563EB;
    margin-bottom: 7px;
    font-family: 'Lora', Georgia, serif;
}

/* ── set card ── */
.set-card {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #f0f4ff;
    border-radius: 10px;
    padding: 9px 13px;
    margin: 4px 0;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.set-num {
    background: #2563EB;
    color: white;
    border-radius: 50%;
    width: 22px; height: 22px;
    font-size: 11px; font-weight: 800;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.set-weight { font-size: 16px; font-weight: 800; color: #1e3a5f; }
.set-x      { color: #bbb; font-size: 13px; font-weight: 600; }
.set-reps   { font-size: 16px; font-weight: 700; color: #374151; }
.set-reps span { font-size: 12px; font-weight: 500; color: #9ca3af; }
.set-rir {
    margin-left: auto; background: #eff6ff; color: #1d4ed8;
    border-radius: 20px; padding: 3px 9px;
    font-size: 11px; font-weight: 700;
}

/* ── previous session box ── */
.prev-box {
    background: #eff6ff; border-left: 4px solid #2563EB;
    border-radius: 0 10px 10px 0; padding: 11px 15px; margin: 5px 0;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.prev-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #2563EB; margin-bottom: 5px;
}

/* ── exercise library row ── */
.lib-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 0; border-bottom: 1px solid #f3f4f6;
}
.lib-name { font-size: 14px; font-weight: 600; color: #1e3a5f; font-family: 'Lora', serif; }
.lib-tag {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
    background: #eff6ff; color: #2563EB;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
</style>
""", unsafe_allow_html=True)


# ── session state defaults ─────────────────────────────────────────────────────
_defaults: dict = {
    "session_id": None,
    "day_type": None,
    "session_start_ts": None,
    "session_end_ts": None,
    "confirm_end": False,
    "weight": 20.0,
    "weight_unit": "kg",
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

def _fmt(w) -> str:
    """Format weight without trailing zeros: 20.0 → '20', 20.5 → '20.5'."""
    return f"{float(w):g}"


def _exercise_map(exercises: list[dict]) -> dict[str, int]:
    return {f"{e['name']}  ·  {e['muscle_group']}": e["id"] for e in exercises}


def _load_last_sets(exercise_id: int) -> None:
    sets, date = get_last_session_sets(exercise_id, st.session_state.session_id)
    st.session_state.last_sets_cache = sets
    st.session_state.last_date_cache = date
    if sets:
        st.session_state.weight = float(sets[-1]["weight_kg"])
        st.session_state.weight_unit = sets[-1].get("unit", "kg")
    st.session_state.last_exercise_id = exercise_id


def _set_card_html(i: int, s: dict) -> str:
    unit    = s.get("unit", "kg")
    rir_html = (
        f'<span class="set-rir">RIR {s["rir"]}</span>'
        if s.get("rir") is not None else ""
    )
    return (
        f'<div class="set-card">'
        f'<div class="set-num">{i}</div>'
        f'<span class="set-weight">{_fmt(s["weight_kg"])} {unit}</span>'
        f'<span class="set-x">×</span>'
        f'<span class="set-reps">{s["reps"]}<span> reps</span></span>'
        f'{rir_html}'
        f'</div>'
    )


def _render_session_sets(sets: list[dict]) -> None:
    order:   list[str]       = []
    grouped: dict[str, list] = {}
    for s in sets:
        name = s["exercises"]["name"]
        if name not in grouped:
            order.append(name)
            grouped[name] = []
        grouped[name].append(s)
    for name in order:
        st.markdown(f'<div class="ex-header">{name}</div>', unsafe_allow_html=True)
        st.markdown(
            "".join(_set_card_html(i, s) for i, s in enumerate(grouped[name], 1)),
            unsafe_allow_html=True,
        )


def _live_timer(start_ts: int) -> None:
    components.html(f"""
    <div style="
        background: linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
        border-radius: 14px; color: white;
        height: {_HEADER_H}px; box-sizing: border-box;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center; gap: 3px;
    ">
        <div id="tmr" style="
            font-size: 28px; font-weight: 800; letter-spacing: -0.5px;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            line-height: 1;
        ">0:00</div>
        <div style="
            font-size: 10px; opacity: 0.5; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.12em;
            font-family: -apple-system, sans-serif;
        ">session time</div>
    </div>
    <script>
    const s = {start_ts};
    function tick() {{
        const e = Math.floor(Date.now() / 1000) - s;
        const m = Math.floor(e / 60), sc = e % 60;
        document.getElementById('tmr').textContent = m + ':' + (sc < 10 ? '0' : '') + sc;
    }}
    tick(); setInterval(tick, 1000);
    </script>
    """, height=_HEADER_H)


def _end_session() -> None:
    st.session_state.session_id       = None
    st.session_state.session_start_ts = None
    st.session_state.session_end_ts   = None
    st.session_state.confirm_end      = False
    st.session_state.last_exercise_id = None
    st.session_state.last_sets_cache  = []
    st.session_state.last_set_logged  = None


def _show_end_summary() -> None:
    today_sets = get_today_sets(st.session_state.session_id)
    start_ts   = st.session_state.session_start_ts or 0
    end_ts     = st.session_state.session_end_ts or int(datetime.datetime.now().timestamp())
    duration   = max(0, round((end_ts - start_ts) / 60))
    total_sets = len(today_sets)
    total_vol  = sum(float(s["weight_kg"]) * s["reps"] for s in today_sets)

    order:   list[str]       = []
    grouped: dict[str, list] = {}
    for s in today_sets:
        name = s["exercises"]["name"]
        if name not in grouped:
            order.append(name)
            grouped[name] = []
        grouped[name].append(s)

    today_date = datetime.date.today().strftime("%A, %d %B %Y")
    st.markdown(
        f'<div style="background: linear-gradient(135deg,#1e3a8a 0%,#2563EB 100%);'
        f'border-radius: 16px; padding: 24px 20px; color: white; text-align: center; margin-bottom: 20px;">'
        f'<div style="font-size: 36px; font-weight: 800; letter-spacing: -1px;'
        f'font-family: Lora, Georgia, serif; line-height: 1;">Session Complete</div>'
        f'<div style="font-size: 14px; font-weight: 600; opacity: 0.85; margin-top: 5px;'
        f'font-family: -apple-system, sans-serif;">{st.session_state.day_type} Day  ·  {today_date}</div>'
        f'<div style="display: flex; justify-content: center; gap: 36px; margin-top: 20px;">'
        f'<div><div style="font-size: 26px; font-weight: 800; font-family: -apple-system, sans-serif;">{duration}</div>'
        f'<div style="font-size: 10px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; font-family: -apple-system, sans-serif;">min</div></div>'
        f'<div><div style="font-size: 26px; font-weight: 800; font-family: -apple-system, sans-serif;">{total_sets}</div>'
        f'<div style="font-size: 10px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; font-family: -apple-system, sans-serif;">sets</div></div>'
        f'<div><div style="font-size: 26px; font-weight: 800; font-family: -apple-system, sans-serif;">{total_vol:,.0f}</div>'
        f'<div style="font-size: 10px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; font-family: -apple-system, sans-serif;">kg vol</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    if order:
        st.markdown('<div class="section-label">Exercises</div>', unsafe_allow_html=True)
        rows = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:10px 0;border-bottom:1px solid #f0f4ff;">'
            f'<span style="font-size:15px;font-weight:600;color:#1e3a5f;font-family:Lora,serif;">{name}</span>'
            f'<span style="font-size:13px;color:#9ca3af;font-family:-apple-system,sans-serif;">'
            f'{len(grouped[name])} set{"s" if len(grouped[name])!=1 else ""}  ·  '
            f'up to {_fmt(max(float(s["weight_kg"]) for s in grouped[name]))} {grouped[name][0].get("unit","kg")}</span>'
            f'</div>'
            for name in order
        )
        st.markdown(rows, unsafe_allow_html=True)

    # ── optional workout rating ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**How did it go?** *(optional)*")
    rate_it = st.checkbox("Rate this session", key="rate_it_checkbox")
    if rate_it:
        e = st.select_slider("Energy level",       options=_ENERGY_OPTS,  value="OK",      key="r_energy")
        f = st.select_slider("Body / fatigue",     options=_FATIGUE_OPTS, value="Normal",  key="r_fatigue")
        p = st.select_slider("Overall performance",options=_PERFORM_OPTS, value="Average", key="r_perform")

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Resume Session", use_container_width=True):
            st.session_state.confirm_end    = False
            st.session_state.session_end_ts = None
            st.rerun()
    with col2:
        if st.button("Done", type="primary", use_container_width=True):
            if st.session_state.get("rate_it_checkbox", False):
                e_val = st.session_state.get("r_energy",  "OK")
                f_val = st.session_state.get("r_fatigue", "Normal")
                p_val = st.session_state.get("r_perform", "Average")
                score = round((
                    _ENERGY_OPTS.index(e_val)  + 1 +
                    _FATIGUE_OPTS.index(f_val) + 1 +
                    _PERFORM_OPTS.index(p_val) + 1
                ) / 3, 1)
                save_session_rating(st.session_state.session_id, score)
            _end_session()
            st.rerun()


# ── side panel functions ───────────────────────────────────────────────────────

def _side_history() -> None:
    sessions = get_recent_sessions(limit=20)
    if not sessions:
        st.caption("No sessions yet.")
        return
    for session in sessions:
        n     = len(session.get("sets", []))
        stars = f"  ·  ★ {session['rating']}" if session.get("rating") else ""
        label = f"**{session['date']}** — {session['day_type']}  ·  {n} set{'s' if n!=1 else ''}{stars}"
        with st.expander(label):
            detail = get_session_detail(session["id"])
            if detail:
                _render_session_sets(detail)
            else:
                st.caption("No sets recorded.")


def _side_exercises() -> None:
    exercises_all = get_exercises()
    muscle_groups = sorted({e["muscle_group"] for e in exercises_all if e.get("muscle_group")})
    fmg = st.selectbox("Filter", ["All"] + muscle_groups, key="ex_filter")
    filtered = (
        exercises_all if fmg == "All"
        else [e for e in exercises_all if e.get("muscle_group") == fmg]
    )
    st.markdown(
        "".join(
            f'<div class="lib-row">'
            f'<span class="lib-name">{e["name"]}</span>'
            f'<span class="lib-tag">{e.get("muscle_group","—")} · {e.get("category","—")}</span>'
            f'</div>'
            for e in filtered
        ),
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**Add exercise**")
    with st.form("add_exercise_form", clear_on_submit=True):
        new_name   = st.text_input("Name")
        new_muscle = st.selectbox("Muscle group",
                        ["Back","Chest","Shoulders","Arms","Legs","Core","Other"])
        new_cat    = st.selectbox("Category", ["compound","isolation"])
        submitted  = st.form_submit_button("Add", use_container_width=True)
    if submitted:
        if new_name.strip():
            add_exercise(new_name.strip(), new_muscle, new_cat)
            st.success(f"Added '{new_name.strip()}'")
            st.rerun()
        else:
            st.warning("Enter a name.")


# ══════════════════════════════════════════════════════════════════════════════
# TOP-LEVEL TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_strength, tab_cardio = st.tabs(["Strength Training", "Cardio"])


# ══════════════════════════════════════════════════════════════════════════════
# STRENGTH TRAINING TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_strength:
    exercises = get_exercises()

    # ── no active session ─────────────────────────────────────────────────────
    if st.session_state.session_id is None:
        st.markdown("# FitnessBuddy")
        st.markdown(
            '<p style="font-size:17px;color:#6b7280;margin-top:-10px;margin-bottom:24px;">'
            "Track every set. See every gain.</p>",
            unsafe_allow_html=True,
        )
        day_type = st.selectbox(
            "What are you training today?",
            ["Push","Pull","Legs","Upper","Lower","Full Body","Custom"],
        )
        if st.button("Start Session", type="primary", use_container_width=True):
            st.session_state.session_id       = start_session(day_type)
            st.session_state.day_type         = day_type
            st.session_state.session_start_ts = int(datetime.datetime.now().timestamp())
            st.session_state.last_exercise_id = None
            st.session_state.last_sets_cache  = []
            st.session_state.last_set_logged  = None
            st.rerun()

    # ── end-session summary ───────────────────────────────────────────────────
    elif st.session_state.confirm_end:
        _show_end_summary()

    # ── active session ────────────────────────────────────────────────────────
    else:
        # header: banner + live timer
        today_date    = datetime.date.today().strftime("%A, %d %B %Y")
        col_ban, col_tmr = st.columns([3, 2])
        with col_ban:
            st.markdown(
                f'<div style="background: linear-gradient(135deg,#1e3a8a 0%,#2563EB 100%);'
                f'border-radius: 14px; padding: 0 20px; color: white;'
                f'height: {_HEADER_H}px; box-sizing: border-box;'
                f'display: flex; flex-direction: column; justify-content: center;">'
                f'<div style="font-size: 22px; font-weight: 700; letter-spacing: -0.3px;'
                f'font-family: Lora, Georgia, serif; line-height: 1.2;">'
                f'{st.session_state.day_type} Day</div>'
                f'<div style="font-size: 12px; opacity: 0.8; margin-top: 5px;'
                f'font-family: -apple-system, sans-serif; font-weight: 500;">{today_date}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_tmr:
            _live_timer(st.session_state.session_start_ts)

        # last same-day session
        prev_session, prev_sets = get_last_same_day_session(
            st.session_state.day_type, st.session_state.session_id
        )
        if prev_session:
            with st.expander(f"Last {st.session_state.day_type} Day — {prev_session.get('date','')}"):
                _render_session_sets(prev_sets)

        st.divider()

        # two-column layout
        col_main, col_side = st.columns([3, 2])

        with col_side:
            side_hist, side_ex = st.tabs(["History", "Exercises"])
            with side_hist:
                _side_history()
            with side_ex:
                _side_exercises()

        with col_main:
            # exercise selector
            st.markdown('<div class="section-label">Exercise</div>', unsafe_allow_html=True)
            emap   = _exercise_map(exercises)
            labels = list(emap.keys())

            def _on_exercise_change() -> None:
                ex_id = emap.get(st.session_state.exercise_label)
                if ex_id is not None:
                    _load_last_sets(ex_id)

            st.selectbox(
                "Exercise", labels, key="exercise_label",
                on_change=_on_exercise_change, label_visibility="collapsed",
            )
            current_exercise_id = emap.get(
                st.session_state.get("exercise_label", labels[0])
            )
            if current_exercise_id and st.session_state.last_exercise_id != current_exercise_id:
                _load_last_sets(current_exercise_id)

            # last session recall
            if st.session_state.last_sets_cache:
                date_label = st.session_state.last_date_cache or "last session"
                rows_html = "".join(
                    _set_card_html(s["set_number"], s)
                    for s in st.session_state.last_sets_cache
                )
                st.markdown(
                    f'<div class="prev-box">'
                    f'<div class="prev-title">Last session — {date_label}</div>'
                    f'{rows_html}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("No previous data for this exercise.")

            st.divider()

            # weight label + unit toggle on the same line
            col_wlabel, col_unit = st.columns([3, 2])
            with col_wlabel:
                st.markdown('<div class="section-label">Weight</div>', unsafe_allow_html=True)
            with col_unit:
                st.radio(
                    "unit", ["kg", "lbs"],
                    key="weight_unit",
                    horizontal=True,
                    label_visibility="collapsed",
                )

            st.number_input(
                "Weight", min_value=0.0, step=0.5,
                key="weight", label_visibility="collapsed",
            )

            # increment / decrement buttons below the input
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("−5", use_container_width=True):
                    st.session_state.weight = max(0.0, st.session_state.weight - 5.0)
            with c2:
                if st.button("−2.5", use_container_width=True):
                    st.session_state.weight = max(0.0, st.session_state.weight - 2.5)
            with c3:
                if st.button("+2.5", use_container_width=True):
                    st.session_state.weight += 2.5
            with c4:
                if st.button("+5", use_container_width=True):
                    st.session_state.weight += 5.0

            # reps + RIR
            col_r, col_i = st.columns(2)
            with col_r:
                st.markdown('<div class="section-label">Reps</div>', unsafe_allow_html=True)
                st.number_input("Reps", min_value=1, max_value=100, step=1,
                                key="reps", label_visibility="collapsed")
            with col_i:
                st.markdown('<div class="section-label">RIR</div>', unsafe_allow_html=True)
                st.number_input("RIR", min_value=0, max_value=10, step=1,
                                key="rir", label_visibility="collapsed")

            # add / duplicate
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Add Set", type="primary", use_container_width=True):
                    log_set(
                        st.session_state.session_id, current_exercise_id,
                        st.session_state.weight, st.session_state.reps,
                        st.session_state.rir, st.session_state.weight_unit,
                    )
                    st.session_state.last_set_logged = {
                        "weight_kg": st.session_state.weight,
                        "reps":      st.session_state.reps,
                        "rir":       st.session_state.rir,
                        "unit":      st.session_state.weight_unit,
                    }
                    st.rerun()
            with b2:
                has_last = st.session_state.last_set_logged is not None
                if st.button("Duplicate", use_container_width=True, disabled=not has_last):
                    last = st.session_state.last_set_logged
                    log_set(
                        st.session_state.session_id, current_exercise_id,
                        last["weight_kg"], last["reps"], last["rir"], last.get("unit","kg"),
                    )
                    st.rerun()

            st.divider()

            # today's log
            today = get_today_sets(st.session_state.session_id)
            if today:
                st.markdown('<div class="section-label">Today\'s Log</div>', unsafe_allow_html=True)
                _render_session_sets(today)
            else:
                st.markdown(
                    '<p style="color:#d1d5db;font-size:14px;text-align:center;padding:16px 0;">'
                    "No sets yet — add your first set above."
                    "</p>",
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("End Session", use_container_width=True):
                st.session_state.confirm_end    = True
                st.session_state.session_end_ts = int(datetime.datetime.now().timestamp())
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CARDIO TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_cardio:
    st.markdown("### Cardio")
    st.info("Cardio tracking coming soon — runs, cycles, and rowing sessions.")
