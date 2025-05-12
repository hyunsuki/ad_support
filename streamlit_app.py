import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from datetime import datetime
import os

def crawl_naver_powerlink(keywords):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")  # streamlit용 headless 모드

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    data = []

    for keyword in keywords:
        driver.get("https://www.naver.com")

        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "query"))
            )
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "nad_area"))
            )
        except:
            data.append([keyword, "없음", ""])
            continue

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        powerlinks = soup.select(".nad_area .lst_type > li")

        if not powerlinks:
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

    if data:
        df = pd.DataFrame(data, columns=["검색 키워드", "광고 제목", "광고 링크"])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"naver_powerlink_{timestamp}.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        return df, filename
    else:
        return None, None


# Streamlit UI 구성
st.title("네이버 파워링크 광고 크롤러")
st.markdown("네이버 검색결과의 파워링크 광고 제목과 링크를 수집합니다.")

keywords_input = st.text_area("🔍 크롤링할 키워드 (줄바꿈으로 구분)", height=200)
if st.button("크롤링 시작"):
    if not keywords_input.strip():
        st.warning("키워드를 입력해 주세요.")
    else:
        keywords = [kw.strip() for kw in keywords_input.strip().split("\n") if kw.strip()]
        with st.spinner("크롤링 중... 브라우저가 자동으로 열리고 종료됩니다."):
            result_df, filename = crawl_naver_powerlink(keywords)

        if result_df is not None:
            st.success(f"크롤링 완료! 총 {len(result_df)}건 수집.")
            st.dataframe(result_df)

            with open(filename, "rb") as f:
                st.download_button(
                    label="📥 엑셀 파일 다운로드",
                    data=f,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            os.remove(filename)
        else:
            st.error("크롤링된 데이터가 없습니다.")
