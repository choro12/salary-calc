import streamlit as st
import pandas as pd

# ==========================================
# 1. [핵심] 기존 계산 로직을 여기에 넣으세요
# ==========================================
def calculate_salary_logic(salary, non_taxable, dependents):
    """
    이 함수 안에 기존에 만드셨던 급여 계산 공식을 넣으시면 됩니다.
    지금은 예시 로직이 들어있습니다.
    """
    taxable_income = salary - non_taxable  # 과세 대상 금액

    # --- (예시) 4대보험 및 세금 계산 ---
    # 실제 사용하시는 정확한 요율이나 로직으로 덮어쓰세요
    national_pension = int(taxable_income * 0.045)        # 국민연금
    health_insurance = int(taxable_income * 0.03545)      # 건강보험
    care_insurance = int(health_insurance * 0.1295)       # 장기요양
    employment_insurance = int(taxable_income * 0.009)    # 고용보험
    
    # 간이 세금 계산 (부양가족 수에 따라 조금 깎아주는 시늉만 냄)
    tax_rate = 0.03 # 3% 가정
    if dependents >= 3:
        tax_rate = 0.02 # 부양가족 많으면 세율 인하 (예시)
        
    income_tax = int(taxable_income * tax_rate)           # 소득세
    local_tax = int(income_tax * 0.1)                     # 지방소득세

    # 공제액 합계
    total_deduction = (national_pension + health_insurance + 
                       care_insurance + employment_insurance + 
                       income_tax + local_tax)
    
    # 실수령액
    net_pay = salary - total_deduction

    # 결과를 딕셔너리(데이터 뭉치)로 반환
    return {
        "net_pay": net_pay,
        "total_deduction": total_deduction,
        "details": {
            "국민연금": national_pension,
            "건강보험": health_insurance,
            "장기요양": care_insurance,
            "고용보험": employment_insurance,
            "소득세": income_tax,
            "지방소득세": local_tax
        }
    }

# ==========================================
# 2. 화면 구성 (UI) - 건드리지 않아도 됩니다
# ==========================================

# 페이지 설정
st.set_page_config(page_title="급여 계산기", page_icon="💸", layout="centered")

st.title("💸 내 월급 실수령액은?")
st.caption("PythonAnywhere보다 빠르고 예쁜 Streamlit 버전입니다.")

st.divider()

# --- 입력 받는 곳 (Input) ---
col1, col2 = st.columns(2)

with col1:
    input_salary = st.number_input("세전 월 급여 (원)", value=3000000, step=100000, format="%d")
    input_dependents = st.number_input("부양가족 수 (본인포함)", value=1, step=1, min_value=1)

with col2:
    input_non_taxable = st.number_input("비과세액 (식대 등)", value=200000, step=10000, format="%d")

# 계산 버튼
if st.button("계산하기 🚀", type="primary", use_container_width=True):
    
    # 위의 계산 함수 호출
    result = calculate_salary_logic(input_salary, input_non_taxable, input_dependents)
    
    # --- 결과 보여주는 곳 (Output) ---
    st.write("") # 여백
    
    # 1. 메인 결과 (실수령액)
    st.success(f"### 예상 실수령액: {result['net_pay']:,} 원")
    
    # 2. 요약 지표
    m1, m2, m3 = st.columns(3)
    m1.metric("세전 급여", f"{input_salary:,}원")
    m2.metric("총 공제액", f"{result['total_deduction']:,}원")
    m3.metric("공제율", f"{(result['total_deduction']/input_salary*100):.1f}%")
    
    # 3. 상세 공제 내역 표 만들기
    st.write("#### 📋 공제 내역 상세")
    
    # 딕셔너리를 보기 좋은 표 데이터로 변환
    detail_data = {
        "항목": list(result['details'].keys()),
        "금액 (원)": [f"{v:,}" for v in result['details'].values()]
    }
    df = pd.DataFrame(detail_data)
    
    # 표 출력 (use_container_width=True로 꽉 차게)
    st.dataframe(df, hide_index=True, use_container_width=True)