import streamlit as st
import pandas as pd
import io  # StringIO를 위한 모듈

# streamlit run viewer/streamlit_handler.py

st.set_page_config(layout="wide")

st.title("Shopping LIVE DashBoard📊")

# 업로드된 엑셀 파일을 처리하는 함수
def process_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success("파일이 성공적으로 업로드되었습니다.")
            return df
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# 파일 업로드 위젯
uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요", type=["xlsx", "xls"])

# 데이터프레임 저장용 세션 상태 초기화
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame()

# 업로드된 파일을 처리
if uploaded_file:
    st.session_state.data = process_uploaded_file(uploaded_file)

# 데이터프레임 출력 및 목록 추가/삭제 기능
if not st.session_state.data.empty:
    st.write("해외여행 라이브 정보:")

    # 데이터프레임 출력
    st.dataframe(st.session_state.data)

    # 목록(행) 추가
    st.write("목록 추가")
    new_row = {col: st.text_input(f"새로운 값 입력 ({col})", "") for col in st.session_state.data.columns}
    if st.button("추가"):
        try:
            st.session_state.data = st.session_state.data.append(new_row, ignore_index=True)
            st.success("새로운 목록(행)이 추가되었습니다.")
        except Exception as e:
            st.error(f"목록 추가 중 오류가 발생했습니다: {e}")

    # 목록(행) 삭제
    st.write("목록 삭제")
    delete_index = st.number_input("삭제할 행의 인덱스 선택", min_value=0, max_value=len(st.session_state.data)-1, step=1)
    if st.button("삭제"):
        try:
            st.session_state.data = st.session_state.data.drop(delete_index).reset_index(drop=True)
            st.success("선택한 목록(행)이 삭제되었습니다.")
        except Exception as e:
            st.error(f"목록 삭제 중 오류가 발생했습니다: {e}")

    # 수정된 데이터 출력
    st.write("수정된 데이터:")
    st.dataframe(st.session_state.data)
else:
    st.info("엑셀 파일을 업로드하면 데이터를 확인하고 관리할 수 있습니다.")
