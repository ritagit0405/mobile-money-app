import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

# 極致手機版並排優化：消除所有間距並縮小字體
st.markdown("""
    <style>
    /* 1. 強制所有橫向區塊不換行且消除間距 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0px !important; /* 消除中間空隙 */
    }
    
    /* 2. 讓三個欄位平均分配極窄的寬度 */
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
        padding: 0px 1px !important; /* 極小內距防止貼邊 */
    }

    /* 3. 針對數值與標籤縮小到極限，確保不超出畫面 */
    [data-testid="stMetricLabel"] {
        font-size: 10px !important;
        color: #999 !important;
        margin-bottom: -5px !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 13px !important; /* 再次縮小以適應寬度 */
        font-weight: bold;
    }

    /* 4. 標題與分頁微調 */
    h3 { font-size: 0.95rem !important; margin: 10px 0 5px 0 !important; }
    .stTabs [data-baseweb="tab"] { font-size: 13px !important; }
    
    /* 5. 表格字體保持適中並支援橫滑 */
    .stDataFrame div { font-size: 11px !important; }
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
    t_choice = st.radio("類型", ["支出", "收入"], horizontal=True)
    cats = ["薪資", "獎金", "投資", "其他"] if t_choice == "收入" else ["飲食", "交通", "購物", "稅金", "娛樂", "醫療費", "電信費", "其他"]
    
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("日期", datetime.date.today())
        c = st.selectbox("分類項目", cats)
        a = st.number_input("金額 (TWD)", min_value=0, step=1)
        m = st.selectbox("支出方式", ["現金", "信用卡", "轉帳"]) if t_choice == "支出" else " "
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
            st.write(f"📊 {curr_y} 支出分析")
            fig = px.pie(y_exp.groupby("分類項目")["金額"].sum().reset_index(), values='金額', names='分類項目', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暫無數據")

# --- Tab 3: 歷史紀錄 (修正並排超出問題) ---
with tab3:
    if not df.empty:
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        df['Year'] = df['日期'].dt.year
        all_m = sorted(df['Month'].unique(), reverse=True)
        sel_m = st.selectbox("🔍 選擇月份", all_m)
        sel_y = int(sel_m.split('-')[0])

        # 月摘要 - 極致並排
        st.markdown(f"### 📅 {sel_m} 摘要")
        m_df = df[df['Month'] == sel_m].copy()
        m_i = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
        m_e = m_df[m_df["收支類型"] == "支出"]["金額"].sum()

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("月收入", f"{m_i:,.0f}")
        mc2.metric("月支出", f"{m_e:,.0f}")
        mc3.metric("月結餘", f"{(m_i-m_e):,.0f}")

        # 年累計 - 極致並排
        st.markdown(f"### 🗓️ {sel_y} 年度累計")
        y_df = df[df['Year'] == sel_y]
        y_i = y_df[y_df["收支類型"] == "收入"]["金額"].sum()
        y_e = y_df[y_df["收支類型"] == "支出"]["金額"].sum()

        yc1, yc2, yc3 = st.columns(3)
        yc1.metric("年收入", f"{y_i:,.0f}")
        yc2.metric("年支出", f"{y_e:,.0f}")
        yc3.metric("年結餘", f"{(y_i-y_e):,.0f}")
        
        st.markdown("---")

        # 完整明細表 (支援橫向捲動)
        if not m_df.empty:
            def style_row(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            disp = m_df.copy()
            disp['日期'] = disp['日期'].dt.strftime('%Y-%m-%d')
            disp = disp[["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註"]]
            
            st.write("📖 明細 (可左右滑動)")
            st.dataframe(
                disp.style.apply(style_row, axis=1).format({"金額": "{:,.0f}", "結餘": "{:,.0f}"}), 
                use_container_width=True
            )

            # 刪除紀錄
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
