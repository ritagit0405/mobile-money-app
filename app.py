import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

# 優化手機顯示的 CSS
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px !important; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; width: 33%; }
    /* 讓按鈕更適合手機點擊 */
    .stButton>button { width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 讀取資料並清除快取以確保最新
        data = conn.read(ttl=0)
        data['日期'] = pd.to_datetime(data['日期'], errors='coerce')
        data = data.dropna(subset=['日期'])
        data['金額'] = pd.to_numeric(data['金額'], errors='coerce').fillna(0)
        return data
    except Exception as e:
        # 如果失敗回傳空表
        return pd.DataFrame(columns=["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註"])

df = load_data()

# --- 2. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📝 新增", "📊 分析", "📜 歷史"])

# --- Tab 1: 新增紀錄 (已修復連動邏輯) ---
with tab1:
    st.subheader("➕ 新增帳目")
    
    # 重點：將類型移出 Form 之外，實現即時連動
    t = st.selectbox("選擇收支類型", ["支出", "收入"], key="main_type")
    
    # 根據類型動態產生分類清單
    if t == "支出":
        c_list = ["飲食", "交通", "購物", "住房", "娛樂", "其他"]
    else:
        c_list = ["薪資", "獎金", "投資", "其他"]
    
    # 進入表單
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("日期", datetime.date.today())
        
        # 此處會根據上面的 t 自動變動
        c = st.selectbox("分類項目", c_list)
        
        a = st.number_input("金額 (TWD)", min_value=0, step=1)
        
        # 支出方式邏輯
        m = st.selectbox("支付方式", ["現金", "信用卡", "轉帳"]) if t == "支出" else " "
        
        n = st.text_input("備註 (選填)")
        
        submit = st.form_submit_button("確認儲存 💾")
        
        if submit:
            if a <= 0:
                st.error("請輸入大於 0 的金額")
            else:
                # 建立新資料
                new = pd.DataFrame([{
                    "日期": d, 
                    "分類項目": c, 
                    "收支類型": t, 
                    "金額": a, 
                    "結餘": a if t == "收入" else -a, 
                    "支出方式": m, 
                    "備註": n
                }])
                
                # 合併並轉為字串格式存回 Google Sheets
                updated = pd.concat([df, new], ignore_index=True)
                updated['日期'] = pd.to_datetime(updated['日期']).dt.strftime('%Y-%m-%d')
                
                conn.update(data=updated)
                st.success("✅ 儲存成功！請至「歷史」查看。")
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        curr_year = datetime.date.today().year
        year_exp = df[(df["收支類型"] == "支出") & (df['日期'].dt.year == curr_year)]
        
        if not year_exp.empty:
            st.write(f"📊 {curr_year} 年度支出比例")
            fig = px.pie(year_exp.groupby("分類項目")["金額"].sum().reset_index(), 
                         values='金額', names='分類項目', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"📅 {curr_year} 年尚未有支出數據")
    else:
        st.info("暫無分析數據")

# --- Tab 3: 歷史紀錄 ---
with tab3:
    st.subheader("📜 歷史明細")
    
    if not df.empty:
        # 產生月份清單
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        all_months = sorted(df['Month'].unique(), reverse=True)
        
        sel_month = st.selectbox("🔍 選擇查詢月份", all_months)
        
        # 篩選月份資料
        m_df = df[df['Month'] == sel_month].copy()
        
        if not m_df.empty:
            # 統計卡片
            inc = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
            exp = m_df[m_df["收支類型"] == "支出"]["金額"].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("當月收入", f"{inc:,.0f}")
            c2.metric("當月支出", f"{exp:,.0f}")
            
            # Tiffany 藍字體樣式
            def color_inc(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            # 顯示表格
            disp = m_df[["日期", "分類項目", "金額", "收支類型", "備註"]].copy()
            disp['日期'] = disp['日期'].dt.strftime('%m-%d')
            
            st.dataframe(
                disp.style.apply(color_inc, axis=1).format({"金額": "{:,.0f}"}), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning("該月份無資料")
    else:
        st.info("尚未連動資料或 Google Sheet 為空。")
