import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def crawl_naver_powerlink_pc(keywords):
    data = []

    headers_pc = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    for keyword in keywords:
        query = requests.utils.quote(keyword)
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

    return data

def crawl_naver_powerlink_mobile_selenium(keywords):
    data = []

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    for keyword in keywords:
        url = f"https://m.search.naver.com/search.naver?where=m&query={requests.utils.quote(keyword)}"
        driver.get(url)
        time.sleep(3)  # 렌더링 대기

        try:
            ads = driver.find_elements(By.CSS_SELECTOR, "div.ad_section._ad_list div.ad_item._ad_item")

            if not ads:
                data.append([keyword, "없음", "", "MO"])
            else:
                for ad in ads:
                    title_el = ad.find_element(By.CSS_SELECTOR, "a.link_tit strong.tit")
                    title = title_el.text.strip()
                    link_el = ad.find_element(By.CSS_SELECTOR, "a.link_tit")
                    link = link_el.get_attribute("href")
                    data.append([keyword, title, link, "MO"])

        except Exception as e:
            data.append([keyword, f"오류 발생: {str(e)}", "", "MO"])

    driver.quit()
    return data

# Streamlit UI
st.title("네이버 파워링크 광고 크롤러 (PC + 모바일 통합)")

keywords_input = st.text_area("검색할 키워드를 입력하세요 (줄바꿈 구분)", "")
keywords = [k.strip() for k in keywords_input.split("\n") if k.strip()] if keywords_input else []

if st.button("크롤링 시작"):
    if keywords:
        with st.spinner("PC 크롤링 중..."):
            pc_results = crawl_naver_powerlink_pc(keywords)
        with st.spinner("모바일 크롤링 중... (시간 좀 걸립니다)"):
            mo_results = crawl_naver_powerlink_mobile_selenium(keywords)

        all_results = pc_results + mo_results

        if all_results:
            df = pd.DataFrame(all_results, columns=["검색 키워드", "광고 제목", "표시용 링크", "구분"])
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
