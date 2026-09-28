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
# 기본 정보
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
    menu = re.sub(r"\s*\([\d.]+\)\s*$", "", menu)
    return menu.strip()


def split_menus(menu_text):
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
# API 한 페이지 가져오기
# --------------------------------------------------

def request_meal_page(api_key, page_index):

    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": page_index,
        "pSize": PAGE_SIZE,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
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
# 전체 급식 데이터 가져오기
# --------------------------------------------------

@st.cache_data(ttl=3600)
def load_all_meals(api_key):

    # 첫 번째 페이지
    first_data = request_meal_page(
        api_key,
        1
    )

    # API 오류 확인
    if "RESULT" in first_data:

        result = first_data["RESULT"]

        if isinstance(result, dict):

            code = result.get("CODE")
            message = result.get("MESSAGE", "")

            if code == "INFO-200":
                return [], 0, "NO_DATA"

            return [], 0, f"{code}: {message}"

    # 급식 데이터가 없는 경우
    if "mealServiceDietInfo" not in first_data:
        return [], 0, "급식 API 응답을 확인할 수 없습니다."

    try:

        head = first_data["mealServiceDietInfo"][0]["head"]

        if isinstance(head, list):
            total_count = int(
                head[0]["list_total_count"]
            )
        else:
            total_count = int(
                head["list_total_count"]
            )

        first_rows = first_data["mealServiceDietInfo"][1]["row"]

    except (KeyError, IndexError, TypeError, ValueError):

        return [], 0, "전체 데이터 건수를 읽을 수 없습니다."

    # 첫 번째 페이지 저장
    all_rows = list(first_rows)

    # 필요한 전체 페이지 수
    total_pages = (
        total_count + PAGE_SIZE - 1
    ) // PAGE_SIZE

    # 두 번째 페이지부터 끝까지 요청
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
                        total_count,
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

    return all_rows, total_count, "OK"


# --------------------------------------------------
# Secrets에서 인증키 가져오기
# --------------------------------------------------

if "NEIS_API_KEY" not in st.secrets:

    st.error(
        "NEIS_API_KEY가 Streamlit Secrets에 설정되어 있지 않습니다."
    )

    st.stop()

API_KEY = st.secrets["NEIS_API_KEY"]


# --------------------------------------------------
# 데이터 가져오기
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
            "잠시 후 다시 실행해 주세요."
        )

        st.stop()

    except Exception as e:

        st.error(
            f"급식 데이터를 불러오는 중 문제가 발생했습니다: {e}"
        )

        st.stop()


# --------------------------------------------------
# 데이터가 없는 경우
# --------------------------------------------------

if status == "NO_DATA" or not rows:

    st.info(
        "선택한 기간에 중식 데이터가 없습니다."
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
# DataFrame 만들기
# --------------------------------------------------

df = pd.DataFrame(rows)

df["MLSV_YMD"] = pd.to_datetime(
    df["MLSV_YMD"],
    format="%Y%m%d",
    errors="coerce"
)

df = df[
    df["DDISH_NM"].notna()
].copy()


# --------------------------------------------------
# 날짜별 메뉴 분리
# --------------------------------------------------

menu_records = []

for _, row in df.iterrows():

    meal_date = row["MLSV_YMD"]
    menu_text = row.get("DDISH_NM", "")

    menus = split_menus(menu_text)

    # 같은 날 같은 메뉴가 여러 번 있어도
    # 하루에 한 번만 세기
    unique_menus = set(menus)

    for menu in unique_menus:

        menu_records.append(
            {
                "date": meal_date,
                "menu": menu
            }
        )


menu_df = pd.DataFrame(menu_records)


if menu_df.empty:

    st.info(
        "집계할 메뉴 데이터가 없습니다."
    )

    st.stop()


# --------------------------------------------------
# 같은 날짜 같은 메뉴 중복 제거
# --------------------------------------------------

menu_df = menu_df.drop_duplicates(
    subset=["date", "menu"]
)


# --------------------------------------------------
# 메뉴별 나온 날짜 수
# --------------------------------------------------

menu_days = (
    menu_df
    .groupby("menu")
    .size()
    .reset_index(name="days")
)


# --------------------------------------------------
# 실제 메뉴가 기록된 날짜 수
# --------------------------------------------------

meal_days = menu_df["date"].nunique()


# --------------------------------------------------
# 비율 계산
# --------------------------------------------------

menu_days["ratio"] = (
    menu_days["days"]
    / meal_days
    * 100
)


# --------------------------------------------------
# 많이 나온 순서대로 정렬
# --------------------------------------------------

menu_days = menu_days.sort_values(
    by=["days", "menu"],
    ascending=[False, True]
).reset_index(drop=True)


# --------------------------------------------------
# 순위
# --------------------------------------------------

menu_days["rank"] = menu_days.index + 1


# --------------------------------------------------
# 1위 정보
# --------------------------------------------------

top_menu = menu_days.iloc[0]

top_menu_name = top_menu["menu"]
top_menu_days = int(top_menu["days"])
top_menu_ratio = float(top_menu["ratio"])


# --------------------------------------------------
# 설명
# --------------------------------------------------

st.caption(
    "조회 기간: 2025년 9월 1일 ~ 2026년 9월 30일 · "
    f"중식 · 전체 API 데이터 {total_count:,}건"
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
# TOP N
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
    },
    color="days",
    color_continuous_scale="Blues"
)


# 1위가 맨 위에 오도록 설정
fig.update_yaxes(
    categoryorder="array",
    categoryarray=chart_df["menu"].tolist()[::-1]
)


fig.update_traces(
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
    coloraxis_showscale=False
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# --------------------------------------------------
# 표
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
