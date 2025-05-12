import time
import re
from datetime import datetime
import pandas as pd
import streamlit as st
from seleniumwire import webdriver
from undetected_chromedriver.v2 import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import urllib.parse
from io import BytesIO

# Selenium WebDriver 설정
def get_selenium_driver():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")  # 브라우저 창을 표시하지 않음
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    driver = Chrome(options=chrome_options)
    return driver

# 네이버 파워링크 광고 크롤링 함수
def crawl_naver_powerlink_selenium_wire(keywords):
    driver = get_selenium_driver()
    
    data = []

    for keyword in keywords:
        query = urllib.parse.quote(keyword)
        url = f"https://search.naver.com/search.naver?query={query}"

        driver.get(url)

        # 페이지 로딩 대기
        time.sleep(3)  # 동적 요소들이 로드될 시간을 줍니다.

        # 파워링크 영역 찾기
        try:
            powerlink_area = driver.find_element(By.CLASS_NAME, "nad_area")
            powerlinks = powerlink_area.find_elements(By.CSS_SELECTOR, ".lst_type li")
        except Exception as e:
            print(f"[{keyword}] 파워링크 광고를 찾지 못했습니다.")
            data.append([keyword, "광고 없음", ""])
            continue

        if not powerlinks:
            print(f"[{keyword}] 파워링크 광고를 찾지 못했습니다.")
            data.append([keyword, "광고 없음", ""])
        else:
            for ad in powerlinks:
                title_element = ad.find_element(By.CSS_SELECTOR, "a.site")
                title = title_element.text.strip() if title_element else "제목 없음"

                link_element = ad.find_element(By.CSS_SELECTOR, "a.site")
                link = link_element.get_attribute("href") if link_element else "링크 없음"

                data.append([keyword, title, link])

    driver.quit()

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
            results = crawl_naver_powerlink_selenium_wire(keywords)

        # 결과 출력
        if results:
            st.write("크롤링된 결과:")
            df = pd.DataFrame(results, columns=["검색 키워드", "광고 제목", "광고 링크"])
            st.dataframe(df)

            # 엑셀 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"naver_powerlink_selenium_wire_{timestamp}.xlsx"
            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="엑셀 파일 다운로드",
                data=output,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("키워드를 입력해 주세요.")
