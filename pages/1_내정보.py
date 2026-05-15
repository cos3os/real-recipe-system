import streamlit as st

st.set_page_config(page_title="내 정보 | RefrigerAI", layout="wide")

# ── TDEE 계산 (Mifflin-St Jeor) ──────────────────────
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

def calc_daily_protein(weight, goal):
    coeff = {"근육증가": 2.0, "체중감량": 1.8, "유지": 1.4}.get(goal, 1.4)
    return round(weight * coeff, 1)

# ── 페이지 시작 ──────────────────────────────────────
st.title("👤 내 정보")
st.caption("신체 정보와 목표를 입력하세요.")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("기본 정보")
    gender = st.radio(
        "성별", ["male", "female"],
        format_func=lambda x: "남성" if x == "male" else "여성",
        horizontal=True,
    )
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
        format_func=lambda x: {
            1.2: "거의 안 움직임",
            1.375: "가벼운 운동",
            1.55: "보통 운동",
            1.725: "활발한 운동",
            1.9: "매우 활발",
        }.get(x, str(x)),
    )
    budget = st.slider("하루 식비 예산 (원)", 5000, 30000, 15000, step=1000)
    allergies = st.multiselect(
        "알레르기 (해당 시 선택)",
        ["난류", "우유", "대두", "밀", "갑각류", "견과류", "땅콩"],
    )

# ── 실시간 계산 미리보기 ─────────────────────────────
tdee = calc_tdee(gender, weight, height, age, activity, goal)
daily_protein = calc_daily_protein(weight, goal)
daily_carb = round(tdee * 0.5 / 4, 1)   # 탄수화물: 총 칼로리 50% / 4kcal
daily_fat = round(tdee * 0.25 / 9, 1)   # 지방: 총 칼로리 25% / 9kcal

st.divider()
st.markdown("#### 📊 오늘 하루 영양 목표")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("TDEE", f"{tdee} kcal")
c2.metric("단백질", f"{daily_protein} g")
c3.metric("탄수화물", f"{daily_carb} g")
c4.metric("지방", f"{daily_fat} g")
c5.metric("식비 예산", f"{budget:,}원")

st.caption("* Mifflin-St Jeor 공식 × 활동계수 × 목표 보정 | 단백질: 체중 × 목표계수 | 탄수화물 50% · 지방 25%")

# ── 네비게이션 ───────────────────────────────────────
st.divider()
col_back, col_next = st.columns(2)

with col_back:
    if st.button("← 홈", use_container_width=True):
        st.switch_page("app.py")

with col_next:
    if st.button("다음: 오늘 먹은 음식 →", use_container_width=True, type="primary"):
        st.session_state.user_profile = {
            "gender": gender,
            "age": age,
            "height": height,
            "weight": weight,
            "goal": goal,
            "activity": activity,
            "budget": budget,
            "allergies": allergies,
            "tdee": tdee,
            "daily_protein": daily_protein,
            "daily_carb": daily_carb,
            "daily_fat": daily_fat,
        }
        st.switch_page("pages/2_오늘식사.py")