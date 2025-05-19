import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO  # 수정된 부분

def crawl_naver_powerlink_with_requests(keywords):
    data = []

    for keyword in keywords:
        query = requests.utils.quote(keyword)
        url = f"https://search.naver.com/search.naver?query={query}"

        # 요청을 보내고, HTML 파싱
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # 파워링크 영역 찾기
        powerlink_area = soup.select_one(".nad_area")
        if powerlink_area:
            powerlinks = powerlink_area.select(".lst_type li")
            if powerlinks:
                for ad in powerlinks:
                    title_element = ad.select_one("a.site")
                    title = title_element.text.strip() if title_element else "제목 없음"
                    link_element = ad.select_one("a.site")
                    #link = link_element.get("href") if link_element else "링크 없음"
                    link = link_element.text if link_element else "링크 없음"
                    data.append([keyword, title, link])
            else:
                data.append([keyword, "광고 없음", ""])
        else:
            data.append([keyword, "광고 없음", ""])

    return data

# Streamlit 앱 UI
st.title("네이버 파워링크 광고 크롤러")
st.write("네이버 검색에서 파워링크 광고를 크롤링하고 결과를 확인하세요.")

# 사용자로부터 키워드 입력 받기
keywords_input = st.text_area("검색할 키워드를 입력하세요 (여러 키워드는 줄바꿈으로 구분)", "")
keywords = keywords_input.split("\n") if keywords_input else []

if st.button("크롤링 시작"):
    if keywords:
        # 크롤링 시작
        with st.spinner("크롤링 중..."):
            results = crawl_naver_powerlink_with_requests(keywords)

        # 결과 출력
        if results:
            st.write("크롤링된 결과:")
            df = pd.DataFrame(results, columns=["검색 키워드", "광고 제목", "광고 링크"])
            st.dataframe(df)

            # 엑셀 파일로 저장
            output = BytesIO()  # 수정된 부분
            df.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="엑셀 파일 다운로드",
                data=output,
                file_name="naver_powerlink_requests.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("키워드를 입력해 주세요.")
