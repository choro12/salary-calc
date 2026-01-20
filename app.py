import streamlit as st
import pandas as pd
import datetime
import calendar
import holidays
import sqlite3
import os

# ==========================================
# 1. 선생님의 기존 로직 (계산 공식 유지)
# ==========================================

def format_time_input(time_str):
    if isinstance(time_str, str):
        time_str = time_str.strip()
        if ':' not in time_str and len(time_str) == 4 and time_str.isdigit():
            return time_str[:2] + ':' + time_str[2:]
    return time_str

def get_break_hours(start_dt, end_dt, is_next_day):
    actual_end_dt = end_dt
    if is_next_day:
        actual_end_dt = end_dt + datetime.timedelta(days=1)
    
    total_elapsed_minutes = (actual_end_dt - start_dt).total_seconds() / 60
    break_minutes = 0

    if total_elapsed_minutes >= 540:
        break_minutes = 60
        remaining_minutes = total_elapsed_minutes - 540
        if remaining_minutes > 0:
            additional_breaks = int(remaining_minutes // 270)
            break_minutes += (additional_breaks * 30)
    elif total_elapsed_minutes >= 270:
        break_minutes = 30

    if is_next_day:
        day2_lunch_start = datetime.datetime.combine(start_dt.date() + datetime.timedelta(days=1), datetime.time(12, 0))
        day2_lunch_end = datetime.datetime.combine(start_dt.date() + datetime.timedelta(days=1), datetime.time(13, 0))
        overlap_start = max(start_dt, day2_lunch_start)
        overlap_end = min(actual_end_dt, day2_lunch_end)
        if overlap_end > overlap_start:
             pass 

    return break_minutes / 60

def calculate_hours_from_time_range(start_time, end_time, day_type, is_next_day):
    try:
        start_dt = datetime.datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.datetime.strptime(end_time, "%H:%M")
    except ValueError:
        return None

    break_hours = get_break_hours(start_dt, end_dt, is_next_day)

    if is_next_day:
        end_dt += datetime.timedelta(days=1)

    total_seconds = (end_dt - start_dt).total_seconds() - (break_hours * 3600)
    if total_seconds < 0: total_seconds = 0

    calculated_hours = {'normal': 0, 'night': 0, 'holiday': 0}
    night_seconds = 0
    current_dt = start_dt
    while current_dt < end_dt:
        if (current_dt.hour >= 22 and current_dt.hour <= 23) or (current_dt.hour >= 0 and current_dt.hour < 6):
            night_seconds += 60
        current_dt += datetime.timedelta(minutes=1)

    total_effective_seconds = (end_dt - start_dt).total_seconds() - (break_hours * 3600)
    actual_night_seconds = min(night_seconds, total_effective_seconds)
    day_seconds = max(0, total_effective_seconds - actual_night_seconds)

    if day_type == '휴일/특근':
        calculated_hours['holiday'] = total_effective_seconds / 3600
    else:
        calculated_hours['normal'] = day_seconds / 3600

    calculated_hours['night'] = actual_night_seconds / 3600
    return calculated_hours

# ==========================================
# 2. 데이터베이스 관리 (SQLite)
# ==========================================
DB_FILE = 'work_records.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS work_records (
            date TEXT PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            day_type TEXT,
            is_next_day BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()

def save_record(date, start, end, dtype, is_next):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 시간 포맷팅 적용
    f_start = format_time_input(start)
    f_end = format_time_input(end)
    c.execute('''
        INSERT OR REPLACE INTO work_records (date, start_time, end_time, day_type, is_next_day)
        VALUES (?, ?, ?, ?, ?)
    ''', (date, f_start, f_end, dtype, is_next))
    conn.commit()
    conn.close()

def delete_record(date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM work_records WHERE date = ?", (date,))
    conn.commit()
    conn.close()

def load_records():
    if not os.path.exists(DB_FILE):
        init_db()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM work_records ORDER BY date", conn)
    conn.close()
    return df

# ==========================================
# 3. Streamlit 화면 구성 (UI)
# ==========================================

st.set_page_config(page_title="급여 계산기", page_icon="💰", layout="wide")
init_db() # 앱 시작 시 DB 확인

# --- 사이드바: 설정 ---
with st.sidebar:
    st.title("⚙️ 설정")
    
    # 1. 날짜 선택
    today = datetime.date.today()
    sel_year = st.number_input("연도 (Year)", value=today.year)
    sel_month = st.number_input("월 (Month)", 1, 12, today.month)
    
    st.divider()
    
    # 2. 급여 기준 (수정 가능하도록)
    st.subheader("급여 기준값")
    base_salary = st.number_input("기본급", value=2285720, step=10000)
    hourly_wage = st.number_input("시급", value=12759, step=100)
    fixed_deduction = st.number_input("고정 공제액", value=385360, step=1000)
    
    st.info("데이터 백업: Streamlit Cloud는 재시작 시 DB가 초기화될 수 있습니다. 주기적으로 CSV로 다운받으세요.")
    
    # CSV 다운로드 기능
    df_all = load_records()
    if not df_all.empty:
        csv = df_all.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 근무기록 백업(CSV)", csv, "work_records.csv", "text/csv")

# --- 메인 화면 ---
st.title(f"💰 {sel_year}년 {sel_month}월 급여 계산기")

tab1, tab2 = st.tabs(["📝 근무 기록 입력", "📊 급여 계산 결과"])

# [탭 1] 근무 기록 입력
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("새 기록 추가/수정")
        with st.form("input_form"):
            input_date = st.date_input("날짜", value=datetime.date(sel_year, sel_month, 1))
            input_start = st.text_input("출근 시간 (예: 0900 또는 09:00)", value="09:00")
            input_end = st.text_input("퇴근 시간 (예: 1800 또는 18:00)", value="18:00")
            input_type = st.selectbox("근무 유형", ["평일", "휴일/특근"])
            input_next_day = st.checkbox("익일 퇴근 (철야)")
            
            submitted = st.form_submit_button("저장하기")
            if submitted:
                save_record(str(input_date), input_start, input_end, input_type, input_next_day)
                st.success(f"{input_date} 기록 저장 완료!")
                st.rerun() # 화면 새로고침

        st.subheader("기록 삭제")
        del_date = st.date_input("삭제할 날짜 선택")
        if st.button("해당 날짜 기록 삭제"):
            delete_record(str(del_date))
            st.warning(f"{del_date} 삭제 완료")
            st.rerun()

    with col2:
        st.subheader("📋 저장된 근무 기록")
        df = load_records()
        
        # 현재 선택된 달의 데이터만 필터링해서 보여주기
        if not df.empty:
            # 날짜 필터링을 위해 문자열 -> 날짜 변환
            df['date_obj'] = pd.to_datetime(df['date'])
            mask = (df['date_obj'].dt.year == sel_year) & (df['date_obj'].dt.month == sel_month)
            df_month = df.loc[mask].sort_values('date')
            
            st.dataframe(df_month[['date', 'start_time', 'end_time', 'day_type', 'is_next_day']], 
                         use_container_width=True, hide_index=True)
        else:
            st.info("저장된 기록이 없습니다.")

# [탭 2] 급여 계산 결과
with tab2:
    if st.button("🚀 급여 계산하기", type="primary", use_container_width=True):
        # 1. 근무일수 및 의무 근로시간 계산
        month_range = calendar.monthrange(sel_year, sel_month)[1]
        kr_holidays = holidays.KR(observed=True, years=sel_year)
        
        work_days = 0
        for day in range(1, month_range + 1):
            curr = datetime.date(sel_year, sel_month, day)
            if curr.weekday() < 5 and curr not in kr_holidays:
                work_days += 1
        
        obligation_hours = work_days * 8
        
        # 2. DB에서 데이터 가져와서 계산
        df = load_records()
        total_hours = {'normal': 0, 'night': 0, 'holiday': 0}
        
        if not df.empty:
            for _, row in df.iterrows():
                r_date = datetime.datetime.strptime(row['date'], '%Y-%m-%d').date()
                if r_date.year == sel_year and r_date.month == sel_month:
                    calc = calculate_hours_from_time_range(
                        row['start_time'], row['end_time'], 
                        row['day_type'], bool(row['is_next_day'])
                    )
                    if calc:
                        for k in total_hours:
                            total_hours[k] += calc.get(k, 0)

        # 3. 급여 계산 (선생님 로직 적용)
        total_effective = sum(total_hours.values())
        overtime_hours = max(0, total_effective - obligation_hours)
        
        overtime_pay = overtime_hours * hourly_wage * 1.5
        night_pay = total_hours['night'] * hourly_wage * 0.5
        holiday_pay = total_hours['holiday'] * hourly_wage * 1.5
        
        gross_pay = base_salary + overtime_pay + night_pay + holiday_pay
        net_pay = gross_pay - fixed_deduction

        # 4. 결과 출력
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("기본급", f"{base_salary:,}원")
        c2.metric("예상 실수령액", f"{int(net_pay):,}원", delta="세후")
        c3.metric("총 지급액(세전)", f"{int(gross_pay):,}원")
        
        st.success(f"### 💰 최종 실수령액: {int(net_pay):,} 원")
        
        st.write("#### 📊 상세 수당 내역")
        
        res_data = {
            "항목": ["연장(OT) 수당", "야간 수당", "휴일/특근 수당", "고정 공제"],
            "시간(h)": [
                f"{overtime_hours:.1f} 시간", 
                f"{total_hours['night']:.1f} 시간", 
                f"{total_hours['holiday']:.1f} 시간", 
                "-"
            ],
            "금액": [
                f"+ {int(overtime_pay):,} 원",
                f"+ {int(night_pay):,} 원",
                f"+ {int(holiday_pay):,} 원",
                f"- {int(fixed_deduction):,} 원"
            ]
        }
        st.table(pd.DataFrame(res_data))
        
        st.caption(f"※ 이번 달 의무 근로시간: {obligation_hours}시간 / 총 인정 근무시간: {total_effective:.1f}시간")