"""
RefrigerAI - 조리 가이드 + AI 코치 (5_조리가이드.py)
──────────────────────────────────────────────────────
정의서 v1.2 기준:
  - 3.3 레시피 상세 + AI 코치: 좌(가이드) / 우(채팅) 분할
  - session_state 이중 구조 (original / current)
  - LLM 응답 JSON 파싱 → recipe_current 업데이트
  - 수정 하이라이트 (🔵 AI 수정됨)
  - 수정 로그 배지
  - 3.4 인분 스케일링 (st.number_input + 채팅 명령 병행)
  - 3.5 Reset/Undo
  - 4.  Missing Item 기반 추천 질문 칩
  - 5.  에러 핸들링 UX
"""

import copy
import json
import math
import os
import re
import sys

import anthropic
import streamlit as st
from dotenv import load_dotenv

# .env / db.env 둘 다 시도
load_dotenv()
load_dotenv("db.env")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.kg_query import create_matcher
from core.scaling import scale_recipe

def round_to_quarter(minutes: float) -> str:
    """15초(0.25분) 단위로 반올림해서 표시용 문자열 반환
    예: 1.1 → 1분 15초, 2.33 → 2분 30초, 4.0 → 4분
    """
    rounded = round(minutes * 4) / 4  # 0.25 단위
    whole = int(rounded)
    frac = rounded - whole
    sec_map = {0.0: "", 0.25: " 15초", 0.5: " 30초", 0.75: " 45초"}
    sec_str = sec_map.get(frac, "")
    if whole == 0:
        return f"{int(frac*60)}초"
    return f"{whole}분{sec_str}"

# ═══════════════════════════════════════════════════
# 0. 페이지 설정
# ═══════════════════════════════════════════════════
st.set_page_config(
    page_title="조리 가이드 | RefrigerAI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════
# 1. session_state 초기화 (정의서 섹션 1.3 / 7)
# ═══════════════════════════════════════════════════
_defaults = {
    "chat_history": [],
    "recipe_original": None,
    "recipe_current": None,
    "serving_count": 1,
    "modification_log": [],
    "completed_steps": set(),
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════
# 2. 데이터 체크 — selected_recipe
# ═══════════════════════════════════════════════════
recipe_meta = st.session_state.get("selected_recipe", {})
if not recipe_meta:
    st.warning("추천 결과에서 레시피를 선택해주세요.")
    if st.button("← 추천 결과로", type="primary"):
        st.switch_page("pages/4_추천결과.py")
    st.stop()

# ═══════════════════════════════════════════════════
# 3. JSON 로드
# ═══════════════════════════════════════════════════
recipe_json_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "structured_steps",
    f'{recipe_meta["recipe_id"]}_{recipe_meta["recipe_name"].replace(" ", "")}.json',
)
if not os.path.exists(recipe_json_path):
    recipe_json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "structured_steps", "137_된장두부찌개.json",
    )
if not os.path.exists(recipe_json_path):
    st.error(f"레시피 JSON을 찾을 수 없습니다: {recipe_json_path}")
    st.stop()

with open(recipe_json_path, "r", encoding="utf-8") as f:
    _raw_recipe = json.load(f)

# ── session_state 이중 구조 초기화 (정의서 3.3) ──
if st.session_state["recipe_original"] is None:
    st.session_state["recipe_original"] = _raw_recipe
    st.session_state["recipe_current"] = copy.deepcopy(_raw_recipe)
    st.session_state["serving_count"] = _raw_recipe["base_servings"]

recipe_original: dict = st.session_state["recipe_original"]
recipe_current: dict = st.session_state["recipe_current"]

# ═══════════════════════════════════════════════════
# 4. Missing Item 추출 (정의서 4.1)
# ═══════════════════════════════════════════════════
fridge = st.session_state.get("fridge", {})
fridge_ingredients = set(fridge.get("ingredients", []))
required_ingredients = set(recipe_meta.get("required_ingredients", []))
missing_items = sorted(required_ingredients - fridge_ingredients)

# ═══════════════════════════════════════════════════
# 5. KG 대체재 조회
# ═══════════════════════════════════════════════════
@st.cache_resource
def _get_matcher():
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )
    return create_matcher(csv_dir=data_dir)

def get_substitutes_for(ingredient: str) -> list[str]:
    """KG/CSV에서 대체 재료 목록 반환"""
    try:
        matcher = _get_matcher()
        subs = matcher.get_substitutes(ingredient)
        # 냉장고 보유 재료 중 대체재 우선 정렬
        in_fridge = [s["substitute"] for s in subs if s["substitute"] in fridge_ingredients]
        not_in_fridge = [s["substitute"] for s in subs if s["substitute"] not in fridge_ingredients]
        return (in_fridge + not_in_fridge)[:5]
    except Exception:
        return []

# ═══════════════════════════════════════════════════
# 6. Claude API 호출 (정의서 3.3 LLM 응답 JSON 포맷)
# ═══════════════════════════════════════════════════
SYSTEM_PROMPT = """당신은 RefrigerAI의 AI 요리 코치입니다.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트(설명, 마크다운 등) 일절 금지.

⚠️ 핵심 원칙:
- [KG 대체재 데이터]에 후보가 있으면 해당 항목을 최우선으로 추천할 것.
- KG 데이터가 없거나 부족하면 요리 상식 기반으로 자연스럽게 답변할 것.
- 냉장고에 있는 재료를 항상 최우선으로 고려할 것.
- similarity가 높을수록 더 적합한 대체재임.

응답 JSON 스키마:
{
  "action": "substitute" | "scale" | "ask" | "none",
  "step_index": <int, 0-based. substitute 시. 나머지는 -1>,
  "target": "<교체 대상 재료명 단독. substitute/ask 시. 나머지는 null>",
  "substitute": "<확정된 대체 재료명. substitute 시만. 나머지는 null>",
  "new_detail": "<substitute 시 해당 step detail을 대체 재료 기준으로 완전 재작성. 원래 재료명/동의어 하나도 남기지 말 것. 나머지는 null>",
  "scale_factor": <float, 인분 배수. scale 시만. 나머지는 null>,
  "modification_intent": <bool. 사용자 메시지에 레시피 수정 의도가 있으면 true>,
  "follow_up_chips": ["선택지1", "선택지2"] 또는 null,
  "summary": "<modification_log용 한 줄 요약. substitute/scale 시만>",
  "chat_reply": "<사용자에게 보여줄 자연어 답변. 한국어. 반드시 포함>"
}

action 선택 규칙:
- "substitute": 사용자가 특정 재료로 교체를 명확히 요청한 경우 → 즉시 적용
- "scale": 인분 변경을 명확히 요청한 경우 → 즉시 적용
- "ask": 수정 의도가 감지되나 확정이 필요한 경우 (어떤 재료로 바꿀지 선택, 수정 여부 확인 등)
         → follow_up_chips로 선택지 제공, 레시피 수정은 보류
- "none": 순수 질문/정보 요청 → 답변만, 수정 없음

follow_up_chips 규칙:
- ask 시: 선택 가능한 재료 목록 또는 ["네, 바꿔주세요", "아니요, 참고만 할게요"]
- 인분 조절 ask 시: ["1인분", "2인분", "3인분", "4인분"]
- substitute/scale/none 시: null
- 최대 4개
"""

def _build_user_context() -> str:
    """현재 레시피 + 냉장고 컨텍스트 + KG 대체재를 LLM에 주입"""
    steps_summary = "\n".join(
        f"  [{i}] {s['action']} — {s['target']}: {s['detail']}"
        for i, s in enumerate(recipe_current["steps"])
    )
    fridge_list = ", ".join(sorted(fridge_ingredients)) if fridge_ingredients else "정보 없음"
    missing_list = ", ".join(missing_items) if missing_items else "없음"

    # KG 대체재 조회 — similarity 포함 구조화 데이터로 주입
    kg_subs_lines = []
    try:
        matcher = _get_matcher()
        # 부족한 재료 + 현재 레시피 전체 재료 대상
        all_targets = list(set(missing_items) | set(
            t for s in recipe_current["steps"] for t in s["target"].split(", ")
        ))
        for item in all_targets[:8]:
            raw_subs = matcher.get_substitutes(item)
            if not raw_subs:
                continue
            in_fridge, not_in_fridge = [], []
            for s in raw_subs:
                entry = f"{s['substitute']} (similarity={s['similarity']:.2f})" if s.get('similarity') else s['substitute']
                if s['substitute'] in fridge_ingredients:
                    in_fridge.append(entry)
                else:
                    not_in_fridge.append(entry)
            line = f"  [{item}] KG 대체재:"
            if in_fridge:
                line += f"\n    ✅ 냉장고에 있음: {', '.join(in_fridge)}"
            if not_in_fridge:
                line += f"\n    ❌ 냉장고에 없음: {', '.join(not_in_fridge[:3])}"
            kg_subs_lines.append(line)
    except Exception as e:
        kg_subs_lines.append(f"  (KG 조회 오류: {e})")
    kg_subs_str = "\n".join(kg_subs_lines) if kg_subs_lines else "  (KG 대체재 데이터 없음)"

    return (
        f"[현재 레시피: {recipe_current['recipe_name']}]\n"
        f"인분: {st.session_state['serving_count']}인분\n"
        f"조리 단계:\n{steps_summary}\n\n"
        f"[냉장고 보유 재료]: {fridge_list}\n"
        f"[부족한 재료]: {missing_list}\n"
        f"[KG 대체재 데이터 — 이 목록에 있는 재료만 추천 가능]:\n{kg_subs_str}"
    )

def _generate_technique_note(action: str, target: str, detail: str, substitute: str) -> str:
    """대체재 적용 후 해당 step의 technique_note를 LLM으로 새로 생성"""
    try:
        client = anthropic.Anthropic()
        prompt = (
            f"조리 단계: {action} — {target}\n"
            f"조리 설명: {detail}\n"
            f"사용 재료: {substitute}\n\n"
            f"위 조리 단계에서 '{substitute}'를 사용할 때의 실용적인 요리 팁을 "
            f"한 문장으로 작성해줘. 팁만 출력, 다른 텍스트 없이."
        )
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return f"{substitute}의 특성에 맞게 조리 시간과 화력을 조절하세요."


def call_claude_api(user_message: str) -> dict:
    """Claude API 호출 → JSON 파싱 → dict 반환"""
    client = anthropic.Anthropic()

    # 히스토리에서 user/assistant 교대 순서 보장
    raw_history = st.session_state["chat_history"][-20:]
    messages = []
    expected_role = "user"
    for msg in raw_history:
        if msg["role"] == expected_role:
            messages.append({"role": msg["role"], "content": msg["content"]})
            expected_role = "assistant" if expected_role == "user" else "user"

    # 마지막이 assistant로 끝났으면 비워서 user로 시작하게 맞춤
    if messages and messages[-1]["role"] == "assistant":
        pass  # 정상 — 다음 user 메시지 추가 예정

    # 현재 컨텍스트를 마지막 user 메시지에 주입
    full_user = f"{_build_user_context()}\n\n사용자 요청: {user_message}"
    messages.append({"role": "user", "content": full_user})

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        raw = response.content[0].text.strip()
        # JSON 펜스 제거
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        parsed = json.loads(raw)
        # 필수 키 기본값 보장
        parsed.setdefault("action", "none")
        parsed.setdefault("step_index", -1)
        parsed.setdefault("target", None)
        parsed.setdefault("substitute", None)
        parsed.setdefault("new_detail", None)
        parsed.setdefault("scale_factor", None)
        parsed.setdefault("modification_intent", False)
        parsed.setdefault("follow_up_chips", None)
        parsed.setdefault("summary", None)
        parsed.setdefault("chat_reply", "완료했어요!")
        print(f"[AI 응답 JSON] {parsed}")  # 디버그
        return parsed
    except json.JSONDecodeError as e:
        import traceback; traceback.print_exc()
        return {
            "action": "none", "step_index": -1,
            "target": None, "substitute": None,
            "scale_factor": None, "summary": None,
            "chat_reply": f"응답 형식 오류: {e}",
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {
            "action": "none", "step_index": -1,
            "target": None, "substitute": None,
            "scale_factor": None, "summary": None,
            "chat_reply": f"오류 상세: {type(e).__name__}: {e}",
        }

# ═══════════════════════════════════════════════════
# 7. 레시피 수정 적용 (정의서 3.3 apply_modification)
# ═══════════════════════════════════════════════════
def apply_modification(mod: dict):
    """LLM JSON 결과를 recipe_current에 반영. ask/none은 레시피 수정 없음"""
    action = mod.get("action", "none")

    # ask/none은 레시피 수정 없이 리턴
    if action in ("ask", "none"):
        return

    if action == "substitute":
        idx = mod.get("step_index", -1)
        target = mod.get("target", "")
        sub = mod.get("substitute", "")
        if 0 <= idx < len(recipe_current["steps"]) and target and sub:
            step = recipe_current["steps"][idx]
            # target 교체
            step["target"] = step["target"].replace(target, sub)
            # detail: LLM이 새로 작성한 new_detail 우선, 없으면 단순 replace
            new_detail = mod.get("new_detail")
            if new_detail:
                step["detail"] = new_detail
            else:
                step["detail"] = step["detail"].replace(target, sub)
            # technique_note를 LLM으로 새로 생성
            step["technique_note"] = _generate_technique_note(
                step["action"], step["target"], step["detail"], sub
            )
            print(f"[technique_note 수정 후] {step.get('technique_note')}")  # 디버그
            if mod.get("summary"):
                st.session_state["modification_log"].append(mod["summary"])

    elif action == "scale":
        factor = mod.get("scale_factor")
        if factor and factor > 0:
            new_servings = max(1, round(st.session_state["serving_count"] * factor))
            st.session_state["serving_count"] = new_servings
            if mod.get("summary"):
                st.session_state["modification_log"].append(mod["summary"])

# ═══════════════════════════════════════════════════
# 8. CSS
# ═══════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

/* 스텝 카드 */
.step-card {
    background: #fafafa;
    border-left: 4px solid #ff6b35;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 12px;
}
.step-card-modified {
    background: #eef4ff;
    border-left: 4px solid #1976d2;
}
.step-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.step-number {
    background: #ff6b35; color: white; font-weight: 700; font-size: 14px;
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.step-number-modified { background: #1976d2; }
.step-action { font-size: 17px; font-weight: 700; color: #1a1a1a; }
.step-detail { font-size: 14px; color: #333; margin-bottom: 12px; line-height: 1.8; white-space: pre-line; }
.modified-badge {
    display: inline-block; font-size: 11px; font-weight: 600;
    background: #1976d2; color: white;
    padding: 2px 8px; border-radius: 10px; margin-left: 8px;
}

/* 메타 칩 */
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.meta-chip { font-size: 12px; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
.chip-heat-강 { background: #ffe0e0; color: #c62828; }
.chip-heat-중 { background: #fff3e0; color: #e65100; }
.chip-heat-약 { background: #e8f5e9; color: #2e7d32; }
.chip-heat-없음 { background: #f5f5f5; color: #757575; }
.chip-time { background: #e3f2fd; color: #1565c0; }
.chip-condition { background: #f3e5f5; color: #6a1b9a; }

/* 팁 / 도구 */
.tip-box { background: #fff8e1; border-radius: 6px; padding: 8px 12px; font-size: 12px; color: #5d4037; margin-top: 6px; }
.tip-box::before { content: "💡 "; }
.tool-tag {
    display: inline-block; font-size: 11px;
    background: #eceff1; color: #546e7a;
    padding: 2px 8px; border-radius: 10px; margin-right: 4px; margin-top: 4px;
}
.ingr-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.ingr-chip {
    font-size: 12px; font-weight: 600;
    background: #e8f5e9; color: #2e7d32;
    padding: 3px 10px; border-radius: 12px;
    border: 1px solid #c8e6c9;
}

/* 시간 배너 */
.time-banner {
    background: linear-gradient(135deg, #ff6b35, #ff8a5c);
    color: white; border-radius: 10px; padding: 16px 20px; text-align: center;
}
.time-banner-label { font-size: 13px; opacity: 0.9; }
.time-banner-value { font-size: 30px; font-weight: 700; margin-top: 2px; }

/* 영양 바 */
.nutrition-bar {
    background: #f0f4ff; border: 1px solid #c5cae9; border-radius: 10px;
    padding: 10px 16px; display: flex; justify-content: space-around;
    flex-wrap: wrap; gap: 6px; margin-bottom: 16px;
}
.nutrition-item { text-align: center; }
.nutrition-item .label { font-size: 10px; color: #888; }
.nutrition-item .value { font-size: 15px; font-weight: 700; }

/* 수정 로그 배지 */
.mod-log {
    background: #e8f0fe; border: 1px solid #c5cae9;
    border-radius: 8px; padding: 8px 14px;
    font-size: 13px; color: #1a237e; margin-bottom: 12px;
}

/* 추천 칩 */
.chip-suggest {
    display: inline-block; cursor: pointer;
    background: #fff3e0; border: 1px solid #ffcc80;
    color: #e65100; font-size: 13px; font-weight: 500;
    padding: 6px 14px; border-radius: 20px; margin: 4px;
}

/* 채팅창 고정 높이 */
[data-testid="stChatMessageContainer"] { max-height: 420px; overflow-y: auto; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# 9. 페이지 헤더
# ═══════════════════════════════════════════════════
st.title(f'👨‍🍳 {recipe_current["recipe_name"]}')
st.caption(
    f'{recipe_current["method"]} · 기준 {recipe_current["base_servings"]}인분 · '
    f'약 {recipe_current["total_time_min"]}분'
)

# 영양 요약 바
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

# 수정 로그 배지 (정의서 3.6)
if st.session_state["modification_log"]:
    log_text = " | ".join(st.session_state["modification_log"])
    st.markdown(
        f'<div class="mod-log">📝 적용 중인 커스텀: {log_text}</div>',
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════
# 10. 인분 조절 + 총 시간 (정의서 3.4)
# ═══════════════════════════════════════════════════
col_srv, col_time = st.columns([1, 1])

with col_srv:
    # number_input은 session_state["serving_input"]과 직접 양방향 연동
    # 채팅/칩으로 serving_count 변경 시 serving_input도 같이 맞춰줌
    if st.session_state.get("serving_input") != st.session_state["serving_count"]:
        st.session_state["serving_input"] = st.session_state["serving_count"]

    st.number_input(
        "🍽️ 인분",
        min_value=1, max_value=10, step=1,
        key="serving_input",
    )
    st.session_state["serving_count"] = st.session_state["serving_input"]

target_servings = st.session_state["serving_count"]
scale_result = scale_recipe(recipe_current, target_servings)
total_scaled = scale_result["scaled_total_min"]

with col_time:
    st.markdown(
        f'<div class="time-banner">'
        f'<div class="time-banner-label">{target_servings}인분 예상 조리시간</div>'
        f'<div class="time-banner-value">약 {math.ceil(total_scaled)}분</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ═══════════════════════════════════════════════════
# 11. 메인 레이아웃: 좌(가이드) / 우(AI 코치)
#     정의서 3.3: st.columns([1.2, 1])
# ═══════════════════════════════════════════════════
col_guide, col_chat = st.columns([1.2, 1])

# ───────────────────────────────────────────────────
# 11-A. 좌측: 인터랙티브 조리 가이드
# ───────────────────────────────────────────────────
with col_guide:
    st.markdown("### 📋 조리 단계")

    # 진행률
    total_steps = len(recipe_current["steps"])
    completed = st.session_state.completed_steps
    progress = len(completed) / total_steps if total_steps > 0 else 0
    st.progress(progress, text=f"진행률: {len(completed)}/{total_steps} 단계 완료")

    for s in recipe_current["steps"]:
        step_num = s["step_number"]
        idx = step_num - 1  # 0-based

        # 원본과 비교해 수정 여부 판단 (정의서 3.3 수정 하이라이트)
        orig_step = recipe_original["steps"][idx] if idx < len(recipe_original["steps"]) else s
        is_modified = (s["target"] != orig_step["target"] or s["detail"] != orig_step["detail"])

        # 스케일된 시간
        scaled_info = next(
            (x for x in scale_result["steps"] if x["step_number"] == step_num), None
        )
        scaled_time = scaled_info["scaled_time_min"] if scaled_info else s["estimated_time_min"]
        time_str = round_to_quarter(scaled_time)

        # 메타 칩
        heat = s.get("heat_level", "없음")
        meta_chips = (
            f'<span class="meta-chip chip-heat-{heat}">🔥 {heat}</span>'
            f'<span class="meta-chip chip-time">⏱ {time_str}</span>'
        )
        if s.get("end_condition"):
            meta_chips += f'<span class="meta-chip chip-condition">🎯 {s["end_condition"]}</span>'

        # 재료 스케일링 렌더링
        ingr_html = ""
        step_ingredients = s.get("ingredients", [])
        print(f"[DEBUG] step {s['step_number']} ingredients: {step_ingredients}")  # 디버그
        if step_ingredients:
            base_srv = recipe_current["base_servings"]
            ratio = target_servings / base_srv if base_srv else 1
            ingr_items = []
            for ing in step_ingredients:
                scaled_amt = ing["amount"] * ratio
                # 단위별 표시 포맷
                unit = ing.get("unit", "")
                if unit in ("g", "ml"):
                    # 정수이면 정수로
                    amt_str = f"{int(scaled_amt)}" if scaled_amt == int(scaled_amt) else f"{scaled_amt:.1f}"
                elif unit in ("큰술", "작은술"):
                    amt_str = f"{scaled_amt:.1f}" if scaled_amt != int(scaled_amt) else f"{int(scaled_amt)}"
                elif unit == "개" or unit == "대" or unit == "마리" or unit == "공기":
                    amt_str = f"{scaled_amt:.1f}" if scaled_amt != int(scaled_amt) else f"{int(scaled_amt)}"
                else:
                    amt_str = f"{scaled_amt:.1f}" if scaled_amt != int(scaled_amt) else f"{int(scaled_amt)}"
                ingr_items.append(f'<span class="ingr-chip">{ing["name"]} {amt_str}{unit}</span>')
            ingr_html = f'<div class="ingr-row">{"".join(ingr_items)}</div>'

        tools_html = "".join(
            f'<span class="tool-tag">🔧 {t}</span>' for t in s.get("tools_used", [])
        )
        tip_html = f'<div class="tip-box">{s["technique_note"]}</div>' if s.get("technique_note") else ""

        # 완료 상태
        is_done = step_num in completed
        border_color = "#4caf50" if is_done else ("#1976d2" if is_modified else "#ff6b35")
        opacity = "opacity: 0.6;" if is_done else ""
        icon = "✓" if is_done else step_num
        num_class = "step-number-modified" if is_modified else ""
        card_extra = "step-card-modified" if is_modified else ""

        # 수정 배지
        modified_badge = '<span class="modified-badge">🔵 AI 수정됨</span>' if is_modified else ""

        card_html = (
            f'<div class="step-card {card_extra}" style="border-left-color: {border_color}; {opacity}">'
            f'<div class="step-header">'
            f'<div class="step-number {num_class}" style="background: {border_color};">{icon}</div>'
            f'<div class="step-action">{s["action"]} — {s["target"]}{modified_badge}</div>'
            f'</div>'
            f'<div class="step-detail">{s["detail"]}</div>'
            f'{ingr_html}'
            f'<div class="meta-row">{meta_chips}</div>'
            f'{tools_html}'
            f'{tip_html}'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        col_check, col_timer = st.columns([1, 1])
        with col_check:
            checked = st.checkbox(f"Step {step_num} 완료", value=is_done, key=f"done_{step_num}")
            if checked:
                completed.add(step_num)
            else:
                completed.discard(step_num)
            st.session_state.completed_steps = completed

        with col_timer:
            timer_sec = int(scaled_time * 60)
            mm, ss = timer_sec // 60, timer_sec % 60
            with st.expander(f"⏱ 타이머 ({time_str})"):
                timer_html = (
                    f'<div style="font-family:Noto Sans KR,sans-serif;text-align:center;padding:8px;">'
                    f'<div id="d-{step_num}" style="font-size:38px;font-weight:700;color:#1565c0;">'
                    f'{mm:02d}:{ss:02d}</div>'
                    f'<div style="display:flex;gap:6px;justify-content:center;margin-top:6px;">'
                    f'<button onclick="sT{step_num}()" style="padding:5px 14px;border:none;background:#ff6b35;color:white;border-radius:6px;cursor:pointer;">▶ 시작</button>'
                    f'<button onclick="pT{step_num}()" style="padding:5px 14px;border:none;background:#eceff1;border-radius:6px;cursor:pointer;">⏸ 정지</button>'
                    f'<button onclick="rT{step_num}()" style="padding:5px 14px;border:none;background:#eceff1;border-radius:6px;cursor:pointer;">↺ 리셋</button>'
                    f'</div></div>'
                    f'<script>'
                    f'var r{step_num}={timer_sec},i{step_num}=null;'
                    f'function sT{step_num}(){{if(i{step_num})return;i{step_num}=setInterval(function(){{'
                    f'if(r{step_num}<=0){{clearInterval(i{step_num});i{step_num}=null;'
                    f'document.getElementById("d-{step_num}").style.color="#c62828";'
                    f'document.getElementById("d-{step_num}").innerText="완료!";return;}}'
                    f'r{step_num}--;var m=Math.floor(r{step_num}/60),s=r{step_num}%60;'
                    f'document.getElementById("d-{step_num}").innerText=String(m).padStart(2,"0")+":"+String(s).padStart(2,"0");}},1000);}}'
                    f'function pT{step_num}(){{clearInterval(i{step_num});i{step_num}=null;}}'
                    f'function rT{step_num}(){{clearInterval(i{step_num});i{step_num}=null;r{step_num}={timer_sec};'
                    f'var m=Math.floor({timer_sec}/60),s={timer_sec}%60;'
                    f'document.getElementById("d-{step_num}").style.color="#1565c0";'
                    f'document.getElementById("d-{step_num}").innerText=String(m).padStart(2,"0")+":"+String(s).padStart(2,"0");}}'
                    f'</script>'
                )
                st.components.v1.html(timer_html, height=110)

    # 조리 완료
    if len(completed) == total_steps and total_steps > 0:
        st.balloons()
        st.success("🎉 조리 완료!")

# ───────────────────────────────────────────────────
# 11-B. 우측: AI 코치 채팅창 (정의서 3.3 / 4)
# ───────────────────────────────────────────────────
with col_chat:
    st.markdown("### 🤖 AI 코치")

    # ── 추천 칩 영역 ──
    # missing 재료 칩 (최대 3개) + 인분 조절 고정 칩
    suggestion_chips = []
    for item in missing_items[:3]:
        subs = get_substitutes_for(item)
        has_in_fridge = any(s in fridge_ingredients for s in subs)
        label = f"🔄 {item} 대체재 보기" if has_in_fridge else f"❌ {item} 없이 만들기"
        suggestion_chips.append({"label": label, "message": f"{item} 대신 쓸 수 있는 재료 알려줘"})
    suggestion_chips.append({"label": "🍽️ 인분 조절하기", "message": "인분을 바꾸고 싶어"})

    if suggestion_chips:
        chip_cols = st.columns(len(suggestion_chips))
        for i, chip in enumerate(suggestion_chips):
            with chip_cols[i]:
                if st.button(chip["label"], key=f"suggest_{i}", use_container_width=True):
                    with st.spinner("AI 코치가 답변 중..."):
                        mod = call_claude_api(chip["message"])
                    apply_modification(mod)
                    st.session_state["chat_history"].append({"role": "user", "content": chip["label"]})
                    st.session_state["chat_history"].append({
                        "role": "assistant",
                        "content": mod["chat_reply"],
                        "follow_up_chips": mod.get("follow_up_chips"),
                    })
                    st.rerun()
        st.divider()

    # ── Reset 칩 (정의서 3.5) ──
    if st.session_state["modification_log"]:
        if st.button("🔄 #원본으로_돌리기", key="reset_chip"):
            st.session_state["recipe_current"] = copy.deepcopy(recipe_original)
            st.session_state["modification_log"] = []
            st.session_state["serving_count"] = recipe_original["base_servings"]
            st.session_state["chat_history"].append(
                {"role": "assistant", "content": "원본 레시피로 초기화했습니다!"}
            )
            st.rerun()

    # ── 대화 히스토리 렌더링 ──
    for msg_idx, msg in enumerate(st.session_state["chat_history"]):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
        # follow_up_chips — 마지막 assistant 메시지에만 표시
        chips = msg.get("follow_up_chips")
        is_last = msg_idx == len(st.session_state["chat_history"]) - 1
        if chips and msg["role"] == "assistant" and is_last:
            fu_cols = st.columns(min(len(chips), 4))
            for ci, chip_label in enumerate(chips):
                with fu_cols[ci % 4]:
                    if st.button(chip_label, key=f"fu_{msg_idx}_{ci}", use_container_width=True):
                        # 인분 선택 칩 ("N인분" 패턴)은 로컬에서 직접 처리
                        import re as _re
                        serving_m = _re.match(r"^(\d+)인분$", chip_label.strip())
                        if serving_m:
                            target_n = int(serving_m.group(1))
                            st.session_state["serving_count"] = target_n
                            st.session_state["modification_log"].append(
                                f"{target_n}인분으로 조절"
                            )
                            st.session_state["chat_history"].append({"role": "user", "content": chip_label})
                            st.session_state["chat_history"].append({
                                "role": "assistant",
                                "content": f"{target_n}인분으로 조절했어요! 조리 시간이 자동 반영됩니다.",
                                "follow_up_chips": None,
                            })
                        else:
                            with st.spinner("AI 코치가 답변 중..."):
                                mod = call_claude_api(chip_label)
                            apply_modification(mod)
                            st.session_state["chat_history"].append({"role": "user", "content": chip_label})
                            st.session_state["chat_history"].append({
                                "role": "assistant",
                                "content": mod["chat_reply"],
                                "follow_up_chips": mod.get("follow_up_chips"),
                            })
                        st.rerun()

    # ── 채팅 입력 (정의서 3.3) ──
    if prompt := st.chat_input("질문하세요 (예: 양파 대신 뭐 쓸 수 있어? / 3인분으로 늘려줘)"):
        # 인분 파싱 시도 (채팅 명령 — 정의서 3.4)
        serving_match = re.search(r"(\d+)\s*인분", prompt)
        if serving_match:
            target_n = int(serving_match.group(1))
            st.session_state["serving_count"] = target_n
            st.session_state["modification_log"].append(f"{target_n}인분으로 조절")
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": f"{target_n}인분으로 조절했어요! 조리 시간이 자동 반영됩니다.",
                "follow_up_chips": None,
            })
        else:
            # LLM 호출 — user push 전에 먼저 호출해야 히스토리 중복 방지
            with st.spinner("AI 코치가 답변 중..."):
                mod = call_claude_api(prompt)
            apply_modification(mod)
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": mod["chat_reply"],
                "follow_up_chips": mod.get("follow_up_chips"),
            })

        st.rerun()

# ═══════════════════════════════════════════════════
# 12. 푸터 & 네비게이션
# ═══════════════════════════════════════════════════
st.divider()
st.caption(
    f'🔬 시간 스케일링: t_scaled = t_base × (인분비)^α | '
    f'기준 {recipe_current["base_servings"]}인분 → {target_servings}인분'
)

col_back, col_home = st.columns(2)
with col_back:
    if st.button("← 추천 결과", use_container_width=True):
        st.switch_page("pages/4_추천결과.py")
with col_home:
    if st.button("🏠 처음으로", use_container_width=True):
        st.session_state.completed_steps = set()
        st.session_state.recipe_original = None
        st.session_state.recipe_current = None
        st.session_state.chat_history = []
        st.session_state.modification_log = []
        st.switch_page("app.py")