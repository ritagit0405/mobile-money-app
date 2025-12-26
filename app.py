import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 22px !important; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; width: 33%; }
    .stButton>button { width: 100%; height: 3.5em; }
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

# --- Tab 1: 新增紀錄 ---
with tab1:
    st.subheader("➕ 新增帳目")
    type_choice = st.radio("選擇類型", ["支出", "收入"], horizontal=True)
    
    if type_choice == "收入":
        categories = ["薪資", "獎金", "投資", "其他"]
    else:
        categories = ["飲食", "交通", "購物", "稅金", "娛樂", "醫療費", "電信費", "其他"]
    
    with st.form("my_form", clear_on_submit=True):
        d = st.date_input("日期", datetime.date.today())
        c = st.selectbox("分類項目", categories)
        a = st.number_input("金額 (TWD)", min_value=0, step=1)
        m = st.selectbox("支付方式", ["現金", "信用卡", "轉帳"]) if type_choice == "支出" else " "
        n = st.text_input("備註")
        
        if st.form_submit_button("確認儲存 💾"):
            if a == 0:
                st.warning("請輸入金額！")
            else:
                new_row = pd.DataFrame([{
                    "日期": d, "分類項目": c, "收支類型": type_choice, 
                    "金額": a, "結餘": a if type_choice == "收入" else -a, 
                    "支出方式": m, "備註": n
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
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

# --- Tab 3: 歷史紀錄 (新增功能：年度統計與刪除) ---
with tab3:
    st.subheader("📜 歷史明細")
    if not df.empty:
        # 準備月份與年度資料
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        df['Year'] = df['日期'].dt.year
        all_months = sorted(df['Month'].unique(), reverse=True)
        sel_month = st.selectbox("🔍 選擇查詢月份", all_months)
        
        # 1. 年度累計統計邏輯
        sel_year = int(sel_month.split('-')[0])
        year_data = df[df['Year'] == sel_year]
        
        y_inc = year_data[year_data["收支類型"] == "收入"]["金額"].sum()
        y_exp = year_data[year_data["收支類型"] == "支出"]["金額"].sum()
        y_bal = y_inc - y_exp
        
        st.markdown(f"### 🗓️ {sel_year} 年度累計統計")
        yc1, yc2, yc3 = st.columns(3)
        yc1.metric("總收入", f"{y_inc:,.0f}")
        yc2.metric("總支出", f"{y_exp:,.0f}")
        yc3.metric("總結餘", f"{y_bal:,.0f}")
        st.markdown("---")

        # 2. 當月明細顯示
        m_df = df[df['Month'] == sel_month].copy()
        if not m_df.empty:
            st.write(f"📅 {sel_month} 明細表 (Tiffany藍為收入)")
            
            def highlight_income(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            # 顯示表格（包含 Index 用於刪除參考）
            disp = m_df[["日期", "分類項目", "金額", "收支類型", "備註"]].copy()
            disp['日期'] = disp['日期'].dt.strftime('%m-%d')
            
            st.dataframe(disp.style.apply(highlight_income, axis=1).format({"金額": "{:,.0f}"}), 
                         use_container_width=True)

            # 3. 刪除紀錄功能
            with st.expander("🗑️ 刪除紀錄"):
                st.write("請對照上方表格最左側的編號 (Index) 進行刪除")
                del_index = st.number_input("輸入要刪除的編號", min_value=0, max_value=int(df.index.max()), step=1)
                if st.button("⚠️ 確認刪除單筆紀錄", type="primary"):
                    # 執行刪除
                    df_dropped = df.drop(del_index).reset_index(drop=True)
                    # 轉回日期字串存回 Google Sheets
                    df_dropped['日期'] = pd.to_datetime(df_dropped['日期']).dt.strftime('%Y-%m-%d')
                    # 移除輔助欄位
                    if 'Month' in df_dropped.columns: df_dropped = df_dropped.drop(columns=['Month'])
                    if 'Year' in df_dropped.columns: df_dropped = df_dropped.drop(columns=['Year'])
                    
                    conn.update(data=df_dropped)
                    st.warning(f"編號 {del_index} 已刪除")
                    st.rerun()
        else:
            st.warning("該月份無資料")
    else:
        st.info("尚未連動資料或 Google Sheet 為空。")
