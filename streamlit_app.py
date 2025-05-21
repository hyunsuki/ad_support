import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO
import re

def crawl_naver_powerlink_with_requests(keywords):
    data = []

    for keyword in keywords:
        query = requests.utils.quote(keyword)
        url = f"https://search.naver.com/search.naver?query={query}"

        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        powerlink_area = soup.select_one(".nad_area")
        if powerlink_area:
            powerlinks = powerlink_area.select(".lst_type li")
            if powerlinks:
                for ad in powerlinks:
                    # 광고 제목 가져오기 — a.site
                    title_element = ad.select_one("a.site")
                    title = title_element.text.strip() if title_element else "없음"

                    # 표시용 링크 가져오기 — a.lnk_url 텍스트
                    link_element = ad.select_one("a.lnk_url")
                    link = link_element.text.strip() if link_element else ""

                    data.append([keyword, title, link])
            else:
                data.append([keyword, "없음", ""])
        else:
            data.append([keyword, "없음", ""])

    return data

# Streamlit 앱 UI
st.title("네이버 파워링크 광고 크롤러")
st.write("네이버 검색에서 파워링크 광고를 크롤링하고 결과를 확인하세요.")

keywords_input = st.text_area("검색할 키워드를 입력하세요 (여러 키워드는 줄바꿈으로 구분)", "")
keywords = keywords_input.split("\n") if keywords_input else []

if st.button("크롤링 시작"):
    if keywords:
        with st.spinner("크롤링 중..."):
            results = crawl_naver_powerlink_with_requests(keywords)

        if results:
            st.write("크롤링된 결과:")
            df = pd.DataFrame(results, columns=["검색 키워드", "광고 제목", "표시용 링크"])
            st.dataframe(df)

            output = BytesIO()
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
