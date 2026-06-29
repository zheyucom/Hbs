import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- 页面基础配置 ---
st.set_page_config(page_title="我们的科研小空间", page_icon="🔬", layout="wide")
st.title("🔬 我们的科研小空间")
st.markdown("记录每天的踩坑与灵光一现。")

# --- 连接 Supabase 数据库 ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- 网页布局分栏 ---
col1, col2 = st.columns([1, 2])

# --- 左侧：新建日志区 ---
with col1:
    st.header("📝 写新日志")
    with st.form("new_log_form"):
        date = st.date_input("日期", datetime.today())
        author = st.selectbox("记录人", ["研究员 A", "研究员 B"])
        
        research_type = st.radio(
            "研究方向", 
            ["临床预测模型 (如 早期休克预测)", "基础实验 (如 蛋白/RNA 提取)", "文献阅读与综述撰写", "其他"]
        )
        progress = st.text_area("今日进展 (清洗了哪些特征？跑了什么模型？)", height=150)
        code_or_params = st.text_area("代码 snippet / SQL 语句 / 实验参数", height=150)
        mood = st.slider("今日科研心情指数", 1, 10, 7)
        
        submitted = st.form_submit_button("提交日志")
        
        if submitted:
            if progress.strip() == "":
                st.warning("进展总得写两句吧！")
            else:
                # 将数据插入 Supabase
                new_data = {
                    "date": date.strftime("%Y-%m-%d"),
                    "author": author,
                    "research_type": research_type,
                    "progress": progress,
                    "code_or_params": code_or_params,
                    "mood": mood
                }
                supabase.table("research_logs").insert(new_data).execute()
                st.success("🎉 提交成功！继续加油！")
                st.rerun()

# --- 右侧：历史时间线 ---
with col2:
    st.header("🕰️ 历史日志墙")
    
    # 从数据库读取数据并按 ID 倒序排列（最新的在最上面）
    response = supabase.table("research_logs").select("*").order("id", desc=True).execute()
    data = response.data
    
    if not data:
        st.info("还没有任何记录，快来写下第一篇吧！")
    else:
        df = pd.DataFrame(data)
        filter_author = st.multiselect("筛选记录人", df["author"].unique(), default=df["author"].unique())
        filtered_df = df[df["author"].isin(filter_author)]
        
        for index, row in filtered_df.iterrows():
            with st.container():
                st.markdown(f"### {row['date']} | {row['author']}")
                st.caption(f"🏷️ 方向: {row['research_type']} | 🌟 心情: {row['mood']}/10")
                st.write(row['progress'])
                
                if pd.notna(row['code_or_params']) and row['code_or_params'].strip() != "":
                    with st.expander("查看代码 / 参数详情"):
                        st.code(row['code_or_params'])
                
                st.markdown("---")