import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

# 針對手機版進行字體與佈局的細節微調
st.markdown("""
    <style>
    /* 1. 縮小統計數值的字體，避免重疊 */
    [data-testid="stMetricValue"] { 
        font-size: 20px !important; 
        font-weight: bold; 
    }
    /* 2. 縮小統計標籤的字體 */
    [data-testid="stMetricLabel"] { 
        font-size: 13px !important; 
    }
    /* 3. 讓卡片在空間不足時自動換行 */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    /* 4. 調整 Tab 標籤，讓它在手機上不會擠成一團 */
    .stTabs [data-baseweb="tab"] { 
        font-size: 15px !important; 
        width: 33% !important; 
        padding: 5px 0px !important;
    }
    /* 5. 縮小歷史表格字體 */
    .stDataFrame div {
        font-size: 12px !important;
    }
    /* 6. 標題縮小一點，避免像圖片中那樣斷行 */
    h3 {
        font-size: 1.2rem !important;
    }
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
    # 使用 radio 並設為橫向，省空間
    t_choice = st.radio("類型", ["支出", "收入"], horizontal=True)
    
    if t_choice == "收入":
        cats = ["薪資", "獎金", "投資", "其他"]
    else:
        cats = ["飲食", "交通", "購物", "稅金", "娛樂", "醫療費", "電信費", "其他"]
    
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("日期", datetime.date.today())
        c = st.selectbox("分類", cats)
        a = st.number_input("金額", min_value=0, step=1)
        m = st.selectbox("方式", ["現金", "信用卡", "轉帳"]) if t_choice == "支出" else " "
        n = st.text_input("備註")
        
        if st.form_submit_button("確認儲存", use_container_width=True):
            if a > 0:
                new_row = pd.DataFrame([{"日期": d, "分類項目": c, "收支類型": t_choice, "金額": a, "結餘": a if t_choice == "收入" else -a, "支出方式": m, "備註": n}])
                updated = pd.concat([df, new_row], ignore_index=True)
                updated['日期'] = pd.to_datetime(updated['日期']).dt.strftime('%Y-%m-%d')
                conn.update(data=updated)
                st.success("儲存成功！")
                st.rerun()
            else:
                st.warning("請輸入金額")

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        curr_y = datetime.date.today().year
        y_exp = df[(df["收支類型"] == "支出") & (df['日期'].dt.year == curr_y)]
        if not y_exp.empty:
            st.write(f"📊 {curr_y} 支出佔比")
            fig = px.pie(y_exp.groupby("分類項目")["金額"].sum().reset_index(), values='金額', names='分類項目', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無數據")

# --- Tab 3: 歷史紀錄 (手機排版修復版) ---
with tab3:
    if not df.empty:
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        df['Year'] = df['日期'].dt.year
        all_m = sorted(df['Month'].unique(), reverse=True)
        sel_m = st.selectbox("🔍 選擇月份", all_m)
        sel_y = int(sel_m.split('-')[0])

        # 月度摘要 (標題變小)
        st.markdown(f"### 📅 {sel_m} 摘要")
        m_df = df[df['Month'] == sel_m].copy()
        m_i = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
        m_e = m_df[m_df["收支類型"] == "支出"]["金額"].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("當月收入", f"{m_i:,.0f}")
        col2.metric("當月支出", f"{m_e:,.0f}")
        col3.metric("月結餘", f"{(m_i-m_e):,.0f}")

        # 年度統計
        st.markdown(f"### 🗓️ {sel_y} 年度統計")
        y_df = df[df['Year'] == sel_year]
        y_i = y_df[y_df["收支類型"] == "收入"]["金額"].sum()
        y_e = y_df[y_df["收支類型"] == "支出"]["金額"].sum()

        yc1, yc2, yc3 = st.columns(3)
        yc1.metric("年度收入", f"{y_i:,.0f}")
        yc2.metric("年度支出", f"{y_e:,.0f}")
        yc3.metric("年結餘", f"{(y_i-y_e):,.0f}")
        
        st.markdown("---")

        if not m_df.empty:
            def style_inc(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            # 手機版隱藏非必要欄位以維持表格整潔
            disp = m_df.copy()
            disp['日期'] = disp['日期'].dt.strftime('%m-%d')
            disp = disp[["日期", "分類項目", "收支類型", "金額"]]
            
            st.dataframe(disp.style.apply(style_inc, axis=1).format({"金額": "{:,.0f}"}), use_container_width=True, hide_index=False)

            with st.expander("🗑️ 刪除紀錄"):
                del_idx = st.number_input("輸入 Index 編號", min_value=0, max_value=int(df.index.max()), step=1)
                if st.button("⚠️ 執行刪除", type="primary"):
                    new_df = df.drop(del_idx).reset_index(drop=True)
                    new_df['日期'] = new_df['日期'].dt.strftime('%Y-%m-%d')
                    save_df = new_df.drop(columns=['Month', 'Year']) if 'Month' in new_df.columns else new_df
                    conn.update(data=save_df)
                    st.success("已刪除")
                    st.rerun()
    else:
        st.info("尚無資料")
