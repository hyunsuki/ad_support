import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from io import BytesIO
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ──────────────────────────────
# PC/모바일 공통 드라이버 생성기
# ──────────────────────────────
def get_driver(mobile=False):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    if mobile:
        options.add_argument("--window-size=375,812")
        options.add_argument(
            "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
    else:
        options.add_argument("--window-size=1920,1080")
    service = Service("/usr/bin/chromedriver")  # 필요 시 경로 수정
    return webdriver.Chrome(service=service, options=options)

# ──────────────────────────────
# 광고 title/link 유연하게 추출
# ──────────────────────────────
def extract_text_by_candidates(element, selectors):
    for sel in selectors:
        try:
            return element.find_element(By.CSS_SELECTOR, sel).text
        except:
            continue
    return "없음"

# ──────────────────────────────
# 메인 크롤링 함수
# ──────────────────────────────
def crawl_naver_powerlink_full(keywords):
    data = []
    pc_driver = get_driver(mobile=False)
    mobile_driver = get_driver(mobile=True)

    for keyword in keywords:
        q = requests.utils.quote(keyword)

        # PC 크롤링 (Selenium)
        url_pc = f"https://search.naver.com/search.naver?query={q}"
        pc_driver.get(url_pc)
        try:
            WebDriverWait(pc_driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.lst_type li"))
            )
            ads_pc = pc_driver.find_elements(By.CSS_SELECTOR, "div.lst_type li")
            for ad in ads_pc:
                title = extract_text_by_candidates(ad, [".site", ".ad_site", ".tit"])
                link = extract_text_by_candidates(ad, [".lnk_url", ".url", ".url_link"])
                data.append([keyword, title, link, "PC"])
        except:
            data.append([keyword, "없음", "", "PC"])

        # 모바일 크롤링 (Selenium)
        url_mo = f"https://m.ad.search.naver.com/search.naver?where=m_expd&query={q}&referenceId"
        mobile_driver.get(url_mo)
        try:
            time.sleep(2)
            for _ in range(3):
                mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

            try:
                btn = mobile_driver.find_element(By.LINK_TEXT, "광고 더보기")
                btn.click()
                time.sleep(1)
            except:
                pass

            mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            WebDriverWait(mobile_driver, 10).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ul#contentsList.powerlink_list li.list_item")
                )
            )
            ads_mo = mobile_driver.find_elements(
                By.CSS_SELECTOR, "ul#contentsList.powerlink_list li.list_item"
            )
            for ad in ads_mo:
                title = extract_text_by_candidates(ad, [".site", ".ad_site", ".txt_site", ".tit"])
                link = extract_text_by_candidates(ad, [".url_link", ".url", ".txt_url"])
                data.append([keyword, title, link, "MO"])
        except:
            data.append([keyword, "없음", "", "MO"])

    pc_driver.quit()
    mobile_driver.quit()
    return data

# ──────────────────────────────
# Streamlit UI
# ──────────────────────────────
st.title("네이버 파워링크 광고 크롤러 (PC + 모바일)")
st.write("JS 렌더링 포함 광고까지 모두 수집하여 엑셀 다운로드 가능")

keywords_input = st.text_area("검색 키워드를 입력하세요 (줄바꿈 구분)", "")
keywords = [k.strip() for k in keywords_input.split("\n") if k.strip()]

if st.button("크롤링 시작"):
    if not keywords:
        st.warning("키워드를 하나 이상 입력해 주세요.")
    else:
        with st.spinner("크롤링 중..."):
            results = crawl_naver_powerlink_full(keywords)

        df = pd.DataFrame(
            results,
            columns=["검색 키워드", "광고주/제목", "표시용 링크", "구분"]
        )
        st.success("크롤링 완료!")
        st.dataframe(df)

        buf = BytesIO()
        df.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button(
            "엑셀 파일 다운로드",
            data=buf,
            file_name="naver_powerlink_results_full.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
