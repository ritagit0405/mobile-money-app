import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- 1. 頁面配置 ---
st.set_page_config(page_title="手機雲端帳本", layout="centered")

# 針對手機版 RWD 優化 CSS
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { 
        font-size: 18px !important; 
        font-weight: bold; 
    }
    [data-testid="stMetricLabel"] { 
        font-size: 13px !important; 
    }
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] { font-size: 14px !important; }
    .stDataFrame div { font-size: 12px !important; }
    h3 { font-size: 1.1rem !important; margin-bottom: 8px !important; }
    .stSubheader { margin-top: -10px !important; }
    </style>
    """, unsafe_allow_html=True)

st.subheader("💰 手機雲端帳本")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl=0)
        data['日期'] = pd.to_datetime(data['日期'], errors='coerce')
        data = data.dropna(subset=['日期'])
        data['金額'] = pd.to_numeric(data['金額'], errors='coerce').fillna(0)
        # 事先建立年份與月份欄位
        data['Year'] = data['日期'].dt.year
        data['Month_Num'] = data['日期'].dt.month
        data['Month_Str'] = data['日期'].dt.strftime('%Y-%m')
        return data
    except:
        return pd.DataFrame(columns=["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註", "Year", "Month_Num", "Month_Str"])

df = load_data()

# --- 2. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📝 新增", "📊 消費分析", "📜 消費明細"])

# --- Tab 1: 新增紀錄 ---
with tab1:
    st.markdown("### ➕ 新增帳目")
    t_choice = st.radio("類型", ["支出", "收入"], horizontal=True)
    cats = ["薪資", "獎金", "投資", "其他"] if t_choice == "收入" else ["飲食", "孝親費", "購物", "稅金", "娛樂", "醫療費", "電信費", "交通", "其他"]
    
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("日期", datetime.date.today())
        c = st.selectbox("分類項目", cats)
        a = st.number_input("金額 (TWD)", min_value=0, step=1)
        m = st.selectbox("支出方式", ["現金", "信用卡", "轉帳"]) if t_choice == "支出" else " "
        n = st.text_input("備註")
        if st.form_submit_button("確認儲存 💾", use_container_width=True):
            if a > 0:
                new_row = pd.DataFrame([{"日期": d, "分類項目": c, "收支類型": t_choice, "金額": a, "結餘": a if t_choice == "收入" else -a, "支出方式": m, "備註": n}])
                updated = pd.concat([df.drop(columns=['Year', 'Month_Num', 'Month_Str'], errors='ignore'), new_row], ignore_index=True)
                updated['日期'] = pd.to_datetime(updated['日期']).dt.strftime('%Y-%m-%d')
                conn.update(data=updated)
                st.success("✅ 儲存成功！")
                st.rerun()

# --- Tab 2: 分析 ---
with tab2:
    if not df.empty:
        all_years_analysis = sorted(df['Year'].unique(), reverse=True)
        sel_y_analysis = st.selectbox("📅 選擇分析年份", all_years_analysis, key="analysis_y")
        
        y_exp = df[(df["收支類型"] == "支出") & (df['Year'] == sel_y_analysis)]
        
        if not y_exp.empty:
            st.write(f"📊 {sel_y_analysis} 支出比例分析")
            fig = px.pie(y_exp.groupby("分類項目")["金額"].sum().reset_index(), 
                         values='金額', names='分類項目', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示該年總支出
            total_y_e = y_exp["金額"].sum()
            st.info(f"💡 {sel_y_analysis} 年度總支出金額：NT$ {total_y_e:,.0f}")
        else:
            st.warning(f"{sel_y_analysis} 年暫無支出數據")
    else:
        st.info("暫無數據")

# --- Tab 3: 消費明細 ---
with tab3:
    if not df.empty:
        # 1. 選擇年份
        all_years = sorted(df['Year'].unique(), reverse=True)
        sel_y = st.selectbox("📅 選擇年份", all_years, key="detail_y")
        
        # 2. 選擇月份 (根據選擇的年份過濾出有的月份)
        available_months = sorted(df[df['Year'] == sel_y]['Month_Num'].unique(), reverse=True)
        month_options = [f"{sel_y}-{m:02d}" for m in available_months]
        sel_m_str = st.selectbox("🔍 選擇月份", month_options)
        sel_m = int(sel_m_str.split('-')[1])

        # --- 資料計算 ---
        m_df = df[(df['Year'] == sel_y) & (df['Month_Num'] == sel_m)].copy()
        m_i = m_df[m_df["收支類型"] == "收入"]["金額"].sum()
        m_e = m_df[m_df["收支類型"] == "支出"]["金額"].sum()

        y_df = df[df['Year'] == sel_y]
        y_i = y_df[y_df["收支類型"] == "收入"]["金額"].sum()
        y_e = y_df[y_df["收支類型"] == "支出"]["金額"].sum()

        # --- 月度摘要 ---
        st.markdown(f"### 📅 {sel_m_str} 摘要")
        col1, col2 = st.columns(2)
        col1.metric("月收入", f"{m_i:,.0f}")
        col2.metric("月支出", f"{m_e:,.0f}")
        st.metric("本月結餘", f"{(m_i-m_e):,.0f}")

        # --- 年度摘要 ---
        st.markdown(f"### 🗓️ {sel_y} 年度累計")
        ycol1, ycol2 = st.columns(2)
        ycol1.metric("年收入", f"{y_i:,.0f}")
        ycol2.metric("年支出", f"{y_e:,.0f}")
        st.metric("年度總結餘", f"{(y_i-y_e):,.0f}")
        
        st.markdown("---")

        # --- 完整明細表 ---
        if not m_df.empty:
            def style_row(row):
                return ['color: #81D8D0' if row['收支類型'] == '收入' else '' for _ in row]
            
            disp = m_df.copy()
            disp['日期'] = disp['日期'].dt.strftime('%m-%d')
            disp = disp[["日期", "分類項目", "收支類型", "金額", "結餘", "支出方式", "備註"]]
            
            st.write("📖 明細表 (可左右滑動)")
            st.dataframe(
                disp.style.apply(style_row, axis=1).format({"金額": "{:,.0f}", "結餘": "{:,.0f}"}), 
                use_container_width=True
            )

            with st.expander("🗑️ 刪除紀錄"):
                st.write("請輸入表格對應的原始編號 (Index)：")
                del_idx = st.number_input("編號 (Index)", min_value=0, max_value=int(df.index.max()), step=1)
                if st.button("⚠️ 確認刪除", type="primary", use_container_width=True):
                    # 刪除並存回 Google Sheets
                    new_df = df.drop(del_idx).reset_index(drop=True)
                    # 存檔前移除輔助計算欄位
                    save_df = new_df.drop(columns=['Year', 'Month_Num', 'Month_Str'], errors='ignore')
                    save_df['日期'] = pd.to_datetime(save_df['日期']).dt.strftime('%Y-%m-%d')
                    conn.update(data=save_df)
                    st.success("已成功刪除")
                    st.rerun()
    else:
        st.info("尚無資料")
