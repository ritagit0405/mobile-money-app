import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 基本設定與手機版 CSS ---
st.set_page_config(page_title="雲端帳本", layout="centered") # 手機建議用 centered

st.markdown("""
    <style>
    /* 調整手機版字體與指標卡片 */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: bold;
    }
    .stDataFrame div {
        font-size: 14px !important;
    }
    /* 讓 Tab 標題更明顯 */
    button[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: bold;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl=0)
        data['日期'] = pd.to_datetime(data['日期'], errors='coerce')
        data = data.dropna(subset=['日期'])
        data = data.sort_values(by="日期", ascending=False).reset_index(drop=True)
        data['金額'] = pd.to_numeric(data['金額'], errors='coerce').fillna(0)
        return data
    except Exception as e:
        return pd.DataFrame(columns=["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註"])

df = load_data()

# --- 2. 功能分頁導覽 (模仿手機 Tab) ---
tab1, tab2, tab3 = st.tabs(["📝 新增", "📊 分析", "📜 歷史"])

# --- 第一頁：新增紀錄 ---
with tab1:
    st.subheader("➕ 新增收支明細")
    date_val = st.date_input("選擇日期", datetime.date.today())
    type_option = st.selectbox("收入/支出", ["支出", "收入"])
    category_list = ["飲食", "交通", "購物", "住房", "教育", "娛樂", "其他", "孝親費"] if type_option == "支出" else ["薪資", "獎金", "投資", "其他"]
    category = st.selectbox("分類項目", category_list)
    amount = st.number_input("金額 (TWD)", min_value=0, step=1)
    pay_method = st.selectbox("方式", ["現金", "信用卡", "轉帳"]) if type_option == "支出" else " "
    note = st.text_input("備註")

    if st.button("確認儲存 💾", use_container_width=True):
        new_entry = pd.DataFrame([{
            "日期": date_val, "分類項目": category, "收支類型": type_option,
            "金額": amount, "結餘": amount if type_option == "收入" else -amount,
            "支出方式": pay_method, "備註": note
        }])
        updated_df = pd.concat([df, new_entry], ignore_index=True)
        updated_df['日期'] = pd.to_datetime(updated_df['日期']).dt.strftime('%Y-%m-%d')
        conn.update(data=updated_df)
        st.success("✅ 已存入雲端！")
        st.rerun()

# --- 第二頁：數據分析 ---
with tab2:
    if not df.empty:
        st.subheader("📊 年度支出佔比")
        current_year = datetime.date.today().year
        year_expense_df = df[(df["收支類型"] == "支出") & (df['日期'].dt.year == current_year)].copy()
        
        if not year_expense_df.empty:
            pie_data = year_expense_df.groupby("分類項目", as_index=False)["金額"].sum()
            fig = px.pie(pie_data, values='金額', names='分類項目', hole=0.5, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0)) # 減少邊距適合手機
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        # 年度累計統計
        y_income = df[df["收支類型"] == "收入"]["金額"].sum()
        y_expense = df[df["收支類型"] == "支出"]["金額"].sum()
        st.metric("🏛️ 年度總結餘", f"{(y_income - y_expense):,.0f} 元")
    else:
        st.info("尚無數據")

# --- 第三頁：歷史明細管理 ---
with tab3:
    if not df.empty:
        # 月份篩選
        all_months = sorted(df['日期'].dt.strftime('%Y-%m').unique(), reverse=True)
        history_month = st.selectbox("🔍 選擇月份", all_months)
        
        history_df = df[df['日期'].dt.strftime('%Y-%m') == history_month].copy()
        m_income = history_df[history_df["收支類型"] == "收入"]["金額"].sum()
        m_expense = history_df[history_df["收支類型"] == "支出"]["金額"].sum()

        col1, col2 = st.columns(2)
        col1.metric("💰 收入", f"{m_income:,.0f}")
        col2.metric("💸 支出", f"{m_expense:,.0f}")

        # Tiffany 藍字呈現
        def style_row(row):
            color = '#81D8D0' if row['收支類型'] == '收入' else ''
            return [f'color: {color}' for _ in row]

        display_df = history_df.copy()
        display_df['日期'] = display_df['日期'].dt.strftime('%m-%d') # 手機版簡化日期顯示
        
        styled_df = display_df[["日期", "分類項目", "金額", "收支類型"]].style.apply(style_row, axis=1).format({"金額": "{:,.0f}"})
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        with st.expander("🗑️ 刪除紀錄"):
            row_to_del = st.number_input("輸入編號 (從全部清單中)", step=1)
            if st.button("確認刪除"):
                # 注意：這裡需對應原始 df 索引刪除
                st.warning("功能開發中，請先於雲端表單手動刪除")
    else:
        st.info("尚無數據")