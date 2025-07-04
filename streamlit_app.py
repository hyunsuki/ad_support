import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO

def crawl_naver_powerlink_with_requests_both(keywords):
    data = []

    headers_mobile = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    }

    for keyword in keywords:
        query = requests.utils.quote(keyword)

        # PC 버전 크롤링
        url_pc = f"https://search.naver.com/search.naver?query={query}"
        response_pc = requests.get(url_pc)
        soup_pc = BeautifulSoup(response_pc.text, "html.parser")

        pc_powerlink_area = soup_pc.select_one(".nad_area")
        if pc_powerlink_area:
            powerlinks_pc = pc_powerlink_area.select(".lst_type li")
            for ad in powerlinks_pc:
                title_element = ad.select_one("a.site")
                title = title_element.text.strip() if title_element else "없음"

                link_element = ad.select_one("a.lnk_url")
                link = link_element.text.strip() if link_element else ""

                data.append([keyword, title, link, "PC"])

        # 모바일 버전 크롤링
        url_mo = f"https://m.search.naver.com/search.naver?query={query}"
        response_mo = requests.get(url_mo, headers=headers_mobile)
        soup_mo = BeautifulSoup(response_mo.text, "html.parser")

        mo_powerlink_area = soup_mo.select_one(".lst_type")
        if mo_powerlink_area:
            powerlinks_mo = mo_powerlink_area.select("li")
            for ad in powerlinks_mo:
                title_element = ad.select_one(".tit")
                title = title_element.text.strip() if title_element else "없음"

                link_element = ad.select_one("a")
                link = link_element.get("href") if link_element else ""

                data.append([keyword, title, link, "MO"])

    return data

# Streamlit 앱 UI
st.title("네이버 파워링크 광고 크롤러")
st.write("네이버 검색에서 파워링크 광고를 PC/모바일 각각 크롤링하고 결과를 확인하세요.")

keywords_input = st.text_area("검색할 키워드를 입력하세요 (여러 키워드는 줄바꿈으로 구분)", "")
keywords = keywords_input.split("\n") if keywords_input else []

if st.button("크롤링 시작"):
    if keywords:
        with st.spinner("크롤링 중..."):
            results = crawl_naver_powerlink_with_requests_both(keywords)

        if results:
            st.write("크롤링된 결과:")
            df = pd.DataFrame(results, columns=["검색 키워드", "광고 제목", "표시용 링크", "구분 (PC/MO)"])
            st.dataframe(df)

            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="엑셀 파일 다운로드",
                data=output,
                file_name="naver_powerlink_pc_mo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("키워드를 입력해 주세요.")
