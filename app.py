import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

# RWD 手機優化樣式
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 18px !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { font-size: 12px !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    .stTabs [data-baseweb="tab"] { font-size: 14px !important; width: 33% !important; padding: 5px 0px !important; }
    .stDataFrame div { font-size: 12px !important; }
    h3 { font-size: 1.1rem !important; margin-bottom: 5px !important; }
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

# --- Tab 3: 歷史紀錄 (修正 KeyError) ---
with tab3:
    if not df.empty:
        df['Month'] = df['日期'].dt.strftime('%Y-%m')
        df['Year'] = df['日期'].dt.year
        all_m = sorted(df['Month'].unique(), reverse=True)
        sel_m = st.selectbox("🔍 選擇月份", all_m)
        sel_y = int(sel_m.split('-')[0])

        # 財務摘要
        m_df = df[df['Month'] == sel_m].copy()
        m_i = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
        m_e = m_df[m_df["收支類型"] == "支出"]["金額"].sum()

        st.markdown(f"### 📅 {sel_m} 摘要")
        c1, c2, c3 = st.columns(3)
        c1.metric("月收入", f"{m_i:,.0f}")
        c2.metric("月支出", f"{m_e:,.0f}")
        c3.metric("月結餘", f"{(m_i-m_e):,.0f}")

        # 年度統計
        y_df = df[df['Year'] == sel_y]
        y_i = y_df[y_df["收支類型"] == "收入"]["金額"].sum()
        y_e = y_df[y_df["收支類型"] == "支出"]["金額"].sum()

        st.markdown(f"### 🗓️ {sel_y} 年度統計")
        yc1, yc2, yc3 = st.columns(3)
        yc1.metric("年收入", f"{y_i:,.0f}")
        yc2.metric("年支出", f"{y_e:,.0f}")
        yc3.metric("年結餘", f"{(y_i-y_e):,.0f}")
        
        st.markdown("---")

        if not m_df.empty:
            # 染色函數
            def style_inc(row):
                # 這裡需要 '收支類型' 欄位來做判斷
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            # 準備顯示用的資料，必須包含 '收支類型' 否則會 KeyError
            disp = m_df.copy()
            disp['日期'] = disp['日期'].dt.strftime('%m-%d')
            # 關鍵修正：保留 '收支類型'，但後面顯示時會控制寬度或隱藏
            disp = disp[["日期", "分類項目", "金額", "收支類型"]]
            
            # 使用 column_order 來隱藏 '收支類型'，讓手機畫面乾淨，但程式邏輯仍能讀到它
            st.dataframe(
                disp.style.apply(style_inc, axis=1).format({"金額": "{:,.0f}"}), 
                use_container_width=True,
                column_order=("日期", "分類項目", "金額") # 隱藏收支類型
            )

            with st.expander("🗑️ 刪除紀錄"):
                del_idx = st.number_input("輸入編號 (Index)", min_value=0, max_value=int(df.index.max()), step=1)
                if st.button("⚠️ 確認刪除", type="primary"):
                    new_df = df.drop(del_idx).reset_index(drop=True)
                    new_df['日期'] = new_df['日期'].dt.strftime('%Y-%m-%d')
                    save_df = new_df.drop(columns=['Month', 'Year']) if 'Month' in new_df.columns else new_df
                    conn.update(data=save_df)
                    st.success("已刪除")
                    st.rerun()
    else:
        st.info("尚無資料")
