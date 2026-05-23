import datetime
import streamlit as st
import streamlit.components.v1 as components
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
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                 "Segoe UI", Roboto, sans-serif;
}
h1 { font-weight: 800; letter-spacing: -0.5px; }
h2 { font-weight: 700; }
h3 { font-weight: 600; }

.section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #999;
    margin: 16px 0 6px 0;
}
.ex-header {
    font-size: 16px;
    font-weight: 700;
    color: #1a1a2e;
    padding: 12px 0 5px 0;
    border-bottom: 2px solid #FF4B4B;
    margin-bottom: 7px;
}
.set-card {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #f7f8fc;
    border-radius: 10px;
    padding: 9px 13px;
    margin: 4px 0;
}
.set-num {
    background: #FF4B4B;
    color: white;
    border-radius: 50%;
    width: 22px; height: 22px;
    font-size: 11px; font-weight: 800;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.set-weight { font-size: 16px; font-weight: 800; color: #1a1a2e; }
.set-x      { color: #bbb; font-size: 13px; font-weight: 600; }
.set-reps   { font-size: 16px; font-weight: 700; color: #444; }
.set-reps span { font-size: 12px; font-weight: 500; color: #888; }
.set-rir    { margin-left: auto; background: #eaf6ea; color: #2d862d;
              border-radius: 20px; padding: 3px 9px;
              font-size: 11px; font-weight: 700; }
.prev-box   { background: #f0f4ff; border-left: 4px solid #4B7BFF;
              border-radius: 0 10px 10px 0; padding: 11px 15px; margin: 5px 0; }
.prev-title { font-size: 11px; font-weight: 700; text-transform: uppercase;
              letter-spacing: 0.08em; color: #4B7BFF; margin-bottom: 5px; }
.lib-row    { display: flex; align-items: center; justify-content: space-between;
              padding: 9px 0; border-bottom: 1px solid #f0f0f0; }
.lib-name   { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.lib-tag    { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
              background: #f0f2f6; color: #666; }
</style>
""", unsafe_allow_html=True)


# ── session state defaults ─────────────────────────────────────────────────────
_defaults: dict = {
    "session_id": None,
    "day_type": None,
    "session_start_ts": None,
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
        st.markdown(
            "".join(_set_card_html(i, s) for i, s in enumerate(grouped[name], 1)),
            unsafe_allow_html=True,
        )


def _live_timer(start_ts: int) -> None:
    components.html(f"""
    <div style="
        background: linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
        border-radius:14px; padding:14px 10px;
        text-align:center; color:white;
    ">
        <div id="tmr" style="
            font-size:28px; font-weight:800; letter-spacing:-0.5px;
            font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;
        ">0:00</div>
        <div style="
            font-size:10px; opacity:0.6; font-weight:600;
            text-transform:uppercase; letter-spacing:0.12em; margin-top:3px;
            font-family:-apple-system,sans-serif;
        ">session time</div>
    </div>
    <script>
    const s={start_ts};
    function tick(){{
        const e=Math.floor(Date.now()/1000)-s;
        const m=Math.floor(e/60), sc=e%60;
        document.getElementById('tmr').textContent=m+':'+(sc<10?'0':'')+sc;
    }}
    tick(); setInterval(tick,1000);
    </script>
    """, height=90)


def _end_session() -> None:
    st.session_state.session_id = None
    st.session_state.session_start_ts = None
    st.session_state.last_exercise_id = None
    st.session_state.last_sets_cache = []
    st.session_state.last_set_logged = None


# ── side panel: history + exercises ───────────────────────────────────────────

def _side_history() -> None:
    sessions = get_recent_sessions(limit=20)
    if not sessions:
        st.caption("No sessions yet.")
        return
    for session in sessions:
        n = len(session.get("sets", []))
        label = f"**{session['date']}** — {session['day_type']}  ·  {n} set{'s' if n!=1 else ''}"
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
    filtered = exercises_all if fmg == "All" else [e for e in exercises_all if e.get("muscle_group") == fmg]
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
tab_strength, tab_cardio = st.tabs(["💪 Strength Training", "🏃 Cardio"])


# ══════════════════════════════════════════════════════════════════════════════
# STRENGTH TRAINING TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_strength:
    exercises = get_exercises()

    # ── no active session ─────────────────────────────────────────────────────
    if st.session_state.session_id is None:
        st.markdown("# 💪 FitnessBuddy")
        st.markdown(
            '<p style="font-size:17px;color:#555;margin-top:-10px;margin-bottom:24px;">'
            "Track every set. See every gain.</p>",
            unsafe_allow_html=True,
        )
        day_type = st.selectbox(
            "What are you training today?",
            ["Push","Pull","Legs","Upper","Lower","Full Body","Custom"],
        )
        if st.button("Start Session", type="primary", use_container_width=True):
            st.session_state.session_id     = start_session(day_type)
            st.session_state.day_type       = day_type
            st.session_state.session_start_ts = int(datetime.datetime.now().timestamp())
            st.session_state.last_exercise_id = None
            st.session_state.last_sets_cache  = []
            st.session_state.last_set_logged  = None
            st.rerun()

    # ── active session ────────────────────────────────────────────────────────
    else:
        # ── header: banner + live timer ───────────────────────────────────────
        today_date = datetime.date.today().strftime("%A, %d %B %Y")
        col_banner, col_timer = st.columns([3, 2])
        with col_banner:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#FF4B4B 0%,#ff7b55 100%);'
                f'border-radius:14px;padding:16px 20px;color:white;">'
                f'<div style="font-size:24px;font-weight:800;letter-spacing:-0.5px;'
                f'line-height:1.1;">{st.session_state.day_type} Day</div>'
                f'<div style="font-size:13px;opacity:0.85;margin-top:4px;'
                f'font-weight:500;">{today_date}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_timer:
            _live_timer(st.session_state.session_start_ts)

        # ── last same-day session ─────────────────────────────────────────────
        prev_session, prev_sets = get_last_same_day_session(
            st.session_state.day_type, st.session_state.session_id
        )
        if prev_session:
            with st.expander(f"Last {st.session_state.day_type} Day — {prev_session.get('date','')}"):
                _render_session_sets(prev_sets)

        st.divider()

        # ── two-column layout: logging (left) | history+exercises (right) ─────
        col_main, col_side = st.columns([3, 2])

        # ── RIGHT: history + exercises ────────────────────────────────────────
        with col_side:
            side_hist, side_ex = st.tabs(["📅 History", "📋 Exercises"])
            with side_hist:
                _side_history()
            with side_ex:
                _side_exercises()

        # ── LEFT: logging ─────────────────────────────────────────────────────
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

            # last session for this exercise
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

            # weight + increments
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
                "Weight", min_value=0.0, step=0.5,
                key="weight", label_visibility="collapsed",
            )

            # reps + RIR side by side
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
                if st.button("Add Set ✚", type="primary", use_container_width=True):
                    log_set(
                        st.session_state.session_id, current_exercise_id,
                        st.session_state.weight, st.session_state.reps, st.session_state.rir,
                    )
                    st.session_state.last_set_logged = {
                        "weight_kg": st.session_state.weight,
                        "reps": st.session_state.reps,
                        "rir": st.session_state.rir,
                    }
                    st.rerun()
            with b2:
                has_last = st.session_state.last_set_logged is not None
                if st.button("Duplicate ⧉", use_container_width=True, disabled=not has_last):
                    last = st.session_state.last_set_logged
                    log_set(
                        st.session_state.session_id, current_exercise_id,
                        last["weight_kg"], last["reps"], last["rir"],
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
                    '<p style="color:#aaa;font-size:14px;text-align:center;padding:16px 0;">'
                    "No sets yet — add your first set above."
                    "</p>",
                    unsafe_allow_html=True,
                )

            # end button at the bottom
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("End Session", use_container_width=True):
                _end_session()
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CARDIO TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_cardio:
    st.markdown("### 🏃 Cardio")
    st.info("Cardio tracking is coming soon. You'll be able to log runs, cycles, and other cardio sessions here.")
