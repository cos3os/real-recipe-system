import streamlit as st
import time

st.set_page_config(page_title="추천 결과 | RefrigerAI", layout="wide")

# ── 데이터 체크 ──────────────────────────────────────
profile = st.session_state.get("user_profile", {})
today = st.session_state.get("today_meals", {})
fridge = st.session_state.get("fridge", {})

if not profile or not today or not fridge:
    st.warning("이전 단계를 먼저 완료해주세요.")
    if st.button("← 처음으로", type="primary"):
        st.switch_page("pages/1_내정보.py")
    st.stop()

remaining = today["remaining"]
consumed = today["consumed"]
expiry = fridge.get("expiry", {})

# ── Mock 레시피 데이터 ───────────────────────────────
MOCK_RECIPE = {
    "recipe_id": 137,
    "recipe_name": "된장 두부찌개",
    "method": "끓이기",
    "dish_type": "찌개",
    "base_servings": 4,
    "total_time_min": 25,
    "kcal": 285.4,
    "protein_g": 18.2,
    "fat_g": 11.3,
    "carb_g": 28.7,
    "estimated_cost": 3200,
    "required_ingredients": ["두부", "돼지고기", "김치", "대파", "청양고추", "홍고추"],
    "required_seasonings": ["된장", "고춧가루", "다진마늘"],
    "required_tools": ["냄비", "믹서기", "칼/도마"],
}

# ── CSS ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.recipe-card { background: white; border: 2px solid #ff6b35; border-radius: 16px; padding: 24px; margin: 16px 0; }
.recipe-card-title { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.recipe-card-sub { font-size: 13px; color: #888; }
.reason-badge { display: inline-block; font-size: 12px; font-weight: 500; padding: 4px 12px; border-radius: 20px; margin: 4px 4px 4px 0; }
.badge-nutrition { background: #e8f5e9; color: #2e7d32; }
.badge-cost { background: #e3f2fd; color: #1565c0; }
.badge-expiry { background: #fff3e0; color: #e65100; }
.badge-match { background: #f3e5f5; color: #6a1b9a; }
.ingr-check { font-size: 15px; margin: 4px 0; }
.ingr-owned { color: #2e7d32; }
.ingr-missing { color: #c62828; }
.pipeline-step { background: #f8f9fa; border-radius: 8px; padding: 12px 16px; margin: 8px 0; font-size: 14px; }
.pipeline-done { border-left: 4px solid #4caf50; }
.pipeline-active { border-left: 4px solid #ff6b35; }
.constraint-card { background: #f0f4ff; border: 1px solid #c5cae9; border-radius: 10px; padding: 14px 18px; margin: 8px 0; }
.constraint-label { font-size: 12px; color: #5c6bc0; font-weight: 600; }
.constraint-value { font-size: 16px; font-weight: 700; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ── 페이지 시작 ──────────────────────────────────────
st.title("🎯 추천 결과")

# ── LP 제약조건 표시 (잔여 영양 기반) ────────────────
st.markdown("#### 📐 LP 제약조건 (오늘 식사 기반 자동 생성)")

lp1, lp2, lp3, lp4, lp5 = st.columns(5)

with lp1:
    st.markdown(
        f'<div class="constraint-card">'
        f'<div class="constraint-label">C1. 칼로리 상한</div>'
        f'<div class="constraint-value">≤ {remaining["kcal"]} kcal</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with lp2:
    st.markdown(
        f'<div class="constraint-card">'
        f'<div class="constraint-label">C2. 단백질 하한</div>'
        f'<div class="constraint-value">≥ {max(remaining["protein"], 0)} g</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with lp3:
    st.markdown(
        f'<div class="constraint-card">'
        f'<div class="constraint-label">C3. 탄수화물 상한</div>'
        f'<div class="constraint-value">≤ {remaining["carb"]} g</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with lp4:
    st.markdown(
        f'<div class="constraint-card">'
        f'<div class="constraint-label">C4. 지방 상한</div>'
        f'<div class="constraint-value">≤ {remaining["fat"]} g</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with lp5:
    st.markdown(
        f'<div class="constraint-card">'
        f'<div class="constraint-label">C5. 예산 상한</div>'
        f'<div class="constraint-value">≤ {remaining["cost"]:,}원</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.caption(
    f'오늘 소비: {consumed["kcal"]} kcal · 단백질 {consumed["protein"]}g '
    f'→ TDEE {profile["tdee"]} kcal에서 차감한 잔여가 제약조건으로 자동 적용'
)

st.divider()

# ── 파이프라인 시뮬레이션 ────────────────────────────
# pipeline_placeholder = st.empty()
#
# steps_log = [
#     ("KG 탐색", f'보유 재료 {len(fridge["ingredients"])}개로 실행 가능한 레시피 검색'),
#     ("KG 매칭", f'재료 {len(fridge["ingredients"])}개 × 조미료 {len(fridge["seasonings"])}개 × 레시피 1,146개 교집합 계산'),
#     ("LP 최적화", f'잔여 칼로리 {remaining["kcal"]} kcal · 단백질 {max(remaining["protein"],0)}g · 예산 {remaining["cost"]:,}원 제약 하에서 최적화'),
#     ("결과 정렬", "목적함수 점수 기준 정렬 완료"),
# ]
# 
# for i, (title, desc) in enumerate(steps_log):
#     with pipeline_placeholder.container():
#         for j in range(i + 1):
#             done_title, done_desc = steps_log[j]
#             if j < i:
#                 st.markdown(
#                     f'<div class="pipeline-step pipeline-done">✅ <b>[{done_title}]</b> {done_desc}</div>',
#                     unsafe_allow_html=True,
#                 )
#             else:
#                 st.markdown(
#                     f'<div class="pipeline-step pipeline-active">⏳ <b>[{done_title}]</b> {done_desc}</div>',
#                     unsafe_allow_html=True,
#                 )
#     time.sleep(0.6)
# 
# with pipeline_placeholder.container():
#     for title, desc in steps_log:
#         st.markdown(
#             f'<div class="pipeline-step pipeline-done">✅ <b>[{title}]</b> {desc}</div>',
#             unsafe_allow_html=True,
#         )
# 
# st.divider()

# ── KG 매칭 계산 ─────────────────────────────────────
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

urgent_items = [(ing, d) for ing, d in expiry.items() if d <= 3 and ing in matched]
urgent_items.sort(key=lambda x: x[1])

# ── 추천 레시피 카드 ─────────────────────────────────
expiry_badges = "".join(
    f'<span class="reason-badge badge-expiry">⏰ {ing} D+{d}</span>'
    for ing, d in urgent_items
)

card_html = (
    f'<div class="recipe-card">'
    f'<div class="recipe-card-title">🏆 {recipe["recipe_name"]}</div>'
    f'<div class="recipe-card-sub">'
    f'{recipe["method"]} · {recipe["dish_type"]} · '
    f'기준 {recipe["base_servings"]}인분 · 약 {recipe["total_time_min"]}분'
    f'</div>'
    f'<div style="margin-top: 12px;">'
    f'<span class="reason-badge badge-match">🔗 재료 매칭률 {match_rate:.0%}</span>'
    f'<span class="reason-badge badge-nutrition">💪 단백질 {recipe["protein_g"]}g</span>'
    f'<span class="reason-badge badge-cost">💰 예상 {recipe["estimated_cost"]:,}원</span>'
    f'{expiry_badges}'
    f'</div>'
    f'</div>'
)
st.markdown(card_html, unsafe_allow_html=True)

# ── LP 점수 분해 ─────────────────────────────────────
st.markdown("#### 📊 LP 목적함수 분해")

# 점수 동적 계산 (mock이지만 잔여 영양 반영)
nutrition_score = min(recipe["protein_g"] / max(remaining["protein"], 1), 1.0) if remaining["protein"] > 0 else 1.0
cost_score = max(1 - recipe["estimated_cost"] / max(remaining["cost"], 1), 0.0)
expiry_score = min(0.5 + len(urgent_items) * 0.15, 1.0)
total_score = round(0.5 * nutrition_score + 0.3 * cost_score + 0.2 * expiry_score, 4)

lp_c1, lp_c2, lp_c3, lp_c4 = st.columns(4)
lp_c1.metric(
    "영양 점수 (w=0.5)",
    f"{nutrition_score:.2f}",
    "단백질 충족" if nutrition_score >= 0.8 else "부분 충족",
)
lp_c2.metric(
    "비용 점수 (w=0.3)",
    f"{cost_score:.2f}",
    f"예산의 {recipe['estimated_cost']/max(remaining['cost'],1)*100:.0f}%",
)
lp_c3.metric(
    "유통기한 점수 (w=0.2)",
    f"{expiry_score:.2f}",
    f"임박 {len(urgent_items)}개 소진",
)
lp_c4.metric("종합 LP 점수", f"{total_score:.4f}", "Optimal")

st.divider()

# ── 영양 정보 + 잔여 대비 ────────────────────────────
st.markdown("#### 🥗 영양 정보 (1인분 기준) vs 잔여 예산")

n1, n2, n3, n4, n5 = st.columns(5)

kcal_pct = recipe["kcal"] / max(remaining["kcal"], 1) * 100
n1.metric("칼로리", f'{recipe["kcal"]} kcal', f'잔여의 {kcal_pct:.0f}%')

prot_pct = recipe["protein_g"] / max(remaining["protein"], 1) * 100 if remaining["protein"] > 0 else 999
n2.metric("단백질", f'{recipe["protein_g"]} g', f'필요량의 {min(prot_pct, 100):.0f}% 충족')

n3.metric("지방", f'{recipe["fat_g"]} g', f'잔여 {remaining["fat"]}g 중')
n4.metric("탄수화물", f'{recipe["carb_g"]} g', f'잔여 {remaining["carb"]}g 중')
n5.metric("예상 비용", f'{recipe["estimated_cost"]:,}원', f'잔여 {remaining["cost"]:,}원 중')

# 제약 충족 여부 체크
violations = []
if recipe["kcal"] > remaining["kcal"]:
    violations.append("칼로리 초과")
if remaining["protein"] > 0 and recipe["protein_g"] < remaining["protein"]:
    violations.append(f'단백질 {remaining["protein"] - recipe["protein_g"]:.1f}g 미달')

if not violations:
    st.success("✅ 모든 LP 제약조건을 충족합니다.")
else:
    st.warning(f'⚠️ 제약 주의: {" · ".join(violations)} — 인분 조절로 보정 가능')

st.divider()

# ── 재료 체크리스트 ──────────────────────────────────
st.markdown("#### 🧾 재료 체크리스트")

col_main, col_season, col_tool = st.columns(3)

with col_main:
    st.markdown("**주재료**")
    for ing in recipe["required_ingredients"]:
        if ing in matched:
            d = expiry.get(ing, "")
            tag = f" (D+{d})" if isinstance(d, int) and d <= 3 else ""
            st.markdown(
                f'<div class="ingr-check ingr-owned">✅ {ing}{tag}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="ingr-check ingr-missing">❌ {ing} — 구매 필요</div>',
                unsafe_allow_html=True,
            )

with col_season:
    st.markdown("**조미료**")
    for s in recipe["required_seasonings"]:
        if s in seasoning_matched:
            st.markdown(
                f'<div class="ingr-check ingr-owned">✅ {s}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="ingr-check ingr-missing">❌ {s}</div>',
                unsafe_allow_html=True,
            )

with col_tool:
    st.markdown("**조리도구**")
    for t in recipe["required_tools"]:
        if t in tool_matched:
            st.markdown(
                f'<div class="ingr-check ingr-owned">✅ {t}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="ingr-check ingr-missing">❌ {t}</div>',
                unsafe_allow_html=True,
            )

# ── 네비게이션 ───────────────────────────────────────
st.divider()
col_back, col_next = st.columns(2)

with col_back:
    if st.button("← 냉장고", use_container_width=True):
        st.switch_page("pages/3_냉장고.py")

with col_next:
    if st.button("👨‍🍳 조리 시작하기", use_container_width=True, type="primary"):
        st.session_state.selected_recipe = recipe
        st.switch_page("pages/5_조리가이드.py")