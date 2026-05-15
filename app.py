import streamlit as st

st.set_page_config(
    page_title="RefrigerAI",
    page_icon="🍳",
    layout="wide",
)

# ── session_state 초기화 (전 페이지 공유) ─────────────
defaults = {
    "user_profile": {},
    "today_meals": {},
    "fridge": {},
    "completed_steps": set(),
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── CSS ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.hero { text-align: center; padding: 60px 20px 40px; }
.hero h1 { font-size: 48px; font-weight: 700; margin-bottom: 8px; }
.hero p { font-size: 18px; color: #666; margin-bottom: 32px; }
.feature-card { background: #f8f9fa; border-radius: 12px; padding: 24px; text-align: center; height: 100%; }
.feature-card h3 { font-size: 18px; margin: 12px 0 8px; }
.feature-card p { font-size: 14px; color: #666; }
.flow-step { display: inline-block; background: #ff6b35; color: white; width: 28px; height: 28px; border-radius: 50%; text-align: center; line-height: 28px; font-size: 13px; font-weight: 700; margin-right: 8px; }
.flow-item { font-size: 15px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ── 히어로 섹션 ──────────────────────────────────────
st.markdown(
    '<div class="hero">'
    '<h1>🍳 RefrigerAI</h1>'
    '<p>내 냉장고 재료 + 영양 목표 + 오늘 먹은 음식 → 최적의 한 끼 추천</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── 핵심 기능 3개 ────────────────────────────────────
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        '<div class="feature-card">'
        '<div style="font-size:36px;">🔗</div>'
        '<h3>지식그래프 (KG)</h3>'
        '<p>1,146개 레시피 × 797종 재료<br>보유 재료·도구·조미료 교집합으로<br>실행 가능한 레시피만 탐색</p>'
        '</div>',
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        '<div class="feature-card">'
        '<div style="font-size:36px;">📐</div>'
        '<h3>선형계획법 (LP)</h3>'
        '<p>단백질 최대화 + 비용 최소화<br>칼로리·영양·예산·유통기한<br>제약조건 동시 최적화</p>'
        '</div>',
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        '<div class="feature-card">'
        '<div style="font-size:36px;">🤖</div>'
        '<h3>LLM 설명</h3>'
        '<p>KG·LP 결과를 컨텍스트로 주입<br>근거 기반 자연어 설명 생성<br>Hallucination 차단</p>'
        '</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── 시연 플로우 안내 ─────────────────────────────────
st.markdown("#### 시연 흐름")
flow = [
    ("1", "내 정보 입력", "키·몸무게·나이 → TDEE 자동 계산"),
    ("2", "오늘 먹은 음식", "아침·점심·간식 기록 → 잔여 영양 계산"),
    ("3", "냉장고 재료", "보유 재료·조미료·도구 선택"),
    ("4", "추천 결과", "KG 매칭 → LP 최적화 → 레시피 카드"),
    ("5", "조리 가이드", "단계별 스텝 카드 + 타이머"),
]
for num, title, desc in flow:
    st.markdown(
        f'<div class="flow-item">'
        f'<span class="flow-step">{num}</span>'
        f'<b>{title}</b> — {desc}'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("")

if st.button("🚀 시작하기", use_container_width=True, type="primary"):
    st.switch_page("pages/1_내정보.py")

st.divider()
st.caption("시스템분석 3조 · 김수민 · 민채연 · 김다인 | KG + LP + LLM 기반 개인화 레시피 추천 시스템")