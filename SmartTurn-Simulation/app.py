# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib import transforms
import matplotlib.patches as mpatches
from PIL import Image

# ----------------------------- Page Setup & Style -----------------------------
st.set_page_config(page_title="SmartTurn Demo", layout="wide")

st.markdown("""
<style>
:root { --radius: 14px; }
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1250px; }
section[data-testid="stSidebar"] .block-container { padding: 1.0rem .8rem; }
h1, h2, h3 { letter-spacing: .3px; }
.smart-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
              border-radius: var(--radius); padding: 1.0rem 1.15rem; }
.stButton>button, .stDownloadButton>button {
  border-radius: 12px; padding: .58rem 1rem; font-weight: 600;
}
div[data-testid="stDataFrame"] { border-radius: var(--radius); overflow: hidden; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent
BED_PHOTO = (BASE_DIR / "assets" / "bed_photo.png").resolve()  # صورة التخت الحقيقي

# ----------------------------- State Helpers ---------------------------------
def init_state():
    s = st.session_state
    if "current_time" not in s:
        s.current_time = datetime.now().replace(second=0, microsecond=0)
    if "protocol_interval" not in s:
        s.protocol_interval = 120
    if "protocol_angle" not in s:
        s.protocol_angle = 15
    if "sequence" not in s:
        s.sequence = ["RIGHT", "LEFT", "BACK"]
    if "seq_index" not in s:
        s.seq_index = 0
    if "next_change_at" not in s:
        s.next_change_at = s.current_time + timedelta(minutes=s.protocol_interval)
    if "grace_minutes" not in s:
        s.grace_minutes = 5
    if "log" not in s:
        s.log = pd.DataFrame(columns=["timestamp","event","side","angle","mode","status"])
    if "last_side" not in s:
        s.last_side = "BACK"
    if "last_angle" not in s:
        s.last_angle = 0

def rotate_sequence():
    st.session_state.seq_index = (st.session_state.seq_index + 1) % len(st.session_state.sequence)

def add_log(ts, event, side, angle, mode, status="OK"):
    row = {
        "timestamp": ts.strftime("%Y-%m-%d %H:%M"),
        "event": event, "side": side, "angle": angle, "mode": mode, "status": status
    }
    st.session_state.log = pd.concat([st.session_state.log, pd.DataFrame([row])], ignore_index=True)
    st.session_state.last_side = side
    st.session_state.last_angle = angle

def apply_auto_change():
    side = st.session_state.sequence[st.session_state.seq_index]
    angle = st.session_state.protocol_angle
    add_log(st.session_state.current_time, "Change position", side, angle, "AUTO", "OK")
    rotate_sequence()
    st.session_state.next_change_at = st.session_state.current_time + timedelta(
        minutes=st.session_state.protocol_interval
    )

def apply_manual_change(side, angle):
    add_log(st.session_state.current_time, "Manual override", side, angle, "MANUAL", "OK")

# ----------------------------- Photo (baseline) -------------------------------
def show_photo_centered(path: Path, max_width: int = 820):
    """يعرض صورة التخت الحقيقي عندما الزاوية = 0°."""
    if not path.exists():
        st.warning(f"Photo not found: {path}")
        return
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    tw = min(max_width, w)
    th = int(h * (tw / w))
    img = img.resize((tw, th))
    a, b, c = st.columns([1, 2, 1])
    with b:
        st.image(img)

# ----------------------------- Schematic Drawing ------------------------------
def draw_bed(angle_deg, side, *, exaggeration=2, show_guides=True):
    """
    رسم تخطيطي فقط (لا خلفية ولا صور فرشة):
      - RIGHT/LEFT: ميل الإطار كاملًا.
      - BACK: رفع مسند الظهر فقط + مؤشرات.
    """
    vis_angle = angle_deg * exaggeration

    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    ax.set_xlim(-2.6, 2.6); ax.set_ylim(-2.6, 2.6)
    ax.set_aspect('equal'); ax.axis('off')

    cx, cy = 0.0, 0.0
    bed_w, bed_h = 3.2, 1.2
    mat_w, mat_h = 3.0, 1.0

    frame_rot = 0
    backrest_angle = 0
    if side == "RIGHT":
        frame_rot = +vis_angle
    elif side == "LEFT":
        frame_rot = -vis_angle
    elif side == "BACK":
        backrest_angle = vis_angle

    T = transforms.Affine2D().rotate_deg_around(cx, cy, frame_rot)

    # Bed frame
    frame = Rectangle((cx - bed_w/2, cy - bed_h/2), bed_w, bed_h,
                      linewidth=2.2, edgecolor='#6c757d', facecolor='#eceff1', zorder=1)
    frame.set_transform(T + ax.transData); ax.add_patch(frame)

    # Mattress (simple rectangle)
    mattress = Rectangle((cx - mat_w/2, cy - mat_h/2), mat_w, mat_h,
                         linewidth=1.6, edgecolor='#5dade2', facecolor='#bfe3fa', zorder=2)
    mattress.set_transform(T + ax.transData); ax.add_patch(mattress)

    # Pillow
    pillow = Rectangle((cx - mat_w/2 + 0.12, cy + mat_h/2 - 0.36), 0.65, 0.26,
                       linewidth=1.1, edgecolor='#85c1e9', facecolor='white', zorder=3)
    pillow.set_transform(T + ax.transData); ax.add_patch(pillow)

    # Wheels
    for (wx, wy) in [(-bed_w/2 + 0.25, -bed_h/2 - 0.15),
                     ( bed_w/2 - 0.25, -bed_h/2 - 0.15),
                     (-bed_w/2 + 0.25,  bed_h/2 + 0.15),
                     ( bed_w/2 - 0.25,  bed_h/2 + 0.15)]:
        wheel = Circle((cx + wx, cy + wy), 0.12, color='black', zorder=0)
        wheel.set_transform(T + ax.transData); ax.add_patch(wheel)

    # Backrest at top edge
    back_w, back_h = 1.7, 0.18
    back_x = cx - back_w/2
    back_y = cy + bed_h/2

    if side == "BACK" and backrest_angle != 0:
        px, py = (T + ax.transData).transform((back_x + back_w/2, back_y))
        T_back = transforms.Affine2D().rotate_deg_around(px, py, -backrest_angle)
        back_tr = T_back + ax.transData
    else:
        back_tr = T + ax.transData

    backrest = Rectangle((back_x, back_y), back_w, back_h,
                         linewidth=2.0, edgecolor='#1f78b4', facecolor='#79b7f2', zorder=4)
    backrest.set_transform(back_tr); ax.add_patch(backrest)

    hinge = Circle((T + ax.transData).transform((back_x + back_w/2, back_y)), 0.06,
                   color='#1f78b4', zorder=5, transform=None)
    ax.add_artist(hinge)

    # Guides
    if side == "BACK" and show_guides:
        px, py = (T + ax.transData).transform((back_x + back_w/2, back_y))
        arc = mpatches.Arc((px, py), 1.2, 1.2, angle=0,
                           theta1=0, theta2=max(1, backrest_angle),
                           linewidth=2.2, color='#ff6b6b', zorder=6)
        ax.add_patch(arc)
        end_angle = np.deg2rad(backrest_angle)
        ax.annotate("", xy=(px + 0.6*np.cos(end_angle), py + 0.6*np.sin(end_angle)),
                    xytext=(px + 0.42*np.cos(end_angle), py + 0.42*np.sin(end_angle)),
                    arrowprops=dict(arrowstyle="->", lw=2, color='#ff6b6b'), zorder=6)
        ax.text(px + 0.75, py + 0.65, f"Backrest ↑ {int(backrest_angle)}°",
                ha='left', va='center', fontsize=11.5, color='#ff6b6b', zorder=6)

    ax.text(0, -2.25,
            f"Side: {side}  •  Display angle: {int(vis_angle)}°  (original: {angle_deg}°)",
            ha='center', va='center', fontsize=11.5)

    st.pyplot(fig)

# ----------------------------- UI --------------------------------------------
init_state()
st.title("SmartTurn – סימולציית מיטה חכמה (Demo)")

with st.sidebar:
    st.header("Protocol")
    st.session_state.protocol_interval = st.number_input(
        "Interval (minutes)", 10, 480, st.session_state.protocol_interval, 5
    )
    st.session_state.protocol_angle = st.slider(
        "Angle (degrees)", 5, 30, st.session_state.protocol_angle, 1
    )
    seq = st.multiselect("Sequence (order of sides)", ["RIGHT","LEFT","BACK"],
                         default=st.session_state.sequence)
    if seq:
        st.session_state.sequence = seq
        if st.session_state.seq_index >= len(seq):
            st.session_state.seq_index = 0

    st.session_state.grace_minutes = st.number_input(
        "Grace period for lateness (minutes)", 0, 60, st.session_state.grace_minutes, 1
    )

    if st.button("Reset Protocol Timer", use_container_width=True):
        st.session_state.next_change_at = st.session_state.current_time + timedelta(
            minutes=st.session_state.protocol_interval
        )
        st.success("Protocol timer reset.")

    st.markdown("---")
    st.header("Display")
    exaggeration = st.slider("Display exaggeration ×", 1, 4, 2, 1)
    show_guides  = st.checkbox("Show backrest guides", True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("Bed Simulation")
    side_preview = st.session_state.sequence[st.session_state.seq_index]
    st.markdown(
        f"**Current simulated time:** {st.session_state.current_time.strftime('%Y-%m-%d %H:%M')}  \n"
        f"**Next change due at:** {st.session_state.next_change_at.strftime('%Y-%m-%d %H:%M')}  \n"
        f"**Upcoming side:** {side_preview} • **Angle:** {st.session_state.protocol_angle}°"
    )

    late = st.session_state.current_time > (
        st.session_state.next_change_at + timedelta(minutes=st.session_state.grace_minutes)
    )
    due = st.session_state.current_time >= st.session_state.next_change_at
    if late:
        st.error("Change is LATE! (past due + grace)")
    elif due:
        st.warning("Change is due now.")

    angle_now = st.session_state.last_angle
    side_now  = st.session_state.last_side

    st.markdown('<div class="smart-card">', unsafe_allow_html=True)
    # Auto logic: إذا الزاوية صفر → صورة التخت الحقيقي، غير ذلك → الرسم التخطيطي
    if angle_now == 0:
        show_photo_centered(BED_PHOTO, max_width=820)
    else:
        draw_bed(angle_now, side_now, exaggeration=exaggeration, show_guides=show_guides)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Advance Simulated Time")
    c1, c2, c3 = st.columns(3)
    if c1.button("Advance 1 min", use_container_width=True):
        st.session_state.current_time += timedelta(minutes=1)
    if c2.button("Advance 10 min", use_container_width=True):
        st.session_state.current_time += timedelta(minutes=10)
    if c3.button("Advance 60 min", use_container_width=True):
        st.session_state.current_time += timedelta(minutes=60)

    if st.session_state.current_time >= st.session_state.next_change_at:
        apply_auto_change()
        st.success(f"Auto change executed → {st.session_state.last_side} at {st.session_state.last_angle}°")

with col2:
    st.subheader("Manual Override")
    side = st.selectbox("Side", ["RIGHT","LEFT","BACK"])
    angle = st.slider("Manual angle", 5, 30, value=10, step=1)
    if st.button("Apply Manual Override", use_container_width=True):
        apply_manual_change(side, angle)
        st.info(f"Manual change applied → {side} at {angle}°")
        st.rerun()

    st.markdown("---")
    st.subheader("Event Log")
    st.markdown('<div class="smart-card">', unsafe_allow_html=True)
    st.dataframe(st.session_state.log, use_container_width=True, height=330)
    st.markdown('</div>', unsafe_allow_html=True)

    if not st.session_state.log.empty:
        csv = st.session_state.log.to_csv(index=False).encode("utf-8")
        st.download_button("Export Log as CSV", data=csv,
                           file_name="smartturn_log.csv", mime="text/csv",
                           use_container_width=True)

st.caption("Demo only. No hardware. All times simulated.")
