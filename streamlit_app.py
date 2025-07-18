import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO
import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info(f"크롤링 시작: {keyword}")

        ## ─── PC 크롤링 개선 (더 다양한 셀렉터 시도)
        url_pc = f"https://search.naver.com/search.naver?query={q}"
        res_pc = requests.get(url_pc, headers=headers_pc)
        soup_pc = BeautifulSoup(res_pc.text, "html.parser")
        
        # 여러 셀렉터 패턴 시도
        pc_selectors = [
            ".lst_type li",
            ".powerlink_list li",
            ".ad_list li",
            "div[data-module='powerlink'] li",
            ".powerlink .lst_type li"
        ]
        
        ads_pc = []
        for selector in pc_selectors:
            ads_pc = soup_pc.select(selector)
            if ads_pc:
                logger.info(f"PC - 셀렉터 '{selector}'로 {len(ads_pc)}개 광고 발견")
                break
        
        if ads_pc:
            for i, ad in enumerate(ads_pc):
                # 여러 가능한 제목 셀렉터 시도
                title_selectors = ["a.site", ".site", "a[class*='site']", ".tit", ".title"]
                title = "없음"
                for t_sel in title_selectors:
                    title_elem = ad.select_one(t_sel)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                # 여러 가능한 링크 셀렉터 시도
                link_selectors = ["a.lnk_url", ".lnk_url", "a[class*='url']", ".url", ".link"]
                link = ""
                for l_sel in link_selectors:
                    link_elem = ad.select_one(l_sel)
                    if link_elem:
                        link = link_elem.get_text(strip=True)
                        break
                
                logger.info(f"PC 광고 {i+1}: {title} - {link}")
                data.append([keyword, title, link, "PC"])
        else:
            logger.warning(f"PC에서 광고를 찾을 수 없음: {keyword}")
            data.append([keyword, "없음", "", "PC"])

        ## ─── 모바일 크롤링 개선
        url_mo = f"https://m.ad.search.naver.com/search.naver?where=m_expd&query={q}&referenceId"
        mobile_driver.get(url_mo)
        
        # 더 충분한 대기 시간
        time.sleep(3)

        # 스크롤 개선
        last_h = 0
        for scroll_count in range(5):  # 스크롤 횟수 증가
            mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_h = mobile_driver.execute_script("return document.body.scrollHeight")
            if new_h == last_h:
                break
            last_h = new_h

        # "광고 더보기" 버튼 클릭
        try:
            more_buttons = mobile_driver.find_elements(By.XPATH, "//a[contains(text(), '광고 더보기') or contains(text(), '더보기')]")
            for btn in more_buttons:
                try:
                    btn.click()
                    time.sleep(2)
                except:
                    pass
        except:
            pass

        # 최종 스크롤
        mobile_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # 광고 수집 - 여러 셀렉터 시도
        mobile_selectors = [
            "ul#contentsList.powerlink_list li.list_item",
            "ul#contentsList li.list_item",
            ".powerlink_list li.list_item",
            ".powerlink_list li",
            "li.list_item"
        ]
        
        ads_mo = []
        for selector in mobile_selectors:
            try:
                WebDriverWait(mobile_driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                ads_mo = mobile_driver.find_elements(By.CSS_SELECTOR, selector)
                if ads_mo:
                    logger.info(f"모바일 - 셀렉터 '{selector}'로 {len(ads_mo)}개 광고 발견")
                    break
            except:
                continue
        
        if ads_mo:
            for i, ad in enumerate(ads_mo):
                try:
                    # 제목 추출 - 여러 셀렉터 시도
                    title_selectors = [".site", ".title", ".tit", "a.site", "[class*='site']"]
                    title = "없음"
                    for t_sel in title_selectors:
                        try:
                            title_elem = ad.find_element(By.CSS_SELECTOR, t_sel)
                            title = title_elem.text.strip()
                            if title:
                                break
                        except:
                            continue
                    
                    # 링크 추출 - 여러 셀렉터 시도
                    link_selectors = [".url_link", ".url", ".link", "[class*='url']"]
                    link = ""
                    for l_sel in link_selectors:
                        try:
                            link_elem = ad.find_element(By.CSS_SELECTOR, l_sel)
                            link = link_elem.text.strip()
                            if link:
                                break
                        except:
                            continue
                    
                    logger.info(f"모바일 광고 {i+1}: {title} - {link}")
                    data.append([keyword, title, link, "MO"])
                except Exception as e:
                    logger.error(f"모바일 광고 {i+1} 파싱 오류: {e}")
                    continue
        else:
            logger.warning(f"모바일에서 광고를 찾을 수 없음: {keyword}")
            data.append([keyword, "없음", "", "MO"])

    mobile_driver.quit()
    return data

# Streamlit UI
st.title("네이버 파워링크 광고 크롤러 (개선버전)")
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

        # 광고 개수 표시
        pc_count = len(df[df['구분'] == 'PC'])
        mo_count = len(df[df['구분'] == 'MO'])
        st.info(f"PC 광고: {pc_count}개, 모바일 광고: {mo_count}개")

        buf = BytesIO()
        df.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button(
            "엑셀 파일 다운로드",
            data=buf,
            file_name="naver_powerlink_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
