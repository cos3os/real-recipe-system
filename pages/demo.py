import streamlit as st
import json
import math
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.scaling import scale_recipe

st.set_page_config(page_title="RefrigerAI Demo", layout="wide")

# 섹션 2: TDEE 계산 함수 (database.py의 Mifflin-St Jeor 공식 그대로)
def calc_tdee(gender, weight, height, age, activity, goal):
    if gender == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = bmr * activity
    if goal == "체중감량":
        tdee *= 0.85
    elif goal == "근육증가":
        tdee *= 1.1
    return round(tdee, 1)

def calc_protein(weight, goal, meal_fraction=0.35):
    coeff = {"근육증가": 2.0, "체중감량": 1.8, "유지": 1.4}.get(goal, 1.4)
    return round(weight * coeff * meal_fraction, 1)

# 섹션 3: 된장두부찌개 mock 데이터
MOCK_RECIPE = {
    "recipe_id": 137,
    "recipe_name": "된장두부찌개",
    "method": "끓이기",
    "dish_type": "찌개",
    "base_servings": 4,
    "total_time_min": 25,
    "kcal": 285.4,
    "protein_g": 18.2,
    "fat_g": 11.3,
    "carb_g": 28.7,
    "estimated_cost": 3200,
    # KG 엣지: 이 레시피가 REQUIRES하는 재료들
    "required_ingredients": ["두부", "돼지고기", "김치", "대파", "청양고추", "홍고추"],
    "required_seasonings": ["된장", "고춧가루", "다진마늘"],
    "required_tools": ["냄비", "믹서기", "칼/도마"],
}

# 전체 선택 가능 재료 목록 (시연용 축소판)
ALL_INGREDIENTS = [
    "두부", "돼지고기", "김치", "대파", "청양고추", "홍고추",
    "애호박", "양파", "표고버섯", "닭고기", "달걀", "감자",
    "당근", "팽이버섯", "청경채", "시금치", "콩나물",
    "소고기", "오징어", "멥쌀밥", "고구마", "브로콜리",
]

ALL_SEASONINGS = ["된장", "고춧가루", "다진마늘", "간장", "참기름",
                  "소금", "고추장", "식용유", "설탕", "후추"]

ALL_TOOLS = ["냄비", "프라이팬", "전자레인지", "오븐", "믹서기", "칼/도마"]

# 섹션 4: CSS (cooking_guide.py 기반 + 추가 스타일)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.profile-card {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white; border-radius: 16px;
    padding: 24px 28px; margin-bottom: 20px;
}
.profile-card h2 { margin: 0 0 8px 0; font-size: 22px; }
.profile-card .stat { font-size: 14px; opacity: 0.9; }

.recipe-card {
    background: white; border: 2px solid #ff6b35;
    border-radius: 16px; padding: 24px; margin: 16px 0;
}
.recipe-card-title { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.recipe-card-sub { font-size: 13px; color: #888; }

.reason-badge {
    display: inline-block; font-size: 12px; font-weight: 500;
    padding: 4px 12px; border-radius: 20px; margin: 4px 4px 4px 0;
}
.badge-nutrition { background: #e8f5e9; color: #2e7d32; }
.badge-cost { background: #e3f2fd; color: #1565c0; }
.badge-expiry { background: #fff3e0; color: #e65100; }
.badge-match { background: #f3e5f5; color: #6a1b9a; }

.ingr-check { font-size: 15px; margin: 4px 0; }
.ingr-owned { color: #2e7d32; }
.ingr-missing { color: #c62828; }

.step-card {
    background: #fafafa; border-left: 4px solid #ff6b35;
    border-radius: 8px; padding: 20px 24px; margin-bottom: 16px;
}
.step-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.step-number {
    background: #ff6b35; color: white; font-weight: 700; font-size: 14px;
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
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

.tip-box {
    background: #fff8e1; border-radius: 6px;
    padding: 10px 14px; font-size: 13px; color: #5d4037; margin-top: 8px;
}
.tip-box::before { content: "💡 "; }

.tool-tag {
    display: inline-block; font-size: 12px; background: #eceff1;
    color: #546e7a; padding: 2px 10px; border-radius: 12px;
    margin-right: 6px; margin-top: 6px;
}

.time-banner {
    background: linear-gradient(135deg, #ff6b35, #ff8a5c);
    color: white; border-radius: 12px;
    padding: 20px 28px; text-align: center;
}
.time-banner-label { font-size: 14px; opacity: 0.9; }
.time-banner-value { font-size: 36px; font-weight: 700; margin-top: 4px; }

.pipeline-step {
    background: #f8f9fa; border-radius: 8px;
    padding: 12px 16px; margin: 8px 0; font-size: 14px;
}
.pipeline-done { border-left: 4px solid #4caf50; }
.pipeline-active { border-left: 4px solid #ff6b35; }
</style>
""", unsafe_allow_html=True)

# 섹션 5: session_state 초기화
if "step" not in st.session_state:
    st.session_state.step = 1
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {}
if "fridge" not in st.session_state:
    st.session_state.fridge = {}

# 섹션 6: Step 1 — 내 정보 입력
if st.session_state.step == 1:
    st.title("🍳 RefrigerAI — 내 정보 입력")
    st.caption("입력한 정보를 기반으로 TDEE와 영양 목표를 자동 계산합니다.")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("기본 정보")
        gender = st.radio("성별", ["male", "female"], format_func=lambda x: "남성" if x == "male" else "여성", horizontal=True)
        age = st.number_input("나이", min_value=15, max_value=80, value=24)
        height = st.number_input("키 (cm)", min_value=140.0, max_value=210.0, value=163.0, step=0.5)
        weight = st.number_input("몸무게 (kg)", min_value=35.0, max_value=150.0, value=55.0, step=0.5)

    with col_right:
        st.subheader("목표 & 예산")
        goal = st.radio("건강 목표", ["체중감량", "유지", "근육증가"], horizontal=True)
        activity = st.select_slider(
            "활동량",
            options=[1.2, 1.375, 1.55, 1.725, 1.9],
            value=1.375,
            format_func=lambda x: {1.2: "거의 안 움직임", 1.375: "가벼운 운동", 1.55: "보통 운동", 1.725: "활발한 운동", 1.9: "매우 활발"}.get(x, str(x)),
        )
        budget = st.slider("1끼 예산 (원)", 3000, 15000, 8000, step=500)
        allergies = st.multiselect("알레르기 (해당 시 선택)", ["난류", "우유", "대두", "밀", "갑각류", "견과류", "땅콩"])

    # TDEE 미리보기
    tdee = calc_tdee(gender, weight, height, age, activity, goal)
    protein = calc_protein(weight, goal)
    meal_kcal = round(tdee * 0.35, 1)

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TDEE", f"{tdee} kcal")
    c2.metric("1끼 목표 칼로리", f"{meal_kcal} kcal")
    c3.metric("1끼 단백질 목표", f"{protein} g")
    c4.metric("1끼 예산", f"{budget:,}원")

    st.caption("* Mifflin-St Jeor 공식 × 활동계수 × 목표 보정 | 1끼 = 하루의 35%")

    if st.button("다음: 냉장고 재료 입력 →", use_container_width=True, type="primary"):
        st.session_state.user_profile = {
            "gender": gender, "age": age, "height": height, "weight": weight,
            "goal": goal, "activity": activity, "budget": budget,
            "allergies": allergies, "tdee": tdee, "protein": protein,
            "meal_kcal": meal_kcal,
        }
        st.session_state.step = 2
        st.rerun()

# 섹션 7: Step 2 — 냉장고 재료 입력
elif st.session_state.step == 2:
    profile = st.session_state.user_profile
    st.title("🧊 RefrigerAI — 내 냉장고")

    # 프로필 요약 카드
    st.markdown(f"""
    <div class="profile-card">
        <h2>👤 내 프로필</h2>
        <div class="stat">
            {profile['gender'] == 'male' and '남성' or '여성'} · {profile['age']}세 · {profile['height']}cm / {profile['weight']}kg · 목표: {profile['goal']}
        </div>
        <div class="stat" style="margin-top:4px;">
            TDEE {profile['tdee']} kcal → 1끼 {profile['meal_kcal']} kcal · 단백질 {profile['protein']}g · 예산 {profile['budget']:,}원
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_ingr, col_extra = st.columns([2, 1])

    with col_ingr:
        st.subheader("보유 재료 선택")
        # 된장두부찌개 재료가 기본 포함된 프리셋
        default_ingredients = ["두부", "돼지고기", "김치", "대파", "청양고추", "홍고추", "닭고기", "감자", "당근"]
        selected_ingredients = st.multiselect(
            "냉장고에 있는 재료를 선택하세요",
            options=ALL_INGREDIENTS,
            default=default_ingredients,
        )

        # 유통기한 입력
        if selected_ingredients:
            st.markdown("**유통기한 (D+N일, 0이면 오늘 만료)**")
            expiry_info = {}
            cols = st.columns(3)
            for i, ing in enumerate(selected_ingredients):
                with cols[i % 3]:
                    days = st.number_input(f"{ing}", min_value=0, max_value=30, value=5, key=f"exp_{ing}")
                    expiry_info[ing] = days

    with col_extra:
        st.subheader("보유 조미료")
        default_seasonings = ["된장", "고춧가루", "다진마늘", "간장", "참기름", "소금"]
        selected_seasonings = st.multiselect(
            "보유 조미료 선택", options=ALL_SEASONINGS, default=default_seasonings,
        )

        st.subheader("보유 조리도구")
        default_tools = ["냄비", "프라이팬", "칼/도마", "믹서기"]
        selected_tools = st.multiselect(
            "보유 도구 선택", options=ALL_TOOLS, default=default_tools,
        )

    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← 이전", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("🔍 레시피 추천받기", use_container_width=True, type="primary"):
            st.session_state.fridge = {
                "ingredients": selected_ingredients,
                "seasonings": selected_seasonings,
                "tools": selected_tools,
                "expiry": expiry_info if selected_ingredients else {},
            }
            st.session_state.step = 3
            st.rerun()

# 섹션 8: Step 3 — 추천 결과 + 조리 가이드
elif st.session_state.step == 3:
    profile = st.session_state.user_profile
    fridge = st.session_state.fridge

    st.title("🎯 RefrigerAI — 추천 결과")

    # ── 파이프라인 시뮬레이션 ──────────────────────────
    pipeline_placeholder = st.empty()

    steps_log = [
        ("KG 탐색", "보유 재료로 실행 가능한 레시피 검색 중..."),
        ("KG 매칭", f"보유 재료 {len(fridge['ingredients'])}개 × 레시피 1,146개 교집합 계산..."),
        ("LP 최적화", "영양·비용·유통기한 동시 최적화 중..."),
        ("결과 정렬", "목적함수 점수 기준 정렬 완료"),
    ]

    for i, (title, desc) in enumerate(steps_log):
        with pipeline_placeholder.container():
            for j in range(i + 1):
                done_title, done_desc = steps_log[j]
                if j < i:
                    st.markdown(f'<div class="pipeline-step pipeline-done">✅ <b>[{done_title}]</b> {done_desc}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="pipeline-step pipeline-active">⏳ <b>[{done_title}]</b> {done_desc}</div>', unsafe_allow_html=True)
        time.sleep(0.6)

    # 최종 상태
    with pipeline_placeholder.container():
        for title, desc in steps_log:
            st.markdown(f'<div class="pipeline-step pipeline-done">✅ <b>[{title}]</b> {desc}</div>', unsafe_allow_html=True)

    st.divider()

    # ── KG 매칭 결과 계산 ─────────────────────────────
    recipe = MOCK_RECIPE
    user_ingr = set(fridge["ingredients"])
    required = set(recipe["required_ingredients"])
    matched = required & user_ingr
    missing = required - user_ingr
    match_rate = len(matched) / len(required) if required else 0

    seasoning_required = set(recipe["required_seasonings"])
    seasoning_matched = seasoning_required & set(fridge["seasonings"])
    seasoning_missing = seasoning_required - set(fridge["seasonings"])

    tool_required = set(recipe["required_tools"])
    tool_matched = tool_required & set(fridge["tools"])

    # 유통기한 임박 재료 찾기
    expiry = fridge.get("expiry", {})
    urgent_items = [(ing, d) for ing, d in expiry.items() if d <= 3 and ing in matched]
    urgent_items.sort(key=lambda x: x[1])

    # ── 추천 레시피 카드 ──────────────────────────────
    # 유통기한 임박 배지 미리 생성
    expiry_badges = "".join(
        f'<span class="reason-badge badge-expiry">⏰ {ing} D+{d}</span>'
        for ing, d in urgent_items
    )

    card_html = (
        f'<div class="recipe-card">'
        f'<div class="recipe-card-title">🏆 {recipe["recipe_name"]}</div>'
        f'<div class="recipe-card-sub">{recipe["method"]} · {recipe["dish_type"]} · 기준 {recipe["base_servings"]}인분 · 약 {recipe["total_time_min"]}분</div>'
        f'<div style="margin-top: 12px;">'
        f'<span class="reason-badge badge-match">🔗 재료 매칭률 {match_rate:.0%}</span>'
        f'<span class="reason-badge badge-nutrition">💪 단백질 {recipe["protein_g"]}g</span>'
        f'<span class="reason-badge badge-cost">💰 예상 {recipe["estimated_cost"]:,}원</span>'
        f'{expiry_badges}'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # LP 선정 이유
    st.markdown("#### 📊 이 레시피가 선택된 이유 (LP 목적함수 분해)")
    lp_c1, lp_c2, lp_c3, lp_c4 = st.columns(4)
    lp_c1.metric("영양 점수", "0.82", "단백질 충족")
    lp_c2.metric("비용 점수", "0.91", f"예산 대비 {recipe['estimated_cost']/profile['budget']*100:.0f}%")
    lp_c3.metric("유통기한 점수", "0.75" if urgent_items else "0.50", f"임박 {len(urgent_items)}개 소진")
    lp_c4.metric("종합 LP 점수", "0.8340", "Optimal")

    st.divider()

    # ── 영양 정보 ─────────────────────────────────────
    st.markdown("#### 🥗 영양 정보 (1인분 기준)")
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("칼로리", f"{recipe['kcal']} kcal", f"목표 {profile['meal_kcal']} kcal")
    n2.metric("단백질", f"{recipe['protein_g']} g", f"목표 {profile['protein']} g")
    n3.metric("지방", f"{recipe['fat_g']} g")
    n4.metric("탄수화물", f"{recipe['carb_g']} g")

    st.divider()

    # ── 재료 체크리스트 ───────────────────────────────
    st.markdown("#### 🧾 재료 체크리스트")
    col_main, col_season, col_tool = st.columns(3)

    with col_main:
        st.markdown("**주재료**")
        for ing in recipe["required_ingredients"]:
            if ing in matched:
                d = expiry.get(ing, "")
                expiry_tag = f" (D+{d})" if isinstance(d, int) and d <= 3 else ""
                st.markdown(f'<div class="ingr-check ingr-owned">✅ {ing}{expiry_tag}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ingr-check ingr-missing">❌ {ing} — 구매 필요</div>', unsafe_allow_html=True)

    with col_season:
        st.markdown("**조미료**")
        for s in recipe["required_seasonings"]:
            if s in seasoning_matched:
                st.markdown(f'<div class="ingr-check ingr-owned">✅ {s}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ingr-check ingr-missing">❌ {s}</div>', unsafe_allow_html=True)

    with col_tool:
        st.markdown("**조리도구**")
        for t in recipe["required_tools"]:
            if t in tool_matched:
                st.markdown(f'<div class="ingr-check ingr-owned">✅ {t}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ingr-check ingr-missing">❌ {t}</div>', unsafe_allow_html=True)

    st.divider()

    # ── 조리 가이드 ───────────────────────────────────
    st.markdown("#### 👨‍🍳 조리 가이드")

    # JSON 로드
    recipe_json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "structured_steps", "137_된장두부찌개.json"
    )

    if os.path.exists(recipe_json_path):
        with open(recipe_json_path, "r", encoding="utf-8") as f:
            recipe_steps_data = json.load(f)

        # 인분 조절
        col_srv, col_time = st.columns([1, 1])
        with col_srv:
            target_servings = st.slider("🍽️ 인분 조절", 1, 8, recipe_steps_data["base_servings"])

        # 스케일링
        result = scale_recipe(recipe_steps_data, target_servings)
        total_scaled = result["scaled_total_min"]

        with col_time:
            st.markdown(f"""
            <div class="time-banner">
                <div class="time-banner-label">{target_servings}인분 예상 조리시간</div>
                <div class="time-banner-value">약 {math.ceil(total_scaled)}분</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # 진행률 바
        total_steps = len(recipe_steps_data["steps"])
        completed = st.session_state.get("completed_steps", set())
        progress = len(completed) / total_steps
        st.progress(progress, text=f"진행률: {len(completed)}/{total_steps} 단계 완료")

        # 스텝 카드 렌더링
        for s in recipe_steps_data["steps"]:
            step_num = s["step_number"]

            # 스케일된 시간 가져오기
            scaled_info = next((x for x in result["steps"] if x["step_number"] == step_num), None)
            scaled_time = scaled_info["scaled_time_min"] if scaled_info else s["estimated_time_min"]

            time_str = f"{int(scaled_time)}분" if scaled_time == int(scaled_time) else f"{scaled_time:.1f}분"

            heat = s.get("heat_level", "없음")
            heat_class = f"chip-heat-{heat}"

            meta_chips = f'<span class="meta-chip {heat_class}">🔥 {heat}</span>'
            meta_chips += f'<span class="meta-chip chip-time">⏱ {time_str}</span>'
            if s.get("end_condition"):
                meta_chips += f'<span class="meta-chip chip-condition">🎯 {s["end_condition"]}</span>'

            tools_html = ""
            if s.get("tools_used"):
                tools_html = "".join(f'<span class="tool-tag">🔧 {t}</span>' for t in s["tools_used"])

            tip_html = ""
            if s.get("technique_note"):
                tip_html = f'<div class="tip-box">{s["technique_note"]}</div>'

            # 완료 체크 표시
            is_done = step_num in completed
            border_color = "#4caf50" if is_done else "#ff6b35"

            st.markdown(f"""
            <div class="step-card" style="border-left-color: {border_color}; {'opacity: 0.6;' if is_done else ''}">
                <div class="step-header">
                    <div class="step-number" style="background: {border_color};">{'✓' if is_done else step_num}</div>
                    <div class="step-action">{s['action']} — {s['target']}</div>
                </div>
                <div class="step-detail">{s['detail']}</div>
                <div class="meta-row">{meta_chips}</div>
                {tools_html}
                {tip_html}
            </div>
            """, unsafe_allow_html=True)

            # 완료 체크박스 + 타이머
            col_check, col_timer = st.columns([1, 1])
            with col_check:
                if st.checkbox(f"Step {step_num} 완료", value=is_done, key=f"done_{step_num}"):
                    completed.add(step_num)
                else:
                    completed.discard(step_num)
                st.session_state.completed_steps = completed

            with col_timer:
                timer_seconds = int(scaled_time * 60)
                with st.expander(f"⏱ 타이머 ({time_str})"):
                    st.components.v1.html(f"""
                    <div style="font-family:'Noto Sans KR',sans-serif; text-align:center; padding:8px;">
                        <div id="d-{step_num}" style="font-size:42px; font-weight:700; color:#1565c0;">
                            {timer_seconds // 60:02d}:{timer_seconds % 60:02d}
                        </div>
                        <div style="display:flex; gap:6px; justify-content:center; margin-top:6px;">
                            <button onclick="sT{step_num}()" style="padding:6px 16px; border:none; background:#ff6b35; color:white; border-radius:6px; cursor:pointer;">▶ 시작</button>
                            <button onclick="pT{step_num}()" style="padding:6px 16px; border:none; background:#eceff1; border-radius:6px; cursor:pointer;">⏸ 정지</button>
                            <button onclick="rT{step_num}()" style="padding:6px 16px; border:none; background:#eceff1; border-radius:6px; cursor:pointer;">↺ 리셋</button>
                        </div>
                    </div>
                    <script>
                    var r{step_num}={timer_seconds},i{step_num}=null;
                    function sT{step_num}(){{if(i{step_num})return;i{step_num}=setInterval(function(){{if(r{step_num}<=0){{clearInterval(i{step_num});i{step_num}=null;document.getElementById('d-{step_num}').style.color='#c62828';document.getElementById('d-{step_num}').innerText='완료!';return;}}r{step_num}--;var m=Math.floor(r{step_num}/60),s=r{step_num}%60;document.getElementById('d-{step_num}').innerText=String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');}},1000);}}
                    function pT{step_num}(){{clearInterval(i{step_num});i{step_num}=null;}}
                    function rT{step_num}(){{clearInterval(i{step_num});i{step_num}=null;r{step_num}={timer_seconds};var m=Math.floor({timer_seconds}/60),s={timer_seconds}%60;document.getElementById('d-{step_num}').style.color='#1565c0';document.getElementById('d-{step_num}').innerText=String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');}}
                    </script>
                    """, height=120)

        # 조리 완료
        if len(completed) == total_steps:
            st.balloons()
            st.success("🎉 조리 완료! CookHistory에 기록됩니다.")

    else:
        st.error(f"레시피 JSON을 찾을 수 없습니다: {recipe_json_path}")

    # 푸터
    st.divider()
    st.caption(f"🔬 파이프라인: KG 재료 매칭 → LP 최적화 (w_nutrition=0.5, w_cost=0.3, w_expiry=0.2) → 조리 가이드")

    if st.button("← 처음부터 다시", use_container_width=True):
        st.session_state.step = 1
        st.session_state.completed_steps = set()
        st.rerun()