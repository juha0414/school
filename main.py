

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

```python
import streamlit as st
import requests
import pandas as pd
import re
import plotly.express as px


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="우리 학교 메뉴별 급식",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 우리 학교 메뉴별 급식")
st.write(
    "송탄고등학교에서 2025년 9월부터 2026년 9월까지 "
    "중식으로 가장 자주 나온 메뉴를 확인합니다."
)


# --------------------------------------------------
# 고정 정보
# --------------------------------------------------

SCHOOL_NAME = "송탄고등학교"
ATPT_OFCDC_SC_CODE = "J10"
SD_SCHUL_CODE = "7530480"

MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

START_DATE = "20250901"
END_DATE = "20260930"

PAGE_SIZE = 1000


# --------------------------------------------------
# 메뉴 이름 정리
# --------------------------------------------------

def clean_menu_name(menu):
    """
    메뉴 이름 뒤에 붙은 알레르기 번호를 제거한다.

    예:
    김치찌개(5.6.9) -> 김치찌개
    돈까스(1.5.6.10) -> 돈까스
    """

    # 끝부분의 알레르기 번호 제거
    menu = re.sub(r"\s*\([\d.]+\)\s*$", "", menu)

    return menu.strip()


def split_menus(menu_text):
    """
    <br/> 기준으로 메뉴를 나눈다.
    """

    if not menu_text:
        return []

    text = menu_text.replace("<br/>", "\n")
    text = text.replace("<br />", "\n")
    text = text.replace("<br>", "\n")

    menus = []

    for line in text.splitlines():

        menu = line.strip()

        if not menu:
            continue

        menu = clean_menu_name(menu)

        if menu:
            menus.append(menu)

    return menus


# --------------------------------------------------
# API 한 페이지 조회
# --------------------------------------------------

def request_meal_page(api_key, page_index):
    """
    지정한 페이지의 급식 데이터를 요청한다.
    """

    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": page_index,
        "pSize": PAGE_SIZE,

        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,

        # 중식
        "MMEAL_SC_CODE": "2",

        "MLSV_FROM_YMD": START_DATE,
        "MLSV_TO_YMD": END_DATE
    }

    response = requests.get(
        MEAL_API_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


# --------------------------------------------------
# 전체 기간 데이터 가져오기
# --------------------------------------------------

@st.cache_data(ttl=3600)
def load_all_meals(api_key):
    """
    전체 건수를 먼저 확인한 뒤,
    1,000건씩 모든 페이지를 가져온다.
    """

    # ----------------------------------------------
    # 첫 페이지
    # ----------------------------------------------

    first_data = request_meal_page(
        api_key,
        1
    )

    # API 결과 코드 확인
    if "RESULT" in first_data:

        result = first_data["RESULT"]

        if isinstance(result, dict):

            code = result.get("CODE")
            message = result.get("MESSAGE", "")

            if code == "INFO-200":
                return [], 0, "NO_DATA"

            return [], 0, f"{code}: {message}"

    if "mealServiceDietInfo" not in first_data:
        return [], 0, "API 응답 형식을 확인할 수 없습니다."

    try:
        head = first_data["mealServiceDietInfo"][0]["head"]

        # head가 리스트인 경우
        if isinstance(head, list):
            list_total_count = int(
                head[0]["list_total_count"]
            )
        else:
            list_total_count = int(
                head["list_total_count"]
            )

        first_rows = first_data["mealServiceDietInfo"][1]["row"]

    except (KeyError, IndexError, TypeError, ValueError):

        return [], 0, "API 응답에서 전체 건수를 읽을 수 없습니다."

    # ----------------------------------------------
    # 첫 페이지 데이터 저장
    # ----------------------------------------------

    all_rows = list(first_rows)

    # ----------------------------------------------
    # 전체 페이지 수 계산
    # ----------------------------------------------

    total_pages = (
        list_total_count + PAGE_SIZE - 1
    ) // PAGE_SIZE

    # ----------------------------------------------
    # 나머지 페이지 요청
    # ----------------------------------------------

    if total_pages > 1:

        progress = st.progress(0)

        for page_index in range(2, total_pages + 1):

            data = request_meal_page(
                api_key,
                page_index
            )

            if "RESULT" in data:

                result = data["RESULT"]

                if isinstance(result, dict):

                    code = result.get("CODE")
                    message = result.get("MESSAGE", "")

                    return (
                        all_rows,
                        list_total_count,
                        f"{code}: {message}"
                    )

            try:
                rows = data["mealServiceDietInfo"][1]["row"]

            except (KeyError, IndexError, TypeError):

                rows = []

            all_rows.extend(rows)

            progress.progress(
                page_index / total_pages
            )

        progress.empty()

    return all_rows, list_total_count, "OK"


# --------------------------------------------------
# Secrets에서 인증키 가져오기
# --------------------------------------------------

try:
    API_KEY = st.secrets["NEIS_API_KEY"]

except Exception:

    st.error(
        "NEIS_API_KEY가 Streamlit Secrets에 설정되어 있지 않습니다."
    )

    st.stop()


# --------------------------------------------------
# 데이터 불러오기
# --------------------------------------------------

with st.spinner(
    "2025년 9월부터 2026년 9월까지의 중식 데이터를 불러오는 중입니다..."
):

    try:

        rows, total_count, status = load_all_meals(
            API_KEY
        )

    except requests.RequestException:

        st.error(
            "나이스 급식 API에 연결하지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )

        st.stop()

    except Exception as e:

        st.error(
            f"급식 데이터를 불러오는 중 문제가 발생했습니다: {e}"
        )

        st.stop()


# --------------------------------------------------
# 데이터 없음
# --------------------------------------------------

if status == "NO_DATA" or not rows:

    st.info(
        "선택한 기간에 급식 데이터가 없습니다."
    )

    st.stop()


# --------------------------------------------------
# API 오류
# --------------------------------------------------

if status != "OK":

    st.error(
        f"급식 데이터를 모두 불러오지 못했습니다.\n\n{status}"
    )

    st.stop()


# --------------------------------------------------
# 전체 데이터 처리
# --------------------------------------------------

df = pd.DataFrame(rows)

# 날짜 컬럼을 날짜형으로 변환
df["MLSV_YMD"] = pd.to_datetime(
    df["MLSV_YMD"],
    format="%Y%m%d",
    errors="coerce"
)

# 메뉴가 없는 행 제거
df = df[
    df["DDISH_NM"].notna()
].copy()


# --------------------------------------------------
# 날짜별 메뉴 집계
# --------------------------------------------------

menu_records = []

for _, row in df.iterrows():

    meal_date = row["MLSV_YMD"]
    menu_text = row.get("DDISH_NM", "")

    menus = split_menus(menu_text)

    # 같은 날 같은 메뉴가 여러 번 나오더라도
    # 하루에 한 번만 기록
    unique_menus = set(menus)

    for menu in unique_menus:

        menu_records.append(
            {
                "date": meal_date,
                "menu": menu
            }
        )


menu_df = pd.DataFrame(menu_records)


# --------------------------------------------------
# 데이터가 없는 경우
# --------------------------------------------------

if menu_df.empty:

    st.info(
        "집계할 메뉴 데이터가 없습니다."
    )

    st.stop()


# --------------------------------------------------
# 메뉴별 나온 날짜 수
# --------------------------------------------------

menu_days = (
    menu_df
    .drop_duplicates(
        subset=["date", "menu"]
    )
    .groupby("menu")
    .size()
    .reset_index(name="days")
)


# --------------------------------------------------
# 실제 급식이 있었던 날짜 수
# --------------------------------------------------

meal_days = (
    menu_df["date"]
    .dropna()
    .nunique()
)


# --------------------------------------------------
# 비율 계산
# --------------------------------------------------

menu_days["ratio"] = (
    menu_days["days"]
    / meal_days
    * 100
)


# --------------------------------------------------
# 내림차순 정렬
# --------------------------------------------------

menu_days = menu_days.sort_values(
    by=["days", "menu"],
    ascending=[False, True]
).reset_index(drop=True)


# --------------------------------------------------
# 순위
# --------------------------------------------------

menu_days["rank"] = (
    menu_days.index + 1
)


# --------------------------------------------------
# 상위 메뉴
# --------------------------------------------------

top_menu = menu_days.iloc[0]

top_menu_name = top_menu["menu"]
top_menu_days = int(top_menu["days"])
top_menu_ratio = float(top_menu["ratio"])


# --------------------------------------------------
# 상단 설명
# --------------------------------------------------

st.caption(
    f"조회 기간: 2025년 9월 1일 ~ 2026년 9월 30일 · "
    f"중식 · 총 API 데이터 {total_count:,}건"
)


# --------------------------------------------------
# 큰 숫자 카드
# --------------------------------------------------

card1, card2, card3 = st.columns(3)


with card1:

    st.metric(
        "🍽️ 집계한 날수",
        f"{meal_days:,}일"
    )


with card2:

    st.metric(
        "🥇 1위 메뉴",
        top_menu_name
    )


with card3:

    st.metric(
        "📊 1위 비율",
        f"{top_menu_ratio:.1f}%"
    )


st.divider()


# --------------------------------------------------
# 몇 위까지 볼지 선택
# --------------------------------------------------

max_rank = min(
    10,
    len(menu_days)
)

rank_count = st.slider(
    "📊 몇 위까지 볼까요?",
    min_value=1,
    max_value=max_rank,
    value=max_rank,
    step=1
)


# --------------------------------------------------
# TOP N 데이터
# --------------------------------------------------

chart_df = menu_days.head(
    rank_count
).copy()


# --------------------------------------------------
# 가로 막대그래프
# --------------------------------------------------

st.subheader(
    f"🍱 메뉴별 등장 빈도 TOP {rank_count}"
)

fig = px.bar(
    chart_df,
    x="days",
    y="menu",
    orientation="h",
    text="days",
    custom_data=["ratio"],
    labels={
        "days": "나온 날수",
        "menu": "메뉴"
    }
)


# 1위가 맨 위에 오도록 역순
fig.update_yaxes(
    categoryorder="array",
    categoryarray=chart_df["menu"].tolist()[::-1]
)


# 값이 클수록 진한 색이 되도록
fig.update_traces(
    marker=dict(
        color=chart_df["days"],
        colorscale="Blues",
        showscale=False
    ),
    texttemplate="%{text}일",
    textposition="outside",
    hovertemplate=(
        "<b>%{y}</b><br>"
        "나온 날수: %{x}일<br>"
        "비율: %{customdata[0]:.1f}%"
        "<extra></extra>"
    )
)


fig.update_layout(
    height=max(
        420,
        rank_count * 55
    ),
    margin=dict(
        l=20,
        r=60,
        t=20,
        b=20
    ),
    xaxis=dict(
        dtick=1
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# --------------------------------------------------
# 메뉴별 일수 + 비율 표
# --------------------------------------------------

st.subheader("📋 메뉴별 나온 날수와 비율")

table_df = chart_df[
    ["rank", "menu", "days", "ratio"]
].copy()

table_df.columns = [
    "순위",
    "메뉴",
    "나온 날수",
    "비율"
]

table_df["나온 날수"] = (
    table_df["나온 날수"]
    .astype(int)
    .astype(str)
    + "일"
)

table_df["비율"] = (
    table_df["비율"]
    .map(lambda x: f"{x:.1f}%")
)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True
)
