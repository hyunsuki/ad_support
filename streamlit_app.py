import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime
import base64

# ✅ 드라이버 생성 함수 (Streamlit Cloud 환경용)
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    # Streamlit Cloud 환경용 경로
    chrome_options.binary_location = "/usr/bin/chromium-browser"

    driver = webdriver.Chrome(
        service=Service("/usr/lib/chromium-browser/chromedriver"),
        options=chrome_options
    )
    return driver

# ✅ 크롤링 함수
def crawl_naver_powerlink(keywords):
    driver = create_driver()
    data = []

    for keyword in keywords:
        driver.get("https://www.naver.com")
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "query"))
        )
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "nad_area"))
            )
        except:
            st.warning(f"[{keyword}] 파워링크 영역을 찾지 못했습니다.")
            data.append([keyword, "없음", ""])
            continue

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        powerlinks = soup.select(".nad_area .lst_type > li")

        if not powerlinks:
            st.warning(f"[{keyword}] 파워링크 광고를 찾지 못했습니다.")
            data.append([keyword, "없음", ""])
        else:
            for ad in powerlinks:
                title_element = ad.select_one("a.site")
                title = title_element.get_text(strip=True) if title_element else "제목 없음"

                link_element = ad.select_one("a.lnk_url")
                if link_element:
                    onclick_attr = link_element.get("onclick", "")
                    match = re.search(r"urlencode\('(.+?)'\)", onclick_attr)
                    link = match.group(1) if match else "링크 없음"
                else:
                    link = "링크 없음"

                data.append([keyword, title, link])

    driver.quit()
    return data

# ✅ 엑셀 다운로드 링크 생성 함수
def get_table_download_link(df, filename):
    towrite = pd.ExcelWriter(filename, engine='openpyxl')
    df.to_excel(towrite, index=False)
    towrite.close()

    with open(filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 엑셀 파일 다운로드</a>'
    return href

# ✅ Streamlit 앱 UI
st.title("네이버 파워링크 광고 크롤러")

keywords_input = st.text_area("크롤링할 키워드를 줄바꿈으로 입력하세요.")
if st.button("크롤링 시작"):
    if keywords_input.strip() == "":
        st.error("키워드를 입력하세요.")
    else:
        keywords = [kw.strip() for kw in keywords_input.strip().split("\n") if kw.strip()]

        with st.spinner("크롤링 중..."):
            result = crawl_naver_powerlink(keywords)

        if result:
            df = pd.DataFrame(result, columns=["검색 키워드", "광고 제목", "광고 링크"])
            st.success("크롤링 완료!")

            st.dataframe(df)

            # 다운로드 링크 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"naver_powerlink_{timestamp}.xlsx"

            # 엑셀 다운로드 링크 표시
            st.markdown(get_table_download_link(df, filename), unsafe_allow_html=True)
        else:
            st.warning("크롤링된 데이터가 없습니다.")
