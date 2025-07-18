import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from io import BytesIO

# 1) 메인 모바일 검색 페이지에서 referenceId 추출
def extract_reference_id(keyword):
    q = requests.utils.quote(keyword)
    url = f"https://m.search.naver.com/search.naver?where=m&query={q}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
    }
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    el = soup.select_one("div[id^=mobilePowerLink_]")
    if not el:
        return ""
    # id 예: mobilePowerLink_c5b0-bidq → suffix: c5b0-bidq
    return el["id"].split("_", 1)[1]

# 2) PC + 모바일 크롤러
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

    for keyword in keywords:
        q = requests.utils.quote(keyword)

        # ───▶ PC 크롤링 (기존)
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

        # ───▶ 모바일 크롤링 (referenceId 적용)
        ref_id = extract_reference_id(keyword)
        url_mo = (
            f"https://m.ad.search.naver.com/search.naver"
            f"?where=m_expd&query={q}&referenceId={ref_id}"
        )
        res_mo = requests.get(url_mo, headers=headers_mo)
        soup_mo = BeautifulSoup(res_mo.text, "html.parser")

        ads_mo = soup_mo.select("div#ct.powerlink li")
        if ads_mo:
            for ad in ads_mo:
                title_el = ad.select_one(".site")
                url_el   = ad.select_one(".url_link")
                title = title_el.get_text(strip=True) if title_el else "없음"
                link  = url_el.get_text(strip=True) if url_el else ""
                data.append([keyword, title, link, "MO"])
        else:
            data.append([keyword, "없음", "", "MO"])

    return data

# 3) Streamlit UI
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
