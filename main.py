```python
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import re


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🍚",
    layout="wide"
)

st.title("🍚 학교 급식 찾아보기")
st.write("학교를 검색하고 날짜를 선택하면 그날의 중식 메뉴를 확인할 수 있습니다.")


SCHOOL_API_URL = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

KST = ZoneInfo("Asia/Seoul")
TODAY_KST = datetime.now(KST).date()


# --------------------------------------------------
# 학교 이름 검색어 변환
# --------------------------------------------------

def make_search_words(keyword):
    """
    처음에는 입력한 학교 이름 그대로 검색하고,
    검색 결과가 없을 경우 줄임말을 풀어서 다시 검색한다.
    """

    words = [keyword.strip()]

    # '여고'를 '여자고등학교'로 변경
    if "여고" in keyword:
        expanded = keyword.replace("여고", "여자고등학교")
        if expanded not in words:
            words.append(expanded)

    # '고'를 '고등학교'로 변경
    # 이미 '고등학교'가 포함된 경우에는 변경하지 않는다.
    if "고" in keyword and "고등학교" not in keyword:
        expanded = keyword.replace("고", "고등학교")
        if expanded not in words:
            words.append(expanded)

    return words


# --------------------------------------------------
# 학교 정보 API
# --------------------------------------------------

@st.cache_data(ttl=3600)
def search_school(keyword):
    """
    학교 이름으로 나이스 학교기본정보 API를 검색한다.
    인증키 없이 조회한다.
    """

    params = {
        "Type": "json",
        "SCHUL_NM": keyword,
        "pSize": 5
    }

    try:
        response = requests.get(
            SCHOOL_API_URL,
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

    except requests.RequestException:
        return None, "NETWORK_ERROR"

    except ValueError:
        return None, "JSON_ERROR"

    # 조회 결과가 없는 경우
    if "RESULT" in data:
        result = data["RESULT"]

        if isinstance(result, dict):
            code = result.get("CODE")

            if code == "INFO-200":
                return [], "NO_DATA"

            return None, code

    # schoolInfo가 없는 경우
    if "schoolInfo" not in data:
        return [], "NO_DATA"

    try:
        rows = data["schoolInfo"][1]["row"]
    except (IndexError, KeyError, TypeError):
        return [], "NO_DATA"

    if not rows:
        return [], "NO_DATA"

    return rows, "OK"


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------

def find_schools(keyword):
    """
    입력한 학교 이름으로 먼저 검색하고,
    결과가 없을 경우 줄임말을 풀어 다시 검색한다.
    """

    search_words = make_search_words(keyword)

    for word in search_words:
        schools, status = search_school(word)

        if status == "OK" and schools:
            return schools, word

        if status not in ["OK", "NO_DATA"]:
            return None, word

    return [], None


# --------------------------------------------------
# 급식 API
# --------------------------------------------------

@st.cache_data(ttl=1800)
def get_meal(
    education_code,
    school_code,
    target_date
):
    """
    선택한 학교의 선택 날짜 중식 정보를 가져온다.
    """

    date_text = target_date.strftime("%Y%m%d")

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": education_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": date_text,
        "MLSV_TO_YMD": date_text,
        "pSize": 1000,
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

    # 조회 결과가 없는 경우
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
# 알레르기 번호 추출
# --------------------------------------------------

def extract_allergy_numbers(menu_text):
    """
    메뉴에 포함된 괄호 안 숫자를 알레르기 번호로 추출한다.

    예:
    쌀밥(5)
    닭갈비(5.6.15)
    """

    numbers = re.findall(r"\(([\d.]+)\)", menu_text)

    result = []

    for item in numbers:
        for number in item.split("."):
            if number and number not in result:
                result.append(number)

    return result


# --------------------------------------------------
# 메뉴 표시용 처리
# --------------------------------------------------

def clean_menu_text(menu_text):
    """
    <br/>를 줄바꿈으로 변경한다.
    HTML 태그가 남아 있을 경우 제거한다.
    """

    if not menu_text:
        return ""

    text = menu_text.replace("<br/>", "\n")
    text = text.replace("<br />", "\n")
    text = text.replace("<br>", "\n")

    # 남아 있는 HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)

    return text.strip()


def split_menu(menu_text):
    """
    급식 메뉴를 줄 단위로 나눈다.
    """

    text = clean_menu_text(menu_text)

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


# --------------------------------------------------
# 화면 - 학교 검색
# --------------------------------------------------

st.subheader("🏫 학교 선택")

school_keyword = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 수도여고, 서울고, 현대청운고"
)

search_button = st.button(
    "학교 찾기",
    type="primary"
)


# --------------------------------------------------
# 학교 검색 실행
# --------------------------------------------------

if search_button:

    if not school_keyword.strip():
        st.warning("학교 이름을 입력해 주세요.")

    else:
        with st.spinner("학교를 찾고 있습니다..."):
            schools, searched_word = find_schools(
                school_keyword.strip()
            )

        if schools is None:
            st.error(
                "학교 정보를 불러오지 못했습니다. "
                "잠시 후 다시 시도해 주세요."
            )

        elif not schools:
            st.session_state["schools"] = []
            st.session_state["selected_school"] = None

            st.info(
                f"'{school_keyword.strip()}'에 해당하는 학교를 찾지 못했습니다. "
                "학교 이름을 확인해 주세요."
            )

        else:
            st.session_state["schools"] = schools
            st.session_state["selected_school"] = None
            st.session_state["searched_word"] = searched_word


# --------------------------------------------------
# 검색 결과 표시
# --------------------------------------------------

schools = st.session_state.get("schools", [])

if schools:

    searched_word = st.session_state.get(
        "searched_word",
        school_keyword
    )

    if searched_word != school_keyword.strip():
        st.info(
            f"'{school_keyword.strip()}'로 찾지 못해 "
            f"'{searched_word}'로 다시 검색했습니다."
        )

    school_options = []

    for school in schools:
        school_name = school.get("SCHUL_NM", "")
        region = school.get("LCTN_SC_NM", "")

        label = f"{school_name} — {region}"
        school_options.append(label)

    selected_index = st.selectbox(
        "학교를 선택하세요",
        options=range(len(school_options)),
        format_func=lambda i: school_options[i]
    )

    selected_school = schools[selected_index]

    st.session_state["selected_school"] = selected_school


# --------------------------------------------------
# 선택한 학교 정보
# --------------------------------------------------

selected_school = st.session_state.get(
    "selected_school"
)


if selected_school:

    school_name = selected_school["SCHUL_NM"]
    region = selected_school.get("LCTN_SC_NM", "")
    education_code = selected_school["ATPT_OFCDC_SC_CODE"]
    school_code = selected_school["SD_SCHUL_CODE"]

    st.divider()

    st.subheader(f"📍 {school_name}")

    st.caption(f"지역: {region}")

    # --------------------------------------------------
    # 날짜 선택
    # --------------------------------------------------

    selected_date = st.date_input(
        "급식 날짜",
        value=TODAY_KST,
        format="YYYY-MM-DD"
    )

    st.caption(
        f"선택한 날짜: {selected_date.strftime('%Y년 %m월 %d일')}"
    )

    # --------------------------------------------------
    # 급식 조회
    # --------------------------------------------------

    with st.spinner("급식 정보를 불러오는 중..."):
        meal_rows, meal_status = get_meal(
            education_code,
            school_code,
            selected_date
        )

    if meal_status == "NO_DATA" or not meal_rows:

        st.info(
            f"{selected_date.strftime('%Y년 %m월 %d일')}에는 "
            "중식 급식 정보가 없습니다."
        )

    elif meal_status != "OK":

        st.error(
            "급식 정보를 불러오지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )

    else:

        # 같은 날짜에 여러 행이 있을 가능성에 대비
        meal = meal_rows[0]

        menu_text = meal.get("DDISH_NM", "")
        calorie = meal.get("CAL_INFO", "")

        menu_items = split_menu(menu_text)
        allergy_numbers = extract_allergy_numbers(menu_text)

        st.subheader("🍚 중식")

        # --------------------------------------------------
        # 메뉴
        # --------------------------------------------------

        if menu_items:

            st.markdown("### 메뉴")

            for menu in menu_items:
                st.write(f"• {menu}")

        else:
            st.info("메뉴 정보가 없습니다.")

        # --------------------------------------------------
        # 알레르기 번호
        # --------------------------------------------------

        st.markdown("### 알레르기 번호")

        if allergy_numbers:
            st.write(", ".join(allergy_numbers))
        else:
            st.write("표시된 알레르기 번호가 없습니다.")

        # --------------------------------------------------
        # 칼로리
        # --------------------------------------------------

        st.markdown("### 🔥 칼로리")

        if calorie:
            st.write(calorie)
        else:
            st.write("칼로리 정보가 없습니다.")

        # --------------------------------------------------
        # 원본 메뉴
        # --------------------------------------------------

        with st.expander("원래 메뉴 데이터 보기"):
            st.code(
                menu_text,
                language=None
            )
```

### `requirements.txt`

```text
streamlit
requests
pandas
```
