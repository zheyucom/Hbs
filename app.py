import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- 页面基础配置 ---
st.set_page_config(page_title="我们的科研小空间", page_icon="🔬", layout="wide")

# --- 连接 Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- 初始化登录状态 ---
if 'user' not in st.session_state:
    st.session_state.user = None

# ==========================================
# 模块 1：登录与注册页面
# ==========================================
def login_page():
    st.title("🔐 欢迎来到专属科研空间")
    st.markdown("请先登录或注册您的账号。")
    
    # 用标签页区分登录和注册
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        st.subheader("账号登录")
        email = st.text_input("邮箱", key="login_email")
        password = st.text_input("密码", type="password", key="login_password")
        if st.button("登录"):
            try:
                # 调用 Supabase 的登录接口
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = response.user
                st.success("登录成功！")
                st.rerun()
            except Exception as e:
                st.error(f"登录失败，请检查账号密码。")

    with tab2:
        st.subheader("新账号注册")
        new_email = st.text_input("邮箱", key="reg_email")
        new_password = st.text_input("密码 (至少6位)", type="password", key="reg_password")
        if st.button("注册"):
            try:
                # 调用 Supabase 的注册接口
                response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("注册成功！请切换到登录页面进行登录。")
            except Exception as e:
                st.error(f"注册失败：{e}")

# ==========================================
# 模块 2：主界面（科研日志空间）
# ==========================================
def main_page():
    # 顶部导航栏：显示当前用户和退出按钮
    col_nav1, col_nav2 = st.columns([8, 1])
    with col_nav1:
        st.title("🔬 我们的科研小空间")
    with col_nav2:
        if st.button("退出登录"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()
            
    st.markdown(f"**当前在线：** {st.session_state.user.email}")
    st.divider() # 一条分割线

    col1, col2 = st.columns([1, 2])

    # --- 左侧：新建日志 ---
    with col1:
        st.header("📝 写新日志")
        with st.form("new_log_form"):
            date = st.date_input("日期", datetime.today())
            # 这里的记录人自动变成当前登录的邮箱，不需要再手动选了！
            author = st.session_state.user.email 
            
            research_type = st.radio(
                "研究方向", 
                ["临床预测模型 (如 早期休克预测)", "基础实验 (如 蛋白/RNA 提取)", "文献阅读与综述撰写", "其他"]
            )
            progress = st.text_area("今日进展", height=150)
            code_or_params = st.text_area("代码 / 实验参数", height=100)
            mood = st.slider("今日心情指数", 1, 10, 7)
            
            submitted = st.form_submit_button("提交日志")
            
            if submitted and progress.strip():
                new_data = {
                    "date": date.strftime("%Y-%m-%d"),
                    "author": author,
                    "research_type": research_type,
                    "progress": progress,
                    "code_or_params": code_or_params,
                    "mood": mood
                }
                supabase.table("research_logs").insert(new_data).execute()
                st.success("提交成功！")
                st.rerun()

    # --- 右侧：历史日志墙 ---
    with col2:
        st.header("🕰️ 历史日志墙")
        response = supabase.table("research_logs").select("*").order("id", desc=True).execute()
        data = response.data
        
        if not data:
            st.info("还没有任何记录，快写下第一篇吧！")
        else:
            df = pd.DataFrame(data)
            # 简单的筛选功能保留
            filter_author = st.multiselect("筛选记录人", df["author"].unique(), default=df["author"].unique())
            filtered_df = df[df["author"].isin(filter_author)]
            
            for index, row in filtered_df.iterrows():
                with st.container():
                    st.markdown(f"### {row['date']} | 👤 {row['author'].split('@')[0]}")
                    st.caption(f"🏷️ 方向: {row['research_type']} | 🌟 心情: {row['mood']}/10")
                    st.write(row['progress'])
                    if pd.notna(row['code_or_params']) and row['code_or_params'].strip() != "":
                        with st.expander("查看详情"):
                            st.code(row['code_or_params'])
                    st.markdown("---")

# ==========================================
# 页面路由控制
# ==========================================
if st.session_state.user is None:
    login_page()
else:
    main_page()