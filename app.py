import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="wide") # 使用 wide 模式讓卡片並排更好看

# 優化字體與間距
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { font-size: 16px !important; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; width: 33%; }
    hr { margin-top: 1rem; margin-bottom: 1rem; }
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
                new_row = pd.DataFrame([{"日期": d, "分類項目": c, "收支類型": type_choice, "金額": a, "結餘": a if type_choice == "收入" else -a, "支出方式": m, "備註": n}])
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
            fig = px.pie(year_exp.groupby("分類項目")["金額"].sum().reset_index(), values='金額', names='分類項目', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無數據")

# --- Tab 3: 歷史紀錄 (比照圖片樣式完全重製) ---
with tab3:
    if not df.empty:
        # 預處理日期資訊
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        df['Year'] = df['日期'].dt.year
        all_months = sorted(df['Month'].unique(), reverse=True)
        
        # 月份選擇器
        sel_month = st.selectbox("🔍 選擇查詢月份", all_months)
        sel_year = int(sel_month.split('-')[0])

        # --- 第一部分：當月財務摘要 ---
        st.markdown(f"### 📅 {sel_month} 財務摘要")
        m_df = df[df['Month'] == sel_month].copy()
        m_inc = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
        m_exp = m_df[m_df["收支類型"] == "支出"]["金額"].sum()
        m_bal = m_inc - m_exp

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("💰 當月總收入", f"{m_inc:,.0f} 元")
        mc2.metric("💸 當月總支出", f"{m_exp:,.0f} 元")
        mc3.metric("⚖️ 本月結餘", f"{m_bal:,.0f} 元")

        # --- 第二部分：當年度累計統計 ---
        st.markdown(f"### 🗓️ {sel_year} 年度累計統計")
        y_df = df[df['Year'] == sel_year]
        y_inc = y_df[y_df["收支類型"] == "收入"]["金額"].sum()
        y_exp = y_df[y_df["收支類型"] == "支出"]["金額"].sum()
        y_bal = y_inc - y_exp

        yc1, yc2, yc3 = st.columns(3)
        yc1.metric("📈 當年度總收入", f"{y_inc:,.0f} 元")
        yc2.metric("📉 當年度總支出", f"{y_exp:,.0f} 元")
        yc3.metric("🏛️ 當年度總結餘", f"{y_bal:,.0f} 元")
        
        st.markdown("---")

        # --- 第三部分：明細表格 ---
        if not m_df.empty:
            def style_row(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            # 格式化日期與選取欄位
            disp = m_df.copy()
            disp['日期'] = disp['日期'].dt.strftime('%Y-%m-%d')
            disp = disp[["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註"]]
            
            st.dataframe(disp.style.apply(style_row, axis=1).format({"金額": "{:,.0f}", "結餘": "{:,.0f}"}), use_container_width=True)

            # --- 第四部分：刪除紀錄功能 ---
            with st.expander("🗑️ 刪除單筆紀錄"):
                st.write("請對照上方表格最左側的編號進行刪除：")
                del_idx = st.number_input("輸入要刪除的編號 (Index)", min_value=0, max_value=int(df.index.max()), step=1)
                if st.button("⚠️ 確認刪除", type="primary"):
                    # 執行刪除並清理暫存欄位
                    new_df = df.drop(del_idx).reset_index(drop=True)
                    new_df['日期'] = new_df['日期'].dt.strftime('%Y-%m-%d')
                    # 存回前移除輔助欄位
                    save_df = new_df.drop(columns=['Month', 'Year']) if 'Month' in new_df.columns else new_df
                    
                    conn.update(data=save_df)
                    st.success(f"已成功刪除編號 {del_idx} 的紀錄！")
                    st.rerun()
        else:
            st.warning("該月份無明細資料")
    else:
        st.info("目前尚無資料，請先至「新增」分頁建立第一筆紀錄。")
