# pages/2_메뉴별_급식.py — 인증키로 두 학기를 한 번에 받아 최다 등장 메뉴 TOP N
import re

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.title("🥇 조회 기간의 최다 등장 메뉴")


@st.cache_data
def load_lunch(frm, to, api_key):
    days = {}
    page = 1
    received = 0
    while True:
        response = requests.get(
            "https://open.neis.go.kr/hub/mealServiceDietInfo",
            params={
                "Type": "json", "KEY": api_key,
                "pSize": 1000, "pIndex": page,
                "ATPT_OFCDC_SC_CODE": "J10", "SD_SCHUL_CODE": "7530480",
                "MMEAL_SC_CODE": "2", "MLSV_FROM_YMD": frm, "MLSV_TO_YMD": to,
            }, timeout=20,
        )
        response.raise_for_status()
        res = response.json()
        if "mealServiceDietInfo" not in res:
            result = res.get("RESULT", {})
            if result.get("CODE") == "INFO-200" and page == 1:
                return {}
            raise ValueError("급식 데이터를 모두 받지 못했습니다. " + result.get("MESSAGE", "응답을 확인해 주세요."))
        head = res["mealServiceDietInfo"][0]["head"]
        total = next(item["list_total_count"] for item in head if "list_total_count" in item)
        rows = res["mealServiceDietInfo"][1]["row"]
        if not rows:
            raise ValueError(f"전체 {total}건인데 받은 행이 없습니다. 인증키를 확인해 주세요.")
        for row in rows:
            # 원본은 유지하고, 빈도 집계용 메뉴 이름에서만 알레르기 번호를 제거한다.
            dishes = [re.sub(r"\s*\([0-9.]+\)", "", d).strip() for d in row["DDISH_NM"].split("<br/>")]
            days.setdefault(row["MLSV_YMD"], set()).update(d for d in dishes if d)
        received += len(rows)
        if received >= total:
            return days
        if len(rows) < 1000:
            # 더 받을 쪽이 없는데 전체 건수에 못 미친다 — 인증키 없이 부른 경우다
            raise ValueError(
                f"전체 {total}건 가운데 {received}건만 받았습니다. 인증키를 확인해 주세요."
            )
        page += 1


try:
    api_key = st.secrets["NEIS_API_KEY"]
except Exception:
    st.error("Secrets 설정에 NEIS_API_KEY가 없습니다. 3절의 인증키 안내를 확인해 주세요.")
    st.stop()

try:
    meals = load_lunch("20250901", "20260930", api_key)
except (requests.RequestException, ValueError) as error:
    st.error(str(error))
    st.stop()
if not meals:
    st.info("조회 기간의 급식 정보가 없습니다.")
    st.stop()
days = len(meals)

counts = (pd.Series([d for dishes in meals.values() for d in dishes])
          .value_counts().rename_axis("메뉴").reset_index(name="일수"))
counts["비율(%)"] = (counts["일수"] / days * 100).round(0).astype(int)

# 몇 위까지 볼지 슬라이더로 고른다
top_n = st.slider("몇 위까지 볼까요?", min_value=5, max_value=20, value=10)
top = counts.head(top_n).copy()
top.insert(0, "순위", range(1, len(top) + 1))

# 큰 숫자 카드 셋 — 집계 일수, 1위 메뉴, 1위 비율
first = top.iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("집계한 날", f"{days}일")
c2.metric("1위 메뉴", first["메뉴"])
c3.metric("1위 등장 비율", f"{first['비율(%)']}% ({first['일수']}일)")

# 막대는 1위가 맨 위, 값이 클수록 진한 색, 막대마다 일수와 비율
top["표시"] = top["일수"].astype(str) + "일 (" + top["비율(%)"].astype(str) + "%)"
fig = px.bar(
    top.sort_values("일수"), x="일수", y="메뉴", orientation="h",
    text="표시", color="일수", color_continuous_scale="Oranges",
    title=f"중식 {days}일 중 가장 자주 나온 메뉴 TOP {top_n}",
)
fig.update_layout(coloraxis_showscale=False, xaxis_title="등장 일수", yaxis_title="")
st.plotly_chart(fig, width="stretch")

st.dataframe(top[["순위", "메뉴", "일수", "비율(%)"]], hide_index=True, width="stretch")
st.caption(f"중식 {days}일 기준 · 이 그래프로 알 수 있는 것: (한 문장으로 적어 보세요)")
