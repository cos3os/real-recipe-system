import streamlit as st
import json
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.scaling import scale_recipe

st.set_page_config(page_title="조리 가이드 | RefrigerAI", layout="wide")

# ── 데이터 체크 ──────────────────────────────────────
recipe_meta = st.session_state.get("selected_recipe", {})
if not recipe_meta:
    st.warning("추천 결과에서 레시피를 선택해주세요.")
    if st.button("← 추천 결과로", type="primary"):
        st.switch_page("pages/4_추천결과.py")
    st.stop()

# ── JSON 로드 ────────────────────────────────────────
recipe_json_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "structured_steps",
    f'{recipe_meta["recipe_id"]}_{recipe_meta["recipe_name"].replace(" ", "")}.json',
)

# fallback: 공백 포함 버전도 시도
if not os.path.exists(recipe_json_path):
    recipe_json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "structured_steps", "137_된장두부찌개.json",
    )

if not os.path.exists(recipe_json_path):
    st.error(f"레시피 JSON을 찾을 수 없습니다: {recipe_json_path}")
    st.stop()

with open(recipe_json_path, "r", encoding="utf-8") as f:
    recipe_data = json.load(f)

# ── CSS ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.step-card { background: #fafafa; border-left: 4px solid #ff6b35; border-radius: 8px; padding: 20px 24px; margin-bottom: 16px; }
.step-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.step-number { background: #ff6b35; color: white; font-weight: 700; font-size: 14px; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.step-action { font-size: 18px; font-weight: 700; color: #1a1a1a; }
.step-detail { font-size: 15px; color: #333; margin-bottom: 12px; line-height: 1.6; }
.meta-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.meta-chip { font-size: 13px; padding: 4px 12px; border-radius: 20px; font-weight: 500; }
.chip-heat-강 { background: #ffe0e0; color: #c62828; }
.chip-heat-중 { background: #fff3e0; color: #e65100; }
.chip-heat-약 { background: #e8f5e9; color: #2e7d32; }
.chip-heat-없음 { background: #f5f5f5; color: #757575; }
.chip-time { background: #e3f2fd; color: #1565c0; }
.chip-condition { background: #f3e5f5; color: #6a1b9a; }
.tip-box { background: #fff8e1; border-radius: 6px; padding: 10px 14px; font-size: 13px; color: #5d4037; margin-top: 8px; }
.tip-box::before { content: "💡 "; }
.tool-tag { display: inline-block; font-size: 12px; background: #eceff1; color: #546e7a; padding: 2px 10px; border-radius: 12px; margin-right: 6px; margin-top: 6px; }
.time-banner { background: linear-gradient(135deg, #ff6b35, #ff8a5c); color: white; border-radius: 12px; padding: 20px 28px; text-align: center; }
.time-banner-label { font-size: 14px; opacity: 0.9; }
.time-banner-value { font-size: 36px; font-weight: 700; margin-top: 4px; }
.nutrition-bar { background: #f0f4ff; border: 1px solid #c5cae9; border-radius: 10px; padding: 12px 18px; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.nutrition-item { text-align: center; }
.nutrition-item .label { font-size: 11px; color: #888; }
.nutrition-item .value { font-size: 16px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── 페이지 시작 ──────────────────────────────────────
st.title(f'👨‍🍳 {recipe_data["recipe_name"]}')
st.caption(f'{recipe_data["method"]} · 기준 {recipe_data["base_servings"]}인분 · 약 {recipe_data["total_time_min"]}분')

# ── 영양 요약 바 ─────────────────────────────────────
r = recipe_meta
st.markdown(
    f'<div class="nutrition-bar">'
    f'<div class="nutrition-item"><div class="label">칼로리</div><div class="value">{r["kcal"]} kcal</div></div>'
    f'<div class="nutrition-item"><div class="label">단백질</div><div class="value">{r["protein_g"]}g</div></div>'
    f'<div class="nutrition-item"><div class="label">지방</div><div class="value">{r["fat_g"]}g</div></div>'
    f'<div class="nutrition-item"><div class="label">탄수화물</div><div class="value">{r["carb_g"]}g</div></div>'
    f'<div class="nutrition-item"><div class="label">예상 비용</div><div class="value">{r["estimated_cost"]:,}원</div></div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── 인분 조절 + 총 시간 ──────────────────────────────
col_srv, col_time = st.columns([1, 1])

with col_srv:
    target_servings = st.slider(
        "🍽️ 인분 조절", 1, 8,
        recipe_data["base_servings"],
    )

result = scale_recipe(recipe_data, target_servings)
total_scaled = result["scaled_total_min"]

with col_time:
    st.markdown(
        f'<div class="time-banner">'
        f'<div class="time-banner-label">{target_servings}인분 예상 조리시간</div>'
        f'<div class="time-banner-value">약 {math.ceil(total_scaled)}분</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── 진행률 ───────────────────────────────────────────
total_steps = len(recipe_data["steps"])

if "completed_steps" not in st.session_state:
    st.session_state.completed_steps = set()
completed = st.session_state.completed_steps

progress = len(completed) / total_steps if total_steps > 0 else 0
st.progress(progress, text=f"진행률: {len(completed)}/{total_steps} 단계 완료")

# ── 스텝 카드 렌더링 ─────────────────────────────────
for s in recipe_data["steps"]:
    step_num = s["step_number"]

    # 스케일된 시간
    scaled_info = next(
        (x for x in result["steps"] if x["step_number"] == step_num),
        None,
    )
    scaled_time = scaled_info["scaled_time_min"] if scaled_info else s["estimated_time_min"]
    time_str = f"{int(scaled_time)}분" if scaled_time == int(scaled_time) else f"{scaled_time:.1f}분"

    # 메타 칩
    heat = s.get("heat_level", "없음")
    meta_chips = (
        f'<span class="meta-chip chip-heat-{heat}">🔥 {heat}</span>'
        f'<span class="meta-chip chip-time">⏱ {time_str}</span>'
    )
    if s.get("end_condition"):
        meta_chips += f'<span class="meta-chip chip-condition">🎯 {s["end_condition"]}</span>'

    # 도구
    tools_html = ""
    if s.get("tools_used"):
        tools_html = "".join(
            f'<span class="tool-tag">🔧 {t}</span>' for t in s["tools_used"]
        )

    # 팁
    tip_html = ""
    if s.get("technique_note"):
        tip_html = f'<div class="tip-box">{s["technique_note"]}</div>'

    # 완료 상태
    is_done = step_num in completed
    border_color = "#4caf50" if is_done else "#ff6b35"
    opacity = "opacity: 0.6;" if is_done else ""
    icon = "✓" if is_done else step_num

    # 카드 렌더
    card_html = (
        f'<div class="step-card" style="border-left-color: {border_color}; {opacity}">'
        f'<div class="step-header">'
        f'<div class="step-number" style="background: {border_color};">{icon}</div>'
        f'<div class="step-action">{s["action"]} — {s["target"]}</div>'
        f'</div>'
        f'<div class="step-detail">{s["detail"]}</div>'
        f'<div class="meta-row">{meta_chips}</div>'
        f'{tools_html}'
        f'{tip_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # 체크박스 + 타이머
    col_check, col_timer = st.columns([1, 1])

    with col_check:
        checked = st.checkbox(
            f"Step {step_num} 완료",
            value=is_done,
            key=f"done_{step_num}",
        )
        if checked:
            completed.add(step_num)
        else:
            completed.discard(step_num)
        st.session_state.completed_steps = completed

    with col_timer:
        timer_seconds = int(scaled_time * 60)
        mm = timer_seconds // 60
        ss = timer_seconds % 60

        with st.expander(f"⏱ 타이머 ({time_str})"):
            timer_html = (
                f'<div style="font-family:Noto Sans KR,sans-serif; text-align:center; padding:8px;">'
                f'<div id="d-{step_num}" style="font-size:42px; font-weight:700; color:#1565c0;">'
                f'{mm:02d}:{ss:02d}'
                f'</div>'
                f'<div style="display:flex; gap:6px; justify-content:center; margin-top:6px;">'
                f'<button onclick="sT{step_num}()" style="padding:6px 16px; border:none; background:#ff6b35; color:white; border-radius:6px; cursor:pointer;">▶ 시작</button>'
                f'<button onclick="pT{step_num}()" style="padding:6px 16px; border:none; background:#eceff1; border-radius:6px; cursor:pointer;">⏸ 정지</button>'
                f'<button onclick="rT{step_num}()" style="padding:6px 16px; border:none; background:#eceff1; border-radius:6px; cursor:pointer;">↺ 리셋</button>'
                f'</div>'
                f'</div>'
                f'<script>'
                f'var r{step_num}={timer_seconds},i{step_num}=null;'
                f'function sT{step_num}(){{if(i{step_num})return;i{step_num}=setInterval(function(){{if(r{step_num}<=0){{clearInterval(i{step_num});i{step_num}=null;document.getElementById("d-{step_num}").style.color="#c62828";document.getElementById("d-{step_num}").innerText="완료!";return;}}r{step_num}--;var m=Math.floor(r{step_num}/60),s=r{step_num}%60;document.getElementById("d-{step_num}").innerText=String(m).padStart(2,"0")+":"+String(s).padStart(2,"0");}},1000);}}'
                f'function pT{step_num}(){{clearInterval(i{step_num});i{step_num}=null;}}'
                f'function rT{step_num}(){{clearInterval(i{step_num});i{step_num}=null;r{step_num}={timer_seconds};var m=Math.floor({timer_seconds}/60),s={timer_seconds}%60;document.getElementById("d-{step_num}").style.color="#1565c0";document.getElementById("d-{step_num}").innerText=String(m).padStart(2,"0")+":"+String(s).padStart(2,"0");}}'
                f'</script>'
            )
            st.components.v1.html(timer_html, height=120)

# ── 조리 완료 ────────────────────────────────────────
if len(completed) == total_steps:
    st.balloons()
    st.success("🎉 조리 완료! CookHistory에 기록됩니다.")

    today = st.session_state.get("today_meals", {})
    if today:
        consumed = today.get("consumed", {})
        new_kcal = consumed.get("kcal", 0) + recipe_meta["kcal"]
        new_protein = consumed.get("protein", 0) + recipe_meta["protein_g"]
        st.info(
            f'오늘 총 섭취: {new_kcal:.0f} kcal · 단백질 {new_protein:.1f}g '
            f'(TDEE {st.session_state.get("user_profile", {}).get("tdee", "?")} kcal)'
        )

# ── 푸터 & 네비게이션 ────────────────────────────────
st.divider()
st.caption(
    f'🔬 시간 스케일링: t_scaled = t_base × (인분비)^α | '
    f'기준 {recipe_data["base_servings"]}인분 → {target_servings}인분'
)

col_back, col_home = st.columns(2)

with col_back:
    if st.button("← 추천 결과", use_container_width=True):
        st.switch_page("pages/4_추천결과.py")

with col_home:
    if st.button("🏠 처음으로", use_container_width=True):
        st.session_state.completed_steps = set()
        st.switch_page("app.py")