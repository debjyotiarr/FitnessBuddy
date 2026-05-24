import datetime
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db import (
    get_exercises, add_exercise,
    start_session, log_set, save_session_rating,
    get_last_session_sets, get_last_same_day_session,
    get_today_sets, get_recent_sessions, get_session_detail,
    get_routines, get_routine_detail, create_routine, delete_routine,
    get_all_sets_for_analytics, get_bodyweight_history, log_bodyweight,
    update_exercise_sfr,
)
from sfr import score_sets, sfr_color, set_stimulus, set_fatigue

st.set_page_config(
    page_title="FitnessBuddy",
    page_icon="💪",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── constants ──────────────────────────────────────────────────────────────────
_HEADER_H    = 88
_DAY_TYPES   = ["Push", "Pull", "Legs", "Upper", "Lower", "Full Body", "Custom"]
_ENERGY_OPTS = ["Drained",     "Tired",     "OK",      "Good",  "Energised"]
_FATIGUE_OPTS= ["Overtrained", "Very Sore", "Normal",  "Mild",  "Fresh"]
_PERFORM_OPTS= ["Poor",        "Below Par", "Average", "Good",  "Excellent"]

# ── global styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400&display=swap');

html, body, [class*="css"] {
    font-family: 'Lora', Georgia, 'Times New Roman', serif;
}

/* ── tab bar ── */
div[role="tablist"] {
    border-bottom: 1px solid #e5e7eb;
    gap: 0; background: transparent;
}
button[role="tab"] {
    font-family: 'Lora', Georgia, serif !important;
    font-size: 14px !important; font-weight: 600 !important;
    color: #6b7280 !important; padding: 10px 22px !important;
    border-radius: 0 !important; border: none !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    letter-spacing: 0.02em !important; margin-bottom: -1px !important;
}
button[role="tab"]:hover { color: #374151 !important; background: #f9fafb !important; }
button[role="tab"][aria-selected="true"] {
    color: #2563EB !important;
    border-bottom: 2px solid #2563EB !important;
    font-weight: 700 !important;
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

.section-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #9ca3af; margin: 16px 0 5px 0;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.ex-header {
    font-size: 16px; font-weight: 700; color: #1e3a5f;
    padding: 12px 0 5px 0; border-bottom: 2px solid #2563EB;
    margin-bottom: 7px; font-family: 'Lora', Georgia, serif;
}
.set-card {
    display: flex; align-items: center; gap: 10px;
    background: #f0f4ff; border-radius: 10px;
    padding: 9px 13px; margin: 4px 0;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.set-num {
    background: #2563EB; color: white; border-radius: 50%;
    width: 22px; height: 22px; font-size: 11px; font-weight: 800;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.set-weight { font-size: 16px; font-weight: 800; color: #1e3a5f; }
.set-x      { color: #bbb; font-size: 13px; font-weight: 600; }
.set-reps   { font-size: 16px; font-weight: 700; color: #374151; }
.set-reps span { font-size: 12px; font-weight: 500; color: #9ca3af; }
.set-rir {
    margin-left: auto; background: #eff6ff; color: #1d4ed8;
    border-radius: 20px; padding: 3px 9px; font-size: 11px; font-weight: 700;
}
.prev-box {
    background: #eff6ff; border-left: 4px solid #2563EB;
    border-radius: 0 10px 10px 0; padding: 11px 15px; margin: 5px 0;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.prev-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #2563EB; margin-bottom: 5px;
}
.lib-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 0; border-bottom: 1px solid #f3f4f6;
}
.lib-name { font-size: 14px; font-weight: 600; color: #1e3a5f; font-family: 'Lora', Georgia, serif; }
.lib-tag {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
    background: #eff6ff; color: #2563EB;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.routine-row {
    display: flex; align-items: center;
    padding: 8px 0; border-bottom: 1px solid #f3f4f6; gap: 10px;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.routine-done   { color: #9ca3af; text-decoration: line-through; font-size: 14px; }
.routine-todo   { color: #1e3a5f; font-weight: 600; font-size: 14px; }
.routine-icon   { font-size: 16px; flex-shrink: 0; }
</style>
""", unsafe_allow_html=True)


# ── session state defaults ─────────────────────────────────────────────────────
_defaults: dict = {
    "session_id": None,
    "day_type": None,
    "session_start_ts": None,
    "session_end_ts": None,
    "confirm_end": False,
    "routine_id": None,
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
    return f"{float(w):g}"


def _exercise_map(exercises: list[dict]) -> dict[str, int]:
    return {f"{e['name']}  ·  {e['muscle_group']}": e["id"] for e in exercises}


def _load_last_sets(exercise_id: int) -> None:
    sets, date = get_last_session_sets(exercise_id, st.session_state.session_id)
    st.session_state.last_sets_cache = sets
    st.session_state.last_date_cache = date
    if sets:
        st.session_state.weight      = float(sets[-1]["weight_kg"])
        st.session_state.weight_unit = sets[-1].get("unit", "kg")
    st.session_state.last_exercise_id = exercise_id


def _set_card_html(i: int, s: dict) -> str:
    unit     = s.get("unit", "kg")
    rir_html = (f'<span class="set-rir">RIR {s["rir"]}</span>'
                if s.get("rir") is not None else "")
    return (
        f'<div class="set-card">'
        f'<div class="set-num">{i}</div>'
        f'<span class="set-weight">{_fmt(s["weight_kg"])} {unit}</span>'
        f'<span class="set-x">×</span>'
        f'<span class="set-reps">{s["reps"]}<span> reps</span></span>'
        f'{rir_html}</div>'
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
    <div style="background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
        border-radius:14px;color:white;height:{_HEADER_H}px;box-sizing:border-box;
        display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;">
      <div id="tmr" style="font-size:28px;font-weight:800;letter-spacing:-0.5px;
          font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;line-height:1;">
        0:00</div>
      <div style="font-size:10px;opacity:0.5;font-weight:600;text-transform:uppercase;
          letter-spacing:0.12em;font-family:-apple-system,sans-serif;">session time</div>
    </div>
    <script>
    const s={start_ts};
    function tick(){{
        const e=Math.floor(Date.now()/1000)-s,m=Math.floor(e/60),sc=e%60;
        document.getElementById('tmr').textContent=m+':'+(sc<10?'0':'')+sc;
    }}
    tick();setInterval(tick,1000);
    </script>""", height=_HEADER_H)


def _end_session() -> None:
    for k in ("session_id","session_start_ts","session_end_ts","confirm_end",
              "routine_id","last_exercise_id","last_sets_cache","last_set_logged"):
        st.session_state[k] = _defaults[k]


# ══════════════════════════════════════════════════════════════════════════════
# PANEL COMPONENTS (shared between front-page tabs and active-session side panel)
# ══════════════════════════════════════════════════════════════════════════════

def _panel_history() -> None:
    sessions = get_recent_sessions(limit=20)
    if not sessions:
        st.caption("No sessions logged yet.")
        return
    for session in sessions:
        n     = len(session.get("sets", []))
        stars = f"  ·  ★ {session['rating']}" if session.get("rating") else ""
        label = f"**{session['date']}** — {session['day_type']}  ·  {n} set{'s' if n!=1 else ''}{stars}"
        with st.expander(label):
            detail = get_session_detail(session["id"])
            if detail:
                _render_session_sets(detail)
                stim, fat, sfr = score_sets(detail)
                _sc = sfr_color(sfr)
                st.markdown(
                    f'<div style="display:flex;gap:8px;margin-top:10px;">'
                    f'<span style="font-size:11px;color:#6b7280;font-family:-apple-system,sans-serif;">'
                    f'Stimulus <b style="color:#1e3a5f">{stim:,.0f}</b></span>'
                    f'<span style="color:#d1d5db">·</span>'
                    f'<span style="font-size:11px;color:#6b7280;font-family:-apple-system,sans-serif;">'
                    f'Fatigue <b style="color:#1e3a5f">{fat:,.0f}</b></span>'
                    f'<span style="color:#d1d5db">·</span>'
                    f'<span style="font-size:11px;font-weight:700;color:{_sc};'
                    f'font-family:-apple-system,sans-serif;">SFR {sfr:.2f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("No sets recorded.")


def _panel_exercises(exercises_all: list[dict]) -> None:
    muscle_groups = sorted({e["muscle_group"] for e in exercises_all if e.get("muscle_group")})
    fmg = st.selectbox("Filter", ["All"] + muscle_groups, key="ex_filter")
    filtered = exercises_all if fmg == "All" else [
        e for e in exercises_all if e.get("muscle_group") == fmg
    ]
    st.markdown(
        "".join(
            f'<div class="lib-row">'
            f'<span class="lib-name">{e["name"]}</span>'
            f'<span style="display:flex;gap:5px;align-items:center;">'
            f'<span class="lib-tag">{e.get("muscle_group","—")} · {e.get("category","—")}</span>'
            f'<span class="lib-tag" style="background:#f0fdf4;color:#16a34a;">SFR {float(e.get("sfr_rating") or 3):.1f}</span>'
            f'</span>'
            f'</div>'
            for e in filtered
        ),
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**Adjust SFR rating**")
    st.caption("Override the stimulus/fatigue multiplier for a specific exercise (1 = low SFR, 5 = high SFR, 3 = default).")
    ex_name_to_id = {e["name"]: e["id"] for e in exercises_all}
    with st.form("sfr_edit_form", clear_on_submit=False):
        sfr_ex    = st.selectbox("Exercise", list(ex_name_to_id.keys()), key="sfr_edit_ex")
        cur_sfr   = float(next((e.get("sfr_rating") or 3.0
                                for e in exercises_all if e["name"] == sfr_ex), 3.0))
        new_sfr   = st.select_slider(
            "SFR rating", options=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
            value=cur_sfr, key="sfr_edit_val",
        )
        if st.form_submit_button("Save", use_container_width=True):
            update_exercise_sfr(ex_name_to_id[sfr_ex], new_sfr)
            st.success(f"SFR for {sfr_ex} set to {new_sfr}")
            st.rerun()
    st.divider()
    st.markdown("**Add exercise**")
    with st.form("add_exercise_form", clear_on_submit=True):
        new_name   = st.text_input("Name")
        new_muscle = st.selectbox("Muscle group",
                        ["Back","Chest","Shoulders","Arms","Legs","Core","Other"])
        new_cat    = st.selectbox("Category", ["compound","isolation"])
        if st.form_submit_button("Add", use_container_width=True):
            if new_name.strip():
                add_exercise(new_name.strip(), new_muscle, new_cat)
                st.success(f"Added '{new_name.strip()}'")
                st.rerun()
            else:
                st.warning("Enter a name.")


def _panel_routines(exercises_all: list[dict]) -> None:
    routines = get_routines()

    if not routines:
        st.caption("No routines yet — create one below.")
    else:
        for r in routines:
            detail    = get_routine_detail(r["id"])
            day_label = f"  ·  {r['day_type']}" if r.get("day_type") else ""
            ex_names  = [ex["exercises"]["name"] for ex in detail]
            with st.expander(f"**{r['name']}**{day_label}"):
                for i, name in enumerate(ex_names, 1):
                    st.write(f"{i}. {name}")
                if st.button("Delete routine", key=f"del_{r['id']}",
                             use_container_width=True):
                    delete_routine(r["id"])
                    st.rerun()

    st.divider()
    st.markdown("**Create Routine**")
    ex_name_to_id = {e["name"]: e["id"] for e in exercises_all}
    with st.form("create_routine_form", clear_on_submit=True):
        r_name   = st.text_input("Routine name")
        r_day    = st.selectbox("Day type",
                        ["Any"] + _DAY_TYPES, key="new_routine_day")
        selected = st.multiselect("Exercises (select in order)",
                        list(ex_name_to_id.keys()))
        if st.form_submit_button("Save Routine", use_container_width=True):
            if r_name.strip() and selected:
                create_routine(
                    r_name.strip(),
                    None if r_day == "Any" else r_day,
                    [ex_name_to_id[n] for n in selected],
                )
                st.success(f"'{r_name}' saved.")
                st.rerun()
            else:
                st.warning("Enter a name and pick at least one exercise.")


def _panel_routine_checklist(routine_id: int | None) -> None:
    """Live checklist shown during an active session."""
    if routine_id is None:
        st.caption("No routine selected for this session.")
        st.caption("Choose a routine on the start screen next time.")
        return

    routine_exs = get_routine_detail(routine_id)
    if not routine_exs:
        st.caption("This routine has no exercises.")
        return

    today_sets  = get_today_sets(st.session_state.session_id)
    done_ids    = {s["exercise_id"] for s in today_sets}
    done_count  = sum(1 for ex in routine_exs if ex["exercise_id"] in done_ids)
    total       = len(routine_exs)

    st.progress(done_count / total if total else 0)
    st.markdown(
        f'<div class="section-label">{done_count} of {total} done</div>',
        unsafe_allow_html=True,
    )

    rows = ""
    for ex in routine_exs:
        ex_id   = ex["exercise_id"]
        ex_name = ex["exercises"]["name"]
        done    = ex_id in done_ids
        if done:
            sets_done = [s for s in today_sets if s["exercise_id"] == ex_id]
            n    = len(sets_done)
            rows += (
                f'<div class="routine-row">'
                f'<span class="routine-icon">✅</span>'
                f'<span class="routine-done">{ex_name} — {n} set{"s" if n!=1 else ""}</span>'
                f'</div>'
            )
        else:
            rows += (
                f'<div class="routine-row">'
                f'<span class="routine-icon">◻</span>'
                f'<span class="routine-todo">{ex_name}</span>'
                f'</div>'
            )
    st.markdown(rows, unsafe_allow_html=True)


# ── end-session summary ────────────────────────────────────────────────────────

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
        f'<div style="background:linear-gradient(135deg,#1e3a8a 0%,#2563EB 100%);'
        f'border-radius:16px;padding:24px 20px;color:white;text-align:center;margin-bottom:20px;">'
        f'<div style="font-size:36px;font-weight:800;letter-spacing:-1px;'
        f'font-family:Lora,Georgia,serif;line-height:1;">Session Complete</div>'
        f'<div style="font-size:14px;font-weight:600;opacity:0.85;margin-top:5px;'
        f'font-family:-apple-system,sans-serif;">{st.session_state.day_type} Day  ·  {today_date}</div>'
        f'<div style="display:flex;justify-content:center;gap:36px;margin-top:20px;">'
        f'<div><div style="font-size:26px;font-weight:800;font-family:-apple-system,sans-serif;">{duration}</div>'
        f'<div style="font-size:10px;opacity:0.6;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;font-family:-apple-system,sans-serif;">min</div></div>'
        f'<div><div style="font-size:26px;font-weight:800;font-family:-apple-system,sans-serif;">{total_sets}</div>'
        f'<div style="font-size:10px;opacity:0.6;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;font-family:-apple-system,sans-serif;">sets</div></div>'
        f'<div><div style="font-size:26px;font-weight:800;font-family:-apple-system,sans-serif;">{total_vol:,.0f}</div>'
        f'<div style="font-size:10px;opacity:0.6;text-transform:uppercase;letter-spacing:0.1em;margin-top:2px;font-family:-apple-system,sans-serif;">kg vol</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── SFR row ──
    stim, fat, sfr = score_sets(today_sets)
    _sc = sfr_color(sfr)
    st.markdown(
        f'<div style="display:flex;gap:10px;margin:0 0 18px 0;">'
        f'<div style="flex:1;background:#f8fafc;border-radius:12px;padding:12px 8px;text-align:center;">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:#9ca3af;font-family:-apple-system,sans-serif;">Stimulus</div>'
        f'<div style="font-size:20px;font-weight:800;color:#1e3a5f;'
        f'font-family:-apple-system,sans-serif;">{stim:,.0f}</div></div>'
        f'<div style="flex:1;background:#f8fafc;border-radius:12px;padding:12px 8px;text-align:center;">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:#9ca3af;font-family:-apple-system,sans-serif;">Fatigue</div>'
        f'<div style="font-size:20px;font-weight:800;color:#1e3a5f;'
        f'font-family:-apple-system,sans-serif;">{fat:,.0f}</div></div>'
        f'<div style="flex:1;background:#f8fafc;border-radius:12px;padding:12px 8px;text-align:center;">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:#9ca3af;font-family:-apple-system,sans-serif;">SFR</div>'
        f'<div style="font-size:20px;font-weight:800;color:{_sc};'
        f'font-family:-apple-system,sans-serif;">{sfr:.2f}</div></div>'
        f'</div>',
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
            f'up to {_fmt(max(float(s["weight_kg"]) for s in grouped[name]))} '
            f'{grouped[name][0].get("unit","kg")}</span></div>'
            for name in order
        )
        st.markdown(rows, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**How did it go?** *(optional)*")
    if st.checkbox("Rate this session", key="rate_it_checkbox"):
        st.select_slider("Energy level",        options=_ENERGY_OPTS,  value="OK",      key="r_energy")
        st.select_slider("Body / fatigue",      options=_FATIGUE_OPTS, value="Normal",  key="r_fatigue")
        st.select_slider("Overall performance", options=_PERFORM_OPTS, value="Average", key="r_perform")

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
                score = round((
                    _ENERGY_OPTS.index(st.session_state.get("r_energy",  "OK"))      + 1 +
                    _FATIGUE_OPTS.index(st.session_state.get("r_fatigue", "Normal"))  + 1 +
                    _PERFORM_OPTS.index(st.session_state.get("r_perform", "Average")) + 1
                ) / 3, 1)
                save_session_rating(st.session_state.session_id, score)
            _end_session()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TOP-LEVEL TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_strength, tab_analytics, tab_cardio = st.tabs(["Strength Training", "Analytics", "Cardio"])


# ══════════════════════════════════════════════════════════════════════════════
# STRENGTH TRAINING
# ══════════════════════════════════════════════════════════════════════════════
with tab_strength:
    exercises = get_exercises()

    # ── front page (no active session) ────────────────────────────────────────
    if st.session_state.session_id is None:
        ft_log, ft_routines, ft_exercises, ft_history = st.tabs(
            ["Log", "Routines", "Exercises", "History"]
        )

        # Log tab ─────────────────────────────────────────────────────────────
        with ft_log:
            st.markdown("# FitnessBuddy")
            st.markdown(
                '<p style="font-size:17px;color:#6b7280;margin-top:-10px;margin-bottom:24px;">'
                "Track every set. See every gain.</p>",
                unsafe_allow_html=True,
            )
            day_type = st.selectbox("Day type", _DAY_TYPES)

            # Routine selector — shows routines matching the chosen day type
            routines = get_routines()
            matching = [r for r in routines
                        if not r.get("day_type") or r["day_type"] == day_type]
            routine_opts = {"Free session (no routine)": None}
            for r in matching:
                routine_opts[r["name"]] = r["id"]

            chosen_label    = st.selectbox("Routine", list(routine_opts.keys()))
            chosen_routine  = routine_opts[chosen_label]

            # Preview selected routine
            if chosen_routine:
                detail = get_routine_detail(chosen_routine)
                if detail:
                    names = [ex["exercises"]["name"] for ex in detail]
                    st.markdown(
                        '<div class="prev-box">'
                        '<div class="prev-title">Routine preview</div>'
                        + "".join(f'<div style="padding:3px 0;font-size:13px;'
                                  f'font-family:-apple-system,sans-serif;color:#374151;">'
                                  f'{i}. {n}</div>'
                                  for i, n in enumerate(names, 1))
                        + '</div>',
                        unsafe_allow_html=True,
                    )

            if st.button("Start Session", type="primary", use_container_width=True):
                st.session_state.session_id       = start_session(day_type)
                st.session_state.day_type         = day_type
                st.session_state.session_start_ts = int(datetime.datetime.now().timestamp())
                st.session_state.routine_id       = chosen_routine
                st.session_state.last_exercise_id = None
                st.session_state.last_sets_cache  = []
                st.session_state.last_set_logged  = None
                st.rerun()

        # Routines tab ────────────────────────────────────────────────────────
        with ft_routines:
            _panel_routines(exercises)

        # Exercises tab ───────────────────────────────────────────────────────
        with ft_exercises:
            _panel_exercises(exercises)

        # History tab ─────────────────────────────────────────────────────────
        with ft_history:
            _panel_history()

    # ── end-session summary ───────────────────────────────────────────────────
    elif st.session_state.confirm_end:
        _show_end_summary()

    # ── active session ────────────────────────────────────────────────────────
    else:
        # Header
        today_date = datetime.date.today().strftime("%A, %d %B %Y")
        col_ban, col_tmr = st.columns([3, 2])
        with col_ban:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1e3a8a 0%,#2563EB 100%);'
                f'border-radius:14px;padding:0 20px;color:white;'
                f'height:{_HEADER_H}px;box-sizing:border-box;'
                f'display:flex;flex-direction:column;justify-content:center;">'
                f'<div style="font-size:22px;font-weight:700;letter-spacing:-0.3px;'
                f'font-family:Lora,Georgia,serif;line-height:1.2;">'
                f'{st.session_state.day_type} Day</div>'
                f'<div style="font-size:12px;opacity:0.8;margin-top:5px;'
                f'font-family:-apple-system,sans-serif;font-weight:500;">{today_date}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_tmr:
            _live_timer(st.session_state.session_start_ts)

        # Last same-day session
        prev_session, prev_sets = get_last_same_day_session(
            st.session_state.day_type, st.session_state.session_id
        )
        if prev_session:
            with st.expander(
                f"Last {st.session_state.day_type} Day — {prev_session.get('date','')}"
            ):
                _render_session_sets(prev_sets)

        st.divider()

        # Two-column layout
        col_main, col_side = st.columns([3, 2])

        # ── RIGHT: Routine / History / Exercises ──────────────────────────────
        with col_side:
            side_routine, side_hist, side_ex = st.tabs(["Routine", "History", "Exercises"])
            with side_routine:
                _panel_routine_checklist(st.session_state.routine_id)
            with side_hist:
                _panel_history()
            with side_ex:
                _panel_exercises(exercises)

        # ── LEFT: Logging ─────────────────────────────────────────────────────
        with col_main:
            st.markdown('<div class="section-label">Exercise</div>', unsafe_allow_html=True)
            emap   = _exercise_map(exercises)
            labels = list(emap.keys())

            def _on_exercise_change() -> None:
                ex_id = emap.get(st.session_state.exercise_label)
                if ex_id is not None:
                    _load_last_sets(ex_id)

            st.selectbox("Exercise", labels, key="exercise_label",
                         on_change=_on_exercise_change, label_visibility="collapsed")
            current_exercise_id = emap.get(
                st.session_state.get("exercise_label", labels[0])
            )
            if current_exercise_id and st.session_state.last_exercise_id != current_exercise_id:
                _load_last_sets(current_exercise_id)

            # Last session recall
            if st.session_state.last_sets_cache:
                date_label = st.session_state.last_date_cache or "last session"
                st.markdown(
                    f'<div class="prev-box">'
                    f'<div class="prev-title">Last session — {date_label}</div>'
                    + "".join(_set_card_html(s["set_number"], s)
                              for s in st.session_state.last_sets_cache)
                    + '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("No previous data for this exercise.")

            st.divider()

            # Weight label + unit toggle
            col_wlabel, col_unit = st.columns([3, 2])
            with col_wlabel:
                st.markdown('<div class="section-label">Weight</div>', unsafe_allow_html=True)
            with col_unit:
                st.radio("unit", ["kg", "lbs"], key="weight_unit",
                         horizontal=True, label_visibility="collapsed")

            # Reserve slot → buttons → fill slot
            weight_slot = st.empty()
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("−5",   use_container_width=True):
                    st.session_state.weight = max(0.0, st.session_state.weight - 5.0)
            with c2:
                if st.button("−2.5", use_container_width=True):
                    st.session_state.weight = max(0.0, st.session_state.weight - 2.5)
            with c3:
                if st.button("+2.5", use_container_width=True):
                    st.session_state.weight += 2.5
            with c4:
                if st.button("+5",   use_container_width=True):
                    st.session_state.weight += 5.0
            with weight_slot:
                st.number_input("Weight", min_value=0.0, step=0.5,
                                key="weight", label_visibility="collapsed")

            # Reps + RIR
            col_r, col_i = st.columns(2)
            with col_r:
                st.markdown('<div class="section-label">Reps</div>', unsafe_allow_html=True)
                st.number_input("Reps", min_value=1, max_value=100, step=1,
                                key="reps", label_visibility="collapsed")
            with col_i:
                st.markdown('<div class="section-label">RIR</div>', unsafe_allow_html=True)
                st.number_input("RIR", min_value=0, max_value=10, step=1,
                                key="rir", label_visibility="collapsed")

            # Add / Duplicate
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
                        last["weight_kg"], last["reps"], last["rir"],
                        last.get("unit", "kg"),
                    )
                    st.rerun()

            st.divider()

            # Today's log
            today = get_today_sets(st.session_state.session_id)
            if today:
                st.markdown('<div class="section-label">Today\'s Log</div>', unsafe_allow_html=True)
                _render_session_sets(today)
            else:
                st.markdown(
                    '<p style="color:#d1d5db;font-size:14px;text-align:center;padding:16px 0;">'
                    "No sets yet — add your first set above.</p>",
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("End Session", use_container_width=True):
                st.session_state.confirm_end    = True
                st.session_state.session_end_ts = int(datetime.datetime.now().timestamp())
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:

    def _lbs_to_kg(w: float) -> float:
        return w * 0.453592

    def _build_analytics_df() -> pd.DataFrame | None:
        raw = get_all_sets_for_analytics()
        if not raw:
            return None
        rows = []
        for s in raw:
            ex   = s.get("exercises") or {}
            sess = s.get("sessions")  or {}
            date = sess.get("date")
            if not date:
                continue
            w_raw = float(s["weight_kg"] or 0)
            unit  = s.get("unit", "kg")
            w_kg  = _lbs_to_kg(w_raw) if unit == "lbs" else w_raw
            reps  = int(s["reps"] or 0)
            rows.append({
                "date":         pd.to_datetime(date),
                "exercise":     ex.get("name", "Unknown"),
                "muscle_group": ex.get("muscle_group") or "Other",
                "category":     ex.get("category") or "compound",
                "sfr_rating":   float(ex.get("sfr_rating") or 3.0),
                "weight_kg":    w_kg,
                "reps":         reps,
                "rir":          s.get("rir"),
                "unit":         unit,
                "e1rm":         w_kg * (1 + reps / 30) if reps > 0 else w_kg,
            })
        if not rows:
            return None
        return pd.DataFrame(rows)

    _PLOTLY_LAYOUT = dict(
        font_family  = "-apple-system, BlinkMacSystemFont, sans-serif",
        paper_bgcolor= "white",
        plot_bgcolor = "white",
        margin       = dict(l=16, r=16, t=48, b=16),
        xaxis        = dict(showgrid=False, linecolor="#e5e7eb"),
        yaxis        = dict(gridcolor="#f3f4f6", linecolor="#e5e7eb"),
        legend       = dict(orientation="h", y=-0.2),
    )

    an_prog, an_vol, an_body = st.tabs(["Progress", "Volume", "Body"])

    # ── PROGRESS ──────────────────────────────────────────────────────────────
    with an_prog:
        df = _build_analytics_df()
        if df is None:
            st.info("Log some workouts first — your progress charts will appear here.")
        else:
            exercise_names = sorted(df["exercise"].unique().tolist())
            sel_ex = st.selectbox("Exercise", exercise_names, key="an_exercise")
            ex_df  = df[df["exercise"] == sel_ex].copy()

            max_weight = ex_df["weight_kg"].max()
            best_e1rm  = ex_df["e1rm"].max()
            n_sets     = len(ex_df)
            n_sessions = ex_df["date"].dt.date.nunique()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Best weight",  f"{_fmt(round(max_weight, 1))} kg")
            c2.metric("Best E1RM",    f"{_fmt(round(best_e1rm, 1))} kg")
            c3.metric("Total sets",   n_sets)
            c4.metric("Sessions",     n_sessions)

            # E1RM — all sets as individual dots, date-only on x-axis
            plot_df = ex_df.copy()
            plot_df["date"] = plot_df["date"].dt.date
            plot_df = plot_df.rename(columns={"e1rm": "E1RM (kg)"})

            fig = px.scatter(
                plot_df, x="date", y="E1RM (kg)",
                title=f"Estimated 1-Rep Max — {sel_ex}",
                labels={"date": ""},
                color_discrete_sequence=["#2563EB"],
            )
            fig.update_traces(marker_size=9, marker_opacity=0.75)
            fig.update_layout(**_PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

            # Best-weight over time (raw top set per day)
            daily_w = (
                ex_df.groupby(ex_df["date"].dt.date)["weight_kg"]
                .max()
                .reset_index()
            )
            daily_w.columns = ["date", "Weight (kg)"]
            daily_w["date"] = pd.to_datetime(daily_w["date"])

            fig2 = px.bar(
                daily_w, x="date", y="Weight (kg)",
                title=f"Top Weight Per Session — {sel_ex}",
                color_discrete_sequence=["#93c5fd"],
            )
            fig2.update_layout(**_PLOTLY_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

    # ── VOLUME ────────────────────────────────────────────────────────────────
    with an_vol:
        df = _build_analytics_df()
        if df is None:
            st.info("Log some workouts first — your volume charts will appear here.")
        else:
            vol_df        = df.copy()
            vol_df["week"]= vol_df["date"].dt.to_period("W").apply(
                lambda p: p.start_time
            )
            vol_df["tonnage"] = vol_df["weight_kg"] * vol_df["reps"]

            # Stacked bar: weekly tonnage by muscle group
            weekly = (
                vol_df.groupby(["week", "muscle_group"])["tonnage"]
                .sum()
                .reset_index()
            )
            weekly.columns = ["Week", "Muscle group", "Tonnage (kg)"]

            fig3 = px.bar(
                weekly, x="Week", y="Tonnage (kg)", color="Muscle group",
                barmode="stack",
                title="Weekly Training Volume by Muscle Group",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig3.update_layout(**_PLOTLY_LAYOUT)
            st.plotly_chart(fig3, use_container_width=True)

            # Weekly sets count (simple line)
            weekly_sets = (
                vol_df.groupby("week")
                .size()
                .reset_index(name="Sets")
            )
            weekly_sets.columns = ["Week", "Sets"]

            fig4 = px.line(
                weekly_sets, x="Week", y="Sets",
                title="Weekly Total Sets",
                markers=True,
                color_discrete_sequence=["#2563EB"],
            )
            fig4.update_traces(line_width=2.5, marker_size=7)
            fig4.update_layout(**_PLOTLY_LAYOUT)
            st.plotly_chart(fig4, use_container_width=True)

            # Weekly stimulus vs accumulated fatigue
            vol_df["stimulus"] = vol_df.apply(
                lambda r: set_stimulus(
                    r["weight_kg"], r["reps"], r["rir"],
                    r["category"], r["sfr_rating"]
                ), axis=1
            )
            vol_df["fatigue"] = vol_df.apply(
                lambda r: set_fatigue(
                    r["weight_kg"], r["reps"], r["rir"],
                    r["muscle_group"], r["category"]
                ), axis=1
            )
            weekly_sf = (
                vol_df.groupby("week")
                .agg(Stimulus=("stimulus", "sum"), Fatigue=("fatigue", "sum"))
                .reset_index()
            )
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=weekly_sf["week"], y=weekly_sf["Stimulus"].round(0),
                name="Stimulus", mode="lines+markers",
                line=dict(color="#2563EB", width=2.5), marker=dict(size=7),
            ))
            fig5.add_trace(go.Scatter(
                x=weekly_sf["week"], y=weekly_sf["Fatigue"].round(0),
                name="Fatigue", mode="lines+markers",
                line=dict(color="#ef4444", width=2.5), marker=dict(size=7),
            ))
            fig5.update_layout(
                title="Weekly Stimulus vs Fatigue",
                yaxis_title="Score",
                **_PLOTLY_LAYOUT,
            )
            st.plotly_chart(fig5, use_container_width=True)

    # ── BODY ──────────────────────────────────────────────────────────────────
    with an_body:
        bw_records = get_bodyweight_history()

        # Log today
        st.markdown('<div class="section-label">Log today\'s weight</div>',
                    unsafe_allow_html=True)
        today_str = datetime.date.today().isoformat()
        existing  = next((r for r in bw_records if r["date"] == today_str), None)

        with st.form("bw_form", clear_on_submit=False):
            bw_val = st.number_input(
                "Weight (kg)", min_value=20.0, max_value=300.0, step=0.1,
                value=float(existing["weight_kg"]) if existing else 70.0,
                key="bw_input",
            )
            if st.form_submit_button(
                "Update" if existing else "Log weight",
                use_container_width=True, type="primary"
            ):
                log_bodyweight(bw_val)
                st.success(f"Logged {_fmt(bw_val)} kg for today.")
                st.rerun()

        if not bw_records:
            st.caption("No bodyweight data yet — log your first entry above.")
        else:
            bw_df = pd.DataFrame(bw_records)
            bw_df["date"] = pd.to_datetime(bw_df["date"])
            bw_df["weight_kg"] = bw_df["weight_kg"].astype(float)

            # Rolling 7-day average
            bw_df = bw_df.sort_values("date")
            bw_df["7d avg"] = bw_df["weight_kg"].rolling(7, min_periods=1).mean()

            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=bw_df["date"], y=bw_df["weight_kg"],
                mode="markers", name="Daily",
                marker=dict(color="#93c5fd", size=7),
            ))
            fig5.add_trace(go.Scatter(
                x=bw_df["date"], y=bw_df["7d avg"].round(2),
                mode="lines", name="7-day avg",
                line=dict(color="#2563EB", width=2.5),
            ))
            fig5.update_layout(
                title="Bodyweight Trend",
                yaxis_title="kg",
                **_PLOTLY_LAYOUT,
            )
            st.plotly_chart(fig5, use_container_width=True)

            # Stats
            latest = bw_df["weight_kg"].iloc[-1]
            lo     = bw_df["weight_kg"].min()
            hi     = bw_df["weight_kg"].max()
            s1, s2, s3 = st.columns(3)
            s1.metric("Latest",  f"{_fmt(round(latest, 1))} kg")
            s2.metric("Lowest",  f"{_fmt(round(lo, 1))} kg")
            s3.metric("Highest", f"{_fmt(round(hi, 1))} kg")


# ══════════════════════════════════════════════════════════════════════════════
# CARDIO TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_cardio:
    st.markdown("### Cardio")
    st.info("Cardio tracking coming soon — runs, cycles, and rowing sessions.")
