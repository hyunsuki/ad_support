import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_mobile_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=375,812")
    options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )
    # Streamlit Cloud에 기본 설치된 드라이버 사용
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

def crawl_naver_powerlink(keywords):
    data = []
    headers_pc = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
    }

    mobile_driver = get_mobile_driver()

    for keyword in keywords:
        q = requests.utils.quote(keyword)

        # ─── PC 크롤링 ───────────────────────────────
        url_pc = f"https://search.naver.com/search.naver?query={q}"
        res_pc = requests.get(url_pc, headers=headers_pc)
        soup_pc = BeautifulSoup(res_pc.text, "html.parser")
        ads_pc = soup_pc.select(".lst_type li")
        if ads_pc:
            for ad in ads_pc:
                title = ad.select_one("a.site").get_text(strip=True) if ad.select_one("a.site") else "없음"
                link  = ad.select_one("a.lnk_url").get_text(strip=True) if ad.select_one("a.lnk_url") else ""
                data.append([keyword, title, link, "PC"])
        else:
            data.append([keyword, "없음", "", "PC"])

        # ─── 모바일 크롤링 (Selenium) ────────────────────────────
        url_mo = f"https://m.ad.search.naver.com/search.naver?where=m_expd&query={q}&referenceId"
        mobile_driver.get(url_mo)
        try:
            WebDriverWait(mobile_driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul#contentsList.powerlink_list li.list_item"))
            )
            ads_mo = mobile_driver.find_elements(By.CSS_SELECTOR, "ul#contentsList.powerlink_list li.list_item")
            if not ads_mo:
                raise Exception("광고 없음")
            for ad in ads_mo:
                title = ad.find_element(By.CSS_SELECTOR, ".site").text
                try:
                    link = ad.find_element(By.CSS_SELECTOR, ".url_link").text
                except:
                    link = ad.find_element(By.CSS_SELECTOR, ".url").text
                data.append([keyword, title, link, "MO"])
        except Exception:
            data.append([keyword, "없음", "", "MO"])

    mobile_driver.quit()
    return data

# ───────────────────────────────────────────────────────────────
# Streamlit UI
# ───────────────────────────────────────────────────────────────
st.title("네이버 파워링크 광고 크롤러")
st.write("PC/모바일 파워링크 광고를 크롤링해 엑셀로 다운로드합니다.")

keywords_input = st.text_area("검색 키워드를 입력하세요 (줄바꿈 구분)", "")
keywords = [k.strip() for k in keywords_input.split("\n") if k.strip()]

if st.button("크롤링 시작"):
    if not keywords:
        st.warning("키워드를 하나 이상 입력해 주세요.")
    else:
        with st.spinner("크롤링 중..."):
            results = crawl_naver_powerlink(keywords)
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
            file_name="naver_powerlink_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
