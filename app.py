import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; width: 33%; }
    .stButton>button { width: 100%; height: 3.5em; background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl=0)
        data['日期'] = pd.to_datetime(data['日期'], errors='coerce')
        data = data.dropna(subset=['日期'])
        data['金額'] = pd.to_numeric(data['金額'], errors='coerce').fillna(0)
        return data
    except:
        return pd.DataFrame(columns=["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註"])

df = load_data()

# --- 2. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📝 新增", "📊 分析", "📜 歷史"])

# --- Tab 1: 新增紀錄 (解決連動問題) ---
with tab1:
    st.subheader("➕ 新增帳目")
    
    # 第一步：在表單外選擇類型（這是連動成功的關鍵）
    type_choice = st.radio("選擇類型", ["支出", "收入"], horizontal=True)
    
    # 第二步：根據類型決定分類清單 (依據您的最新條件)
    if type_choice == "收入":
        categories = ["薪資", "獎金", "投資", "其他"]
    else:
        categories = ["飲食", "交通", "購物", "稅金", "娛樂", "醫療費", "電信費", "其他"]
    
    # 第三步：進入表單填寫其餘內容
    with st.form("my_form", clear_on_submit=True):
        d = st.date_input("日期", datetime.date.today())
        
        # 這裡的分類會隨 type_choice 即時改變
        c = st.selectbox("分類項目", categories)
        
        a = st.number_input("金額 (TWD)", min_value=0, step=1)
        
        # 只有支出才顯示支付方式
        m = st.selectbox("支付方式", ["現金", "信用卡", "轉帳"]) if type_choice == "支出" else " "
        
        n = st.text_input("備註")
        
        submit_button = st.form_submit_button("確認儲存 💾")
        
        if submit_button:
            if a == 0:
                st.warning("請輸入金額！")
            else:
                new_data = pd.DataFrame([{
                    "日期": d, 
                    "分類項目": c, 
                    "收支類型": type_choice, 
                    "金額": a, 
                    "結餘": a if type_choice == "收入" else -a, 
                    "支出方式": m, 
                    "備註": n
                }])
                
                updated_df = pd.concat([df, new_data], ignore_index=True)
                # 存回雲端前格式化日期
                updated_df['日期'] = pd.to_datetime(updated_df['日期']).dt.strftime('%Y-%m-%d')
                
                conn.update(data=updated_df)
                st.success("✅ 資料儲存成功！")
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        curr_year = datetime.date.today().year
        year_exp = df[(df["收支類型"] == "支出") & (df['日期'].dt.year == curr_year)]
        if not year_exp.empty:
            st.write(f"📊 {curr_year} 年度支出結構")
            fig = px.pie(year_exp.groupby("分類項目")["金額"].sum().reset_index(), 
                         values='金額', names='分類項目', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無數據")

# --- Tab 3: 歷史紀錄 ---
with tab3:
    st.subheader("📜 歷史明細")
    if not df.empty:
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        all_months = sorted(df['Month'].unique(), reverse=True)
        sel_month = st.selectbox("🔍 選擇查詢月份", all_months)
        
        m_df = df[df['Month'] == sel_month].copy()
        
        if not m_df.empty:
            inc = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
            exp = m_df[m_df["收支類型"] == "支出"]["金額"].sum()
            
            col1, col2 = st.columns(2)
            col1.metric("當月收入", f"{inc:,.0f}")
            col2.metric("當月支出", f"{exp:,.0f}")
            
            def highlight_income(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            disp = m_df[["日期", "分類項目", "金額", "收支類型", "備註"]].copy()
            disp['日期'] = disp['日期'].dt.strftime('%m-%d')
            
            st.dataframe(disp.style.apply(highlight_income, axis=1).format({"金額": "{:,.0f}"}), 
                         use_container_width=True, hide_index=True)
    else:
        st.info("尚未連動資料或 Google Sheet 為空。")
