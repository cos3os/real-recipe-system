import streamlit as st

st.set_page_config(page_title="냉장고 | RefrigerAI", layout="wide")

# ── 데이터 체크 ──────────────────────────────────────
profile = st.session_state.get("user_profile", {})
today = st.session_state.get("today_meals", {})
if not profile or not today:
    st.warning("이전 단계를 먼저 완료해주세요.")
    if st.button("← 처음으로", type="primary"):
        st.switch_page("pages/1_내정보.py")
    st.stop()

# ── 재료 목록 (mock) ─────────────────────────────────
ALL_INGREDIENTS = [
    "두부", "돼지고기", "김치", "대파", "청양고추", "홍고추",
    "애호박", "양파", "표고버섯", "닭고기", "달걀", "감자",
    "당근", "팽이버섯", "청경채", "시금치", "콩나물",
    "소고기", "오징어", "멥쌀밥", "고구마", "브로콜리",
]

ALL_SEASONINGS = [
    "된장", "고춧가루", "다진마늘", "간장", "참기름",
    "소금", "고추장", "식용유", "설탕", "후추",
]

ALL_TOOLS = ["냄비", "프라이팬", "전자레인지", "오븐", "믹서기", "칼/도마"]

# ── CSS ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.summary-bar { background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-radius: 12px; padding: 16px 24px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.summary-item { font-size: 14px; opacity: 0.95; }
.summary-item b { font-size: 16px; }
.expiry-urgent { color: #c62828; font-weight: 600; }
.expiry-normal { color: #666; }
</style>
""", unsafe_allow_html=True)

# ── 상단 요약 바 ─────────────────────────────────────
remaining = today["remaining"]
consumed = today["consumed"]

st.title("🧊 나의 냉장고")

summary_html = (
    f'<div class="summary-bar">'
    f'<div class="summary-item">👤 {"남" if profile["gender"]=="male" else "여"} · {profile["age"]}세 · {profile["goal"]}</div>'
    f'<div class="summary-item">오늘 소비 <b>{consumed["kcal"]} kcal</b></div>'
    f'<div class="summary-item">잔여 <b>{remaining["kcal"]} kcal</b> · 단백질 <b>{max(remaining["protein"],0)}g</b></div>'
    f'<div class="summary-item">예산 잔여 <b>{remaining["cost"]:,}원</b></div>'
    f'</div>'
)
st.markdown(summary_html, unsafe_allow_html=True)

# ── 재료 입력 ────────────────────────────────────────
col_ingr, col_extra = st.columns([2, 1])

with col_ingr:
    st.subheader("보유 재료")

    default_ingredients = [
        "두부", "돼지고기", "김치", "대파", "청양고추", "홍고추",
        "닭고기", "감자", "당근",
    ]
    selected_ingredients = st.multiselect(
        "냉장고에 있는 재료를 선택하세요",
        options=ALL_INGREDIENTS,
        default=default_ingredients,
    )

    # 유통기한 입력
    expiry_info = {}
    if selected_ingredients:
        st.markdown("**유통기한 (D+N일)**")

        # 프리셋: 된장두부찌개 재료는 임박으로 설정
        expiry_defaults = {
            "두부": 2, "돼지고기": 2, "김치": 7, "대파": 5,
            "청양고추": 4, "홍고추": 4, "닭고기": 2,
            "감자": 14, "당근": 7,
        }

        cols = st.columns(3)
        for i, ing in enumerate(selected_ingredients):
            with cols[i % 3]:
                default_d = expiry_defaults.get(ing, 7)
                days = st.number_input(
                    f"{ing}", min_value=0, max_value=30,
                    value=default_d, key=f"exp_{ing}",
                )
                expiry_info[ing] = days

        # 임박 재료 하이라이트
        urgent = [(ing, d) for ing, d in expiry_info.items() if d <= 3]
        if urgent:
            urgent.sort(key=lambda x: x[1])
            urgent_text = " · ".join(f"{ing} (D+{d})" for ing, d in urgent)
            st.markdown(
                f'<div style="margin-top:8px; font-size:14px;">'
                f'⚠️ <span class="expiry-urgent">유통기한 임박: {urgent_text}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

with col_extra:
    st.subheader("보유 조미료")
    default_seasonings = ["된장", "고춧가루", "다진마늘", "간장", "참기름", "소금"]
    selected_seasonings = st.multiselect(
        "보유 조미료 선택",
        options=ALL_SEASONINGS,
        default=default_seasonings,
    )

    st.subheader("보유 조리도구")
    default_tools = ["냄비", "프라이팬", "칼/도마", "믹서기"]
    selected_tools = st.multiselect(
        "보유 도구 선택",
        options=ALL_TOOLS,
        default=default_tools,
    )

# ── 하단 요약 ────────────────────────────────────────
st.divider()

c1, c2, c3 = st.columns(3)
c1.metric("선택 재료", f"{len(selected_ingredients)}종")
c2.metric("보유 조미료", f"{len(selected_seasonings)}종")
c3.metric("보유 도구", f"{len(selected_tools)}종")

# ── 네비게이션 ───────────────────────────────────────
st.divider()
col_back, col_next = st.columns(2)

with col_back:
    if st.button("← 오늘 식사", use_container_width=True):
        st.switch_page("pages/2_오늘식사.py")

with col_next:
    if st.button("🔍 레시피 추천받기", use_container_width=True, type="primary"):
        st.session_state.fridge = {
            "ingredients": selected_ingredients,
            "seasonings": selected_seasonings,
            "tools": selected_tools,
            "expiry": expiry_info,
        }
        st.switch_page("pages/4_추천결과.py")