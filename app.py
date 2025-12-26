import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

# RWD 手機版樣式微調
st.markdown("""
    <style>
    /* 調整 subheader 的邊距，讓畫面更緊湊 */
    .stMarkdown h2 {
        margin-top: -10px !important;
        margin-bottom: 5px !important;
        text-align: center;
    }
    
    /* 確保統計指標在手機上清晰且不重疊 */
    [data-testid="stMetricValue"] { 
        font-size: 18px !important; 
        font-weight: bold; 
    }
    [data-testid="stMetricLabel"] { 
        font-size: 13px !important; 
    }
    
    /* 表格字體優化 */
    .stDataFrame div { font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# 使用您提議的 subheader
st.subheader("📱 手機雲端帳本")

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
    st.write("### ➕ 新增帳目")
    t_choice = st.radio("類型", ["支出", "收入"], horizontal=True)
    cats = ["薪資", "獎金", "投資", "其他"] if t_choice == "收入" else ["飲食", "交通", "購物", "稅金", "娛樂", "醫療費", "電信費", "其他"]
    
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("日期", datetime.date.today())
        c = st.selectbox("分類項目", cats)
        a = st.number_input("金額 (TWD)", min_value=0, step=1)
        m = st.selectbox("方式", ["現金", "信用卡", "轉帳"]) if t_choice == "支出" else " "
        n = st.text_input("備註")
        if st.form_submit_button("確認儲存 💾", use_container_width=True):
            if a > 0:
                new_row = pd.DataFrame([{"日期": d, "分類項目": c, "收支類型": t_choice, "金額": a, "結餘": a if t_choice == "收入" else -a, "支出方式": m, "備註": n}])
                updated = pd.concat([df, new_row], ignore_index=True)
                updated['日期'] = pd.to_datetime(updated['日期']).dt.strftime('%Y-%m-%d')
                conn.update(data=updated)
                st.success("✅ 儲存成功！")
                st.rerun()

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

# --- Tab 3: 歷史紀錄 (採用穩定排版) ---
with tab3:
    if not df.empty:
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        df['Year'] = df['日期'].dt.year
        all_m = sorted(df['Month'].unique(), reverse=True)
        sel_m = st.selectbox("🔍 選擇月份", all_m)
        sel_y = int(sel_m.split('-')[0])

        m_df = df[df['Month'] == sel_m].copy()
        m_i = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
        m_e = m_df[m_df["收支類型"] == "支出"]["金額"].sum()

        y_df = df[df['Year'] == sel_y]
        y_i = y_df[y_df["收支類型"] == "收入"]["金額"].sum()
        y_e = y_df[y_df["收支類型"] == "支出"]["金額"].sum()

        # 摘要排版優化：收入支出並列，結餘獨立
        st.write(f"### 📅 {sel_m} 摘要")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("月收入", f"{m_i:,.0f}")
        m_col2.metric("月支出", f"{m_e:,.0f}")
        st.metric("本月結餘", f"{(m_i-m_e):,.0f}")

        st.write(f"### 🗓️ {sel_y} 年度累計")
        y_col1, y_col2 = st.columns(2)
        y_col1.metric("年收入", f"{y_i:,.0f}")
        y_col2.metric("年支出", f"{y_e:,.0f}")
        st.metric("年度總結餘", f"{(y_i-y_e):,.0f}")
        
        st.markdown("---")

        # 明細表支援橫滑
        if not m_df.empty:
            def style_row(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            disp = m_df.copy()
            disp['日期'] = disp['日期'].dt.strftime('%m-%d')
            disp = disp[["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註"]]
            
            st.write("📖 明細表 (左右滑動)")
            st.dataframe(
                disp.style.apply(style_row, axis=1).format({"金額": "{:,.0f}", "結餘": "{:,.0f}"}), 
                use_container_width=True
            )

            with st.expander("🗑️ 刪除紀錄"):
                del_idx = st.number_input("輸入 Index 編號", min_value=0, max_value=int(df.index.max()), step=1)
                if st.button("⚠️ 確認刪除", type="primary", use_container_width=True):
                    new_df = df.drop(del_idx).reset_index(drop=True)
                    new_df['日期'] = new_df['日期'].dt.strftime('%Y-%m-%d')
                    save_df = new_df.drop(columns=['Month', 'Year']) if 'Month' in new_df.columns else new_df
                    conn.update(data=save_df)
                    st.success("已成功刪除！")
                    st.rerun()
    else:
        st.info("尚無資料")
