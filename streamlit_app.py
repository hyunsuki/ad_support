import streamlit as st
import pandas as pd
from io import BytesIO
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─────────────────────────────────────────────
# Selenium 드라이버 설정
# ─────────────────────────────────────────────
def get_pc_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    service = Service("/usr/bin/chromedriver")  # 환경에 맞춰 수정
    return webdriver.Chrome(service=service, options=options)


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
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# ─────────────────────────────────────────────
# 크롤링 함수
# ─────────────────────────────────────────────
def crawl_naver_powerlink(keywords):
    data = []

    pc_driver = get_pc_driver()
    mobile_driver = get_mobile_driver()

    for keyword in keywords:
        # URL 인코딩
        q = keyword.replace(' ', '+')

        # ─── PC 광고 수집
        pc_url = f"https://search.naver.com/search.naver?query={q}"
        pc_driver.get(pc_url)

        # 광고 로딩 대기
        try:
            WebDriverWait(pc_driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.site"))
            )
            titles_pc = pc_driver.find_elements(By.CSS_SELECTOR, "a.site")
            links_pc  = pc_driver.find_elements(By.CSS_SELECTOR, "a.lnk_url")
            if titles_pc and links_pc:
                for t, l in zip(titles_pc, links_pc):
                    data.append([keyword, t.text.strip(), l.text.strip(), "PC"])
            else:
                data.append([keyword, "없음", "", "PC"])
        except:
            data.append([keyword, "없음", "", "PC"])

        # ─── 모바일 광고 수집
        mo_url = f"https://m.ad.search.naver.com/search.naver?where=m_expd&query={q}&referenceId"
        mobile_driver.get(mo_url)

        # 스크롤
        for _ in range(3):
            mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        # 광고 더보기 클릭
        try:
            btn = mobile_driver.find_element(By.LINK_TEXT, "광고 더보기")
            btn.click()
            time.sleep(1)
        except:
            pass

        # 추가 스크롤 후 수집
        mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        try:
            WebDriverWait(mobile_driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul#contentsList.powerlink_list li.list_item"))
            )
            ads_mo = mobile_driver.find_elements(By.CSS_SELECTOR, "ul#contentsList.powerlink_list li.list_item")
            if ads_mo:
                for ad in ads_mo:
                    title = ad.find_element(By.CSS_SELECTOR, ".site").text
                    try:
                        link = ad.find_element(By.CSS_SELECTOR, ".url_link").text
                    except:
                        link = ad.find_element(By.CSS_SELECTOR, ".url").text
                    data.append([keyword, title.strip(), link.strip(), "MO"])
            else:
                data.append([keyword, "없음", "", "MO"])
        except:
            data.append([keyword, "없음", "", "MO"])

    pc_driver.quit()
    mobile_driver.quit()
    return data

# ─────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────
st.title("🟢 네이버 파워링크 광고 크롤러")
st.write("PC/모바일 파워링크 광고를 크롤링하고 엑셀로 다운로드합니다.")

keywords_input = st.text_area("🔍 검색 키워드 입력 (줄바꿈 구분)", "")
keywords = [k.strip() for k in keywords_input.split("\n") if k.strip()]

if st.button("크롤링 시작"):
    if not keywords:
        st.warning("❗ 키워드를 하나 이상 입력해 주세요.")
    else:
        with st.spinner("⏳ 크롤링 중..."):
            results = crawl_naver_powerlink(keywords)

        df = pd.DataFrame(results, columns=["검색 키워드", "광고주/제목", "표시용 링크", "구분"])
        st.success("✅ 크롤링 완료!")
        st.dataframe(df)

        buf = BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button(
            "📥 엑셀 파일 다운로드",
            data=buf,
            file_name="naver_powerlink_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

