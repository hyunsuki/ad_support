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
from selenium.common.exceptions import NoSuchElementException

# ───────────────────────────────────────────────────────────────
# 1) 모바일용 크롬 드라이버 생성 함수 (Selenium)
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
# 2) PC + 모바일 광고 크롤링 통합 함수
# ───────────────────────────────────────────────────────────────
def crawl_naver_powerlink(keywords):
    data = []
    headers_pc = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
    }
    headers_mo = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
    }

    driver = get_mobile_driver()

    for keyword in keywords:
        query = requests.utils.quote(keyword)

        # ───▶ PC 버전 크롤링 (기존 방식)
        url_pc = f"https://search.naver.com/search.naver?query={query}"
        res_pc = requests.get(url_pc, headers=headers_pc)
        soup_pc = BeautifulSoup(res_pc.text, "html.parser")

        powerlinks_pc = soup_pc.select(".lst_type li")
        if powerlinks_pc:
            for ad in powerlinks_pc:
                title_el = ad.select_one("a.site")
                title = title_el.get_text(strip=True) if title_el else "없음"
                link_el = ad.select_one("a.lnk_url")
                link = link_el.get_text(strip=True) if link_el else ""
                data.append([keyword, title, link, "PC"])
        else:
            data.append([keyword, "없음", "", "PC"])

        # ───▶ 모바일 버전 크롤링
        url_mo = f"https://m.search.naver.com/search.naver?query={query}"
        driver.get(url_mo)
        time.sleep(2)

        ads_collected = set()
        collected = False

        # (1) “광고 더보기” 링크 탐색 → 정적 HTML 요청
        try:
            more_btn = driver.find_element(By.LINK_TEXT, "광고 더보기")
            more_url = more_btn.get_attribute("href")
            if more_url:
                res_more = requests.get(more_url, headers=headers_mo)
                soup_more = BeautifulSoup(res_more.text, "html.parser")
                ads_more = soup_more.select("div.ad_item._ad_item")

                for ad in ads_more:
                    title_el = ad.select_one("a.link_tit strong.tit")
                    title = title_el.get_text(strip=True) if title_el else "없음"
                    adv_el = ad.select_one("span.site")
                    advertiser = adv_el.get_text(strip=True) if adv_el else "없음"
                    link_el = ad.select_one("span.url")
                    link = link_el.get_text(strip=True) if link_el else ""
                    key = (title, advertiser, link)
                    if key not in ads_collected:
                        ads_collected.add(key)
                        data.append([keyword, f"{title} ({advertiser})", link, "MO"])
                        collected = True
        except NoSuchElementException:
            # “광고 더보기” 버튼이 없으면 그냥 폴백
            pass

        # (2) 정적 페이지에서 한 건도 못 수집했다면 iframe 폴백
        if not collected:
            # 메인 DOM
            soup_main = BeautifulSoup(driver.page_source, "html.parser")
            ads_main = soup_main.select("div.ad_section._ad_list div.ad_item._ad_item")
            for ad in ads_main:
                title_el = ad.select_one("a.link_tit strong.tit")
                title = title_el.get_text(strip=True) if title_el else "없음"
                adv_el = ad.select_one("span.site")
                advertiser = adv_el.get_text(strip=True) if adv_el else "없음"
                link_el = ad.select_one("span.url")
                link = link_el.get_text(strip=True) if link_el else ""
                key = (title, advertiser, link)
                if key not in ads_collected:
                    ads_collected.add(key)
                    data.append([keyword, f"{title} ({advertiser})", link, "MO"])

            # iframe 내부까지
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in iframes:
                src = frame.get_attribute("src") or ""
                if "ad" not in src.lower():
                    continue
                driver.switch_to.frame(frame)
                time.sleep(1)
                soup_if = BeautifulSoup(driver.page_source, "html.parser")
                ads_if = soup_if.select("div.ad_item._ad_item")
                for ad in ads_if:
                    title_el = ad.select_one("a.link_tit strong.tit")
                    title = title_el.get_text(strip=True) if title_el else "없음"
                    adv_el = ad.select_one("span.site")
                    advertiser = adv_el.get_text(strip=True) if adv_el else "없음"
                    link_el = ad.select_one("span.url")
                    link = link_el.get_text(strip=True) if link_el else ""
                    key = (title, advertiser, link)
                    if key not in ads_collected:
                        ads_collected.add(key)
                        data.append([keyword, f"{title} ({advertiser})", link, "MO"])
                driver.switch_to.default_content()

        # (3) 단건도 없으면 "없음"
        if not ads_collected:
            data.append([keyword, "없음", "", "MO"])

    driver.quit()
    return data

# ───────────────────────────────────────────────────────────────
# 3) Streamlit 앱 UI
# ───────────────────────────────────────────────────────────────
st.title("네이버 파워링크 광고 크롤러")
st.write("네이버 검색에서 PC/모바일 파워링크 광고를 크롤링하고 결과를 확인하세요.")

keywords_input = st.text_area(
    "검색할 키워드를 입력하세요 (여러 키워드는 줄바꿈으로 구분)", ""
)
keywords = [k.strip() for k in keywords_input.split("\n") if k.strip()]

if st.button("크롤링 시작"):
    if not keywords:
        st.warning("키워드를 입력해 주세요.")
    else:
        with st.spinner("크롤링 중..."):
            results = crawl_naver_powerlink(keywords)

        df = pd.DataFrame(
            results,
            columns=["검색 키워드", "광고 제목 (광고주)", "표시용 링크", "구분"]
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
            mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet"
        )
