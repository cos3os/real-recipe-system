import streamlit as st

st.set_page_config(page_title="오늘 식사 | RefrigerAI", layout="wide")

# ── 프로필 체크 ───────────────────────────────────────
profile = st.session_state.get("user_profile", {})
if not profile:
    st.warning("먼저 내 정보를 입력해주세요.")
    if st.button("← 내 정보 입력으로", type="primary"):
        st.switch_page("pages/1_내정보.py")
    st.stop()

# ── 음식 DB (단품 기준) ──────────────────────────────
FOOD_DB = {
    # 밥·면·빵
    "밥":           {"kcal": 300, "protein": 5,  "fat": 1,  "carb": 65, "cost": 500},
    "토스트":       {"kcal": 250, "protein": 8,  "fat": 9,  "carb": 35, "cost": 1500},
    "라면":         {"kcal": 500, "protein": 10, "fat": 16, "carb": 78, "cost": 1500},
    "시리얼":       {"kcal": 200, "protein": 4,  "fat": 2,  "carb": 44, "cost": 1500},
    # 반찬·메인
    "김치찌개":     {"kcal": 200, "protein": 12, "fat": 10, "carb": 15, "cost": 4000},
    "제육볶음":     {"kcal": 450, "protein": 23, "fat": 24, "carb": 25, "cost": 5500},
    "비빔밥":       {"kcal": 580, "protein": 18, "fat": 12, "carb": 88, "cost": 7500},
    "떡볶이":       {"kcal": 480, "protein": 8,  "fat": 10, "carb": 88, "cost": 3500},
    "계란후라이":   {"kcal": 120, "protein": 8,  "fat": 9,  "carb": 1,  "cost": 500},
    "닭가슴살":     {"kcal": 165, "protein": 31, "fat": 4,  "carb": 0,  "cost": 3000},
    "삼각김밥":     {"kcal": 200, "protein": 5,  "fat": 3,  "carb": 38, "cost": 1200},
    # 음료·간식
    "우유":         {"kcal": 130, "protein": 6,  "fat": 5,  "carb": 10, "cost": 1000},
    "아메리카노":   {"kcal": 5,   "protein": 0,  "fat": 0,  "carb": 1,  "cost": 1500},
    "프로틴쉐이크": {"kcal": 150, "protein": 25, "fat": 2,  "carb": 8,  "cost": 3000},
    "요거트":       {"kcal": 100, "protein": 4,  "fat": 3,  "carb": 14, "cost": 1500},
    "바나나":       {"kcal": 93,  "protein": 1,  "fat": 0,  "carb": 24, "cost": 500},
    "고구마":       {"kcal": 130, "protein": 2,  "fat": 0,  "carb": 32, "cost": 1000},
    "샐러드":       {"kcal": 80,  "protein": 3,  "fat": 4,  "carb": 8,  "cost": 3500},
    "사과":         {"kcal": 95,  "protein": 0,  "fat": 0,  "carb": 25, "cost": 1500},
    "삶은달걀":     {"kcal": 78,  "protein": 6,  "fat": 5,  "carb": 1,  "cost": 300},
}

# ── CSS ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.remaining-card { border-radius: 12px; padding: 20px 24px; text-align: center; }
.remaining-ok { background: #e8f5e9; border: 2px solid #4caf50; }
.remaining-warn { background: #fff3e0; border: 2px solid #ff9800; }
.remaining-over { background: #ffebee; border: 2px solid #f44336; }
.remaining-label { font-size: 13px; color: #666; }
.remaining-value { font-size: 28px; font-weight: 700; margin-top: 4px; }
.food-item { background: #f8f9fa; border-radius: 8px; padding: 10px 16px; margin: 4px 0; font-size: 14px; display: flex; justify-content: space-between; align-items: center; }
.food-item-name { font-weight: 600; }
.food-item-info { color: #666; font-size: 13px; }
.available-foods { background: #f8f9fa; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #666; line-height: 1.8; }
</style>
""", unsafe_allow_html=True)

# ── 페이지 시작 ──────────────────────────────────────
st.title("🍽️ 오늘 먹은 음식")
st.caption("오늘 먹은 음식을 입력하면 잔여 영양이 자동 계산되고, 메뉴 추천 시 LP 제약조건으로 반영됩니다.")

# ── 음식 입력 ────────────────────────────────────────
if "eaten_list" not in st.session_state:
    st.session_state.eaten_list = []

col_input, col_add = st.columns([3, 1])

with col_input:
    food_input = st.text_input(
        "음식 이름 입력",
        placeholder="예: 라면, 닭가슴살, 바나나...",
        key="food_input",
    )

with col_add:
    st.markdown("<br>", unsafe_allow_html=True)
    add_clicked = st.button("➕ 추가", use_container_width=True)

if add_clicked and food_input:
    cleaned = food_input.strip()
    if cleaned in FOOD_DB:
        st.session_state.eaten_list.append(cleaned)
        st.rerun()
    else:
        # 부분 매칭 시도
        partial = [name for name in FOOD_DB if cleaned in name or name in cleaned]
        if partial:
            st.warning(f'"{cleaned}"을 찾을 수 없습니다. 혹시 이건가요? → {", ".join(partial)}')
        else:
            st.error(f'"{cleaned}"은 현재 DB에 없습니다. 아래 입력 가능 목록을 확인해주세요.')

st.divider()

# ── 추가된 음식 목록 ────────────────────────────────
st.markdown("#### 📋 오늘 먹은 것")

if not st.session_state.eaten_list:
    st.info("아직 추가된 음식이 없습니다. 위에서 음식 이름을 입력하고 추가해주세요.")
else:
    for idx, food_name in enumerate(st.session_state.eaten_list):
        info = FOOD_DB[food_name]
        col_item, col_del = st.columns([5, 1])
        with col_item:
            st.markdown(
                f'<div class="food-item">'
                f'<span class="food-item-name">{food_name}</span>'
                f'<span class="food-item-info">'
                f'{info["kcal"]} kcal · 단백질 {info["protein"]}g · '
                f'지방 {info["fat"]}g · 탄수화물 {info["carb"]}g · {info["cost"]:,}원'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("🗑️", key=f"del_{idx}", use_container_width=True):
                st.session_state.eaten_list.pop(idx)
                st.rerun()

# ── 합산 계산 ────────────────────────────────────────
consumed = {"kcal": 0, "protein": 0, "fat": 0, "carb": 0, "cost": 0}
for food_name in st.session_state.eaten_list:
    info = FOOD_DB[food_name]
    for key in consumed:
        consumed[key] += info[key]

remaining = {
    "kcal": round(profile["tdee"] - consumed["kcal"], 1),
    "protein": round(profile["daily_protein"] - consumed["protein"], 1),
    "fat": round(profile["daily_fat"] - consumed["fat"], 1),
    "carb": round(profile["daily_carb"] - consumed["carb"], 1),
    "cost": profile["budget"] - consumed["cost"],
}

st.divider()

# ── 소비량 요약 ──────────────────────────────────────
st.markdown("#### 📊 오늘 소비량")
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("칼로리", f'{consumed["kcal"]} kcal', f'/ {profile["tdee"]} kcal')
s2.metric("단백질", f'{consumed["protein"]} g', f'/ {profile["daily_protein"]} g')
s3.metric("탄수화물", f'{consumed["carb"]} g', f'/ {profile["daily_carb"]} g')
s4.metric("지방", f'{consumed["fat"]} g', f'/ {profile["daily_fat"]} g')
s5.metric("식비", f'{consumed["cost"]:,}원', f'/ {profile["budget"]:,}원')

st.divider()

# ── 잔여 영양 예산 ───────────────────────────────────
st.markdown("#### 🎯 저녁 식사 영양 예산 (= LP 제약조건)")

def card_class(value):
    if value <= 0:
        return "remaining-over"
    elif value < 200:
        return "remaining-warn"
    return "remaining-ok"

def protein_class(value):
    if value <= 0:
        return "remaining-ok"
    elif value > 30:
        return "remaining-warn"
    return "remaining-ok"

r1, r2, r3, r4, r5 = st.columns(5)

with r1:
    cls = card_class(remaining["kcal"])
    st.markdown(
        f'<div class="remaining-card {cls}">'
        f'<div class="remaining-label">잔여 칼로리</div>'
        f'<div class="remaining-value">{remaining["kcal"]} kcal</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with r2:
    cls = protein_class(remaining["protein"])
    label = "아직 필요" if remaining["protein"] > 0 else "충족 완료"
    st.markdown(
        f'<div class="remaining-card {cls}">'
        f'<div class="remaining-label">잔여 단백질 ({label})</div>'
        f'<div class="remaining-value">{max(remaining["protein"], 0)} g</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with r3:
    cls = card_class(remaining["carb"])
    st.markdown(
        f'<div class="remaining-card {cls}">'
        f'<div class="remaining-label">잔여 탄수화물</div>'
        f'<div class="remaining-value">{remaining["carb"]} g</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with r4:
    cls = card_class(remaining["fat"])
    st.markdown(
        f'<div class="remaining-card {cls}">'
        f'<div class="remaining-label">잔여 지방</div>'
        f'<div class="remaining-value">{remaining["fat"]} g</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with r5:
    cls = card_class(remaining["cost"])
    st.markdown(
        f'<div class="remaining-card {cls}">'
        f'<div class="remaining-label">잔여 예산</div>'
        f'<div class="remaining-value">{remaining["cost"]:,}원</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

if remaining["kcal"] <= 0:
    st.warning("오늘 칼로리를 이미 다 소비했어요. 저녁은 가벼운 메뉴를 추천합니다.")

st.caption("* 잔여 영양 = 하루 목표 - 오늘 소비량 → 이 값이 저녁 추천 시 LP 제약조건으로 자동 적용됩니다.")

# ── 네비게이션 ───────────────────────────────────────
st.divider()
col_back, col_next = st.columns(2)

with col_back:
    if st.button("← 내 정보", use_container_width=True):
        st.switch_page("pages/1_내정보.py")

with col_next:
    if st.button("다음: 냉장고 재료 →", use_container_width=True, type="primary"):
        st.session_state.today_meals = {
            "eaten_list": st.session_state.eaten_list,
            "consumed": consumed,
            "remaining": remaining,
        }
        st.switch_page("pages/3_냉장고.py")