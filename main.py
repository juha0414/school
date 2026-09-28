

import streamlit as st
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="우리 학교 달력별 급식",
    page_icon="🍚",
    layout="wide"
)

st.title("🍚 우리 학교 달력별 급식")
st.write("송탄고등학교의 날짜별 중식 메뉴를 확인할 수 있습니다.")


# --------------------------------------------------
# 송탄고등학교 고정 정보
# --------------------------------------------------

SCHOOL_NAME = "송탄고등학교"
ATPT_OFCDC_SC_CODE = "J10"
SD_SCHUL_CODE = "7530480"

MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

KST = ZoneInfo("Asia/Seoul")
TODAY_KST = datetime.now(KST).date()


# --------------------------------------------------
# 급식 API
# --------------------------------------------------

@st.cache_data(ttl=1800)
def get_meal(target_date):
    """
    선택한 하루의 송탄고등학교 중식 정보를 조회한다.
    인증키 없이 사용한다.
    """

    date_text = target_date.strftime("%Y%m%d")

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": date_text,
        "MLSV_TO_YMD": date_text,
        "pSize": 10,
        "pIndex": 1
    }

    try:
        response = requests.get(
            MEAL_API_URL,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        return None, "NETWORK_ERROR"

    except ValueError:
        return None, "JSON_ERROR"

    # 데이터가 없는 경우
    if "RESULT" in data:
        result = data["RESULT"]

        if isinstance(result, dict):
            code = result.get("CODE")

            if code == "INFO-200":
                return [], "NO_DATA"

            return None, code

    if "mealServiceDietInfo" not in data:
        return [], "NO_DATA"

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (IndexError, KeyError, TypeError):
        return [], "NO_DATA"

    if not rows:
        return [], "NO_DATA"

    return rows, "OK"


# --------------------------------------------------
# 메뉴 처리
# --------------------------------------------------

def clean_menu_text(menu_text):
    """
    <br/>를 줄바꿈으로 변경하고
    불필요한 HTML 태그를 제거한다.
    """

    text = menu_text.replace("<br/>", "\n")
    text = text.replace("<br />", "\n")
    text = text.replace("<br>", "\n")

    text = re.sub(r"<[^>]+>", "", text)

    return text.strip()


def remove_allergy_number(menu):
    """
    메뉴 이름 뒤의 알레르기 번호를 제거한다.

    예:
    쌀밥(5) -> 쌀밥
    닭갈비(5.6.15) -> 닭갈비
    """

    return re.sub(r"\s*\([\d.]+\)\s*$", "", menu).strip()


def split_menu(menu_text):
    """
    급식 전체 문자열을 메뉴별로 분리한다.
    """

    cleaned = clean_menu_text(menu_text)

    menus = [
        menu.strip()
        for menu in cleaned.splitlines()
        if menu.strip()
    ]

    return menus


# --------------------------------------------------
# CSS
# --------------------------------------------------

st.markdown(
    """
    <style>
    .meal-card {
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 12px;
        background-color: #ffffff;
        min-height: 80px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .meal-card-title {
        font-size: 1.1rem;
        font-weight: 600;
        line-height: 1.5;
        color: #222222;
    }

    .school-name {
        font-size: 1.15rem;
        color: #666666;
        margin-bottom: 15px;
    }

    .metric-card {
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 18px;
        text-align: center;
        background-color: #fafafa;
    }

    .metric-label {
        font-size: 0.95rem;
        color: #666666;
        margin-bottom: 5px;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #222222;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# 날짜 + 알레르기 스위치
# --------------------------------------------------

date_col, allergy_col = st.columns([2, 1])

with date_col:
    selected_date = st.date_input(
        "📅 날짜",
        value=TODAY_KST,
        format="YYYY-MM-DD"
    )

with allergy_col:
    st.write("")
    st.write("")
    show_allergy = st.toggle(
        "알레르기 정보 보기",
        value=True
    )


# --------------------------------------------------
# 선택 날짜 표시
# --------------------------------------------------

weekday_names = [
    "월요일",
    "화요일",
    "수요일",
    "목요일",
    "금요일",
    "토요일",
    "일요일"
]

weekday = weekday_names[selected_date.weekday()]

st.markdown(
    f"### {selected_date.strftime('%Y년 %m월 %d일')} · {weekday}"
)

st.markdown(
    f'<div class="school-name">🏫 {SCHOOL_NAME} · 중식</div>',
    unsafe_allow_html=True
)


# --------------------------------------------------
# 급식 조회
# --------------------------------------------------

with st.spinner("급식 정보를 불러오는 중..."):
    meal_rows, meal_status = get_meal(selected_date)


# --------------------------------------------------
# 급식이 없는 경우
# --------------------------------------------------

if meal_status == "NO_DATA" or not meal_rows:

    st.info("🍽️ 급식이 없는 날입니다")


# --------------------------------------------------
# API 오류
# --------------------------------------------------

elif meal_status != "OK":

    st.error(
        "급식 정보를 불러오지 못했습니다. "
        "잠시 후 다시 시도해 주세요."
    )


# --------------------------------------------------
# 급식 표시
# --------------------------------------------------

else:

    meal = meal_rows[0]

    menu_text = meal.get("DDISH_NM", "")
    calorie = meal.get("CAL_INFO", "")

    menus = split_menu(menu_text)

    # 알레르기 번호 표시 여부
    if not show_allergy:
        display_menus = [
            remove_allergy_number(menu)
            for menu in menus
        ]
    else:
        display_menus = menus

    # --------------------------------------------------
    # 메뉴 가짓수 + 칼로리 큰 숫자 카드
    # --------------------------------------------------

    metric1, metric2 = st.columns(2)

    with metric1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">🍱 메뉴 가짓수</div>
                <div class="metric-value">{len(menus)}개</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with metric2:
        calorie_display = calorie if calorie else "정보 없음"

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">🔥 칼로리</div>
                <div class="metric-value">{calorie_display}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("")

    # --------------------------------------------------
    # 메뉴 카드
    # --------------------------------------------------

    st.subheader("🍚 오늘의 메뉴")

    if display_menus:

        # 화면 너비에 따라 3개씩 카드 배치
        for i in range(0, len(display_menus), 3):

            cols = st.columns(3)

            for j, col in enumerate(cols):

                index = i + j

                if index < len(display_menus):

                    menu = display_menus[index]

                    with col:
                        st.markdown(
                            f"""
                            <div class="meal-card">
                                <div class="meal-card-title">
                                    {menu}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

    else:
        st.info("메뉴 정보가 없습니다.")

