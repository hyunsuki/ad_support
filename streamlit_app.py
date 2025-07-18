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

# 크롬 드라이버 직접 경로 지정 함수
def get_mobile_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=375,812")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def crawl_mobile_powerlink_all_ads(keywords):
    data = []
    driver = get_mobile_driver()

    for keyword in keywords:
        query = requests.utils.quote(keyword)
        url_mo = f"https://m.search.naver.com/search.naver?query={query}"
        driver.get(url_mo)
        time.sleep(2)

        ads_collected = set()
        max_clicks = 5  # 최대 5번 슬라이드 이동 (필요에 따라 조정)

        for _ in range(max_clicks):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            ads = soup.select("div.ad_section._ad_list div.ad_item._ad_item")

            for ad in ads:
                title_el = ad.select_one("a.link_tit strong.tit")
                title = title_el.get_text(strip=True) if title_el else "없음"

                advertiser_el = ad.select_one("span.site")
                advertiser = advertiser_el.get_text(strip=True) if advertiser_el else "없음"

                link_el = ad.select_one("span.url")
                link = link_el.get_text(strip=True) if link_el else ""

                unique_id = (title, advertiser, link)
                if unique_id not in ads_collected:
                    ads_collected.add(unique_id)
                    data.append([keyword, f"{title} ({advertiser})", link, "MO"])

            # 다음 광고 슬라이드 버튼 클릭 시도
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "button.btn_next")  # CSS 셀렉터는 실제 버튼에 맞게 조정 필요
                if next_button.is_enabled():
                    next_button.click()
                    time.sleep(1)  # 애니메이션 대기
                else:
                    break
            except NoSuchElementException:
                break

        if not ads_collected:
            data.append([keyword, "없음", "", "MO"])

    driver.quit()
    return data

# Streamlit UI
st.title("네이버 파워링크 광고 크롤러")
st.write("네이버 검색에서 PC/모바일 파워링크 광고를 크롤링하고 결과를 확인하세요.")

keywords_input = st.text_area("검색할 키워드를 입력하세요 (여러 키워드는 줄바꿈으로 구분)", "")
keywords = [k.strip() for k in keywords_input.split("\n") if k.strip()] if keywords_input else []

if st.button("크롤링 시작"):
    if keywords:
        with st.spinner("크롤링 중..."):
            results = crawl_mobile_powerlink_all_ads(keywords)

        if results:
            st.write("크롤링된 결과:")
            df = pd.DataFrame(results, columns=["검색 키워드", "광고 제목 (광고주)", "표시용 링크", "구분"])
            st.dataframe(df)

            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="엑셀 파일 다운로드",
                data=output,
                file_name="naver_powerlink_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("키워드를 입력해 주세요.")
