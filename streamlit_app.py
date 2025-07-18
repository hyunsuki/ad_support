import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ───────────────────────────────────────────────────────────────
# 모바일용 Selenium 드라이버 (system chromedriver 사용)
# ───────────────────────────────────────────────────────────────
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

# ───────────────────────────────────────────────────────────────
# PC용 Selenium 드라이버 추가
# ───────────────────────────────────────────────────────────────
def get_pc_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

# ───────────────────────────────────────────────────────────────
# 메인 크롤러 (개선된 버전)
# ───────────────────────────────────────────────────────────────
def crawl_naver_powerlink(keywords):
    data = []
    
    pc_driver = get_pc_driver()
    mobile_driver = get_mobile_driver()

    for keyword in keywords:
        q = requests.utils.quote(keyword)

        ## ─── PC 크롤링 (Selenium으로 변경)
        try:
            url_pc = f"https://search.naver.com/search.naver?query={q}"
            pc_driver.get(url_pc)
            time.sleep(2)

            # PC 광고 요소들을 찾는 여러 셀렉터 시도
            pc_ad_selectors = [
                "div.group_ad a.link_ad",  # 새로운 구조
                "div.ad_area a.ad_link",  # 대안 구조
                "div[data-module='PowerLink'] a",  # 파워링크 모듈
                ".lst_type li",  # 기존 구조
                ".api_ans_base .total_wrap a"  # 통합 검색 광고
            ]
            
            ads_pc = []
            for selector in pc_ad_selectors:
                try:
                    ads_pc = pc_driver.find_elements(By.CSS_SELECTOR, selector)
                    if ads_pc:
                        break
                except:
                    continue
            
            if ads_pc:
                for ad in ads_pc:
                    try:
                        # 제목 추출
                        title_element = ad.find_element(By.CSS_SELECTOR, ".site, .ad_tit, .link_tit")
                        title = title_element.text.strip() if title_element else "없음"
                        
                        # 링크 추출
                        link_element = ad.find_element(By.CSS_SELECTOR, ".url, .ad_url, .link_url")
                        link = link_element.text.strip() if link_element else ""
                        
                        if title and title != "없음":
                            data.append([keyword, title, link, "PC"])
                    except:
                        continue
            
            if not data or not any(row[3] == "PC" and row[0] == keyword for row in data):
                data.append([keyword, "없음", "", "PC"])

        except Exception as e:
            print(f"PC 크롤링 오류: {e}")
            data.append([keyword, "없음", "", "PC"])

        ## ─── 모바일 크롤링 (개선된 버전)
        try:
            url_mo = f"https://m.ad.search.naver.com/search.naver?where=m_expd&query={q}"
            mobile_driver.get(url_mo)
            time.sleep(2)

            # 전체 스크롤 (lazy-loading)
            for _ in range(3):
                mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

            # "광고 더보기" 버튼 클릭 (존재 시)
            try:
                more_btn_selectors = [
                    "a:contains('광고 더보기')",
                    ".btn_more",
                    "[onclick*='more']",
                    "a[href*='more']"
                ]
                for btn_selector in more_btn_selectors:
                    try:
                        btn = mobile_driver.find_element(By.CSS_SELECTOR, btn_selector)
                        btn.click()
                        time.sleep(1)
                        break
                    except:
                        continue
            except:
                pass

            # 한 번 더 스크롤
            mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # 모바일 광고 요소들을 찾는 여러 셀렉터 시도 (개선된 부분)
            mobile_ad_selectors = [
                "#contentsList li",  # 가장 단순한 형태
                "ul#contentsList li",  # ul 포함
                "#contentsList .list_item",  # 클래스 포함
                "ul#contentsList.powerlink_list li.list_item",  # 기존 구조
                ".powerlink_list li",  # 대안 구조
                "[id*='contents'] li"  # 유사한 ID
            ]
            
            ads_mo = []
            for selector in mobile_ad_selectors:
                try:
                    ads_mo = mobile_driver.find_elements(By.CSS_SELECTOR, selector)
                    if ads_mo:
                        print(f"모바일 광고 {len(ads_mo)}개 발견 (셀렉터: {selector})")
                        break
                except:
                    continue
            
            if ads_mo:
                for ad in ads_mo:
                    try:
                        # 제목 추출 (여러 셀렉터 시도)
                        title_selectors = [".site", ".ad_tit", ".tit", "h3", "strong"]
                        title = "없음"
                        for title_sel in title_selectors:
                            try:
                                title_element = ad.find_element(By.CSS_SELECTOR, title_sel)
                                title = title_element.text.strip()
                                if title:
                                    break
                            except:
                                continue
                        
                        # 링크 추출 (여러 셀렉터 시도)
                        link_selectors = [".url_link", ".url", ".link_url", ".ad_url"]
                        link = ""
                        for link_sel in link_selectors:
                            try:
                                link_element = ad.find_element(By.CSS_SELECTOR, link_sel)
                                link = link_element.text.strip()
                                if link:
                                    break
                            except:
                                continue
                        
                        if title and title != "없음":
                            data.append([keyword, title, link, "MO"])
                    except:
                        continue
            
            if not any(row[3] == "MO" and row[0] == keyword for row in data):
                data.append([keyword, "없음", "", "MO"])

        except Exception as e:
            print(f"모바일 크롤링 오류: {e}")
            data.append([keyword, "없음", "", "MO"])

    pc_driver.quit()
    mobile_driver.quit()
    return data

# ───────────────────────────────────────────────────────────────
# Streamlit UI
# ───────────────────────────────────────────────────────────────
st.title("네이버 파워링크 광고 크롤러 (개선된 버전)")
st.write("PC/모바일 파워링크 광고를 크롤링 후 엑셀로 다운로드합니다.")

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
