import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta

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
# 模块 1：纯净版登录页面 (VIP 通行证模式)
# ==========================================
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 欢迎来到专属科研空间</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>内部专属通道，请凭通行证登录</p>", unsafe_allow_html=True)
    st.write("") 
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("通行证账号 (邮箱)", placeholder="输入您的专属账号")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            submit_login = st.form_submit_button("立即登录", use_container_width=True)
            
            if submit_login:
                if not email or not password:
                    st.warning("账号和密码都要填哦！")
                else:
                    try:
                        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = response.user
                        st.rerun()
                    except Exception as e:
                        st.error("❌ 登录失败：账号或密码不正确，请核对。")

# ==========================================
# 模块 2：主界面（包含高级检索与翻页）
# ==========================================
def main_page():
    # 顶部导航栏
    col_nav1, col_nav2 = st.columns([8, 1])
    with col_nav1:
        st.title("🔬 我们的科研小空间")
    with col_nav2:
        if st.button("退出登录"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()
            
    st.markdown(f"**当前在线：** `{st.session_state.user.email}`")
    st.divider()

    # --- 从数据库读取全部数据 ---
    response = supabase.table("research_logs").select("*").order("id", desc=True).execute()
    raw_data = response.data
    df = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()

    # ==========================================
    # 核心升级：侧边栏检索与控制中心
    # ==========================================
    st.sidebar.header("⚙️ 检索与筛选中心")
    
    search_keyword = st.sidebar.text_input("🔍 关键词搜索", placeholder="输入代码、进展关键字...")
    
    # 日期范围筛选（默认显示最近30天）
    today = datetime.today()
    start_default = today - timedelta(days=30)
    date_range = st.sidebar.date_input("📅 选择日期范围", value=(start_default, today))
    
    filter_author = []
    filter_type = []
    
    if not df.empty:
        filter_author = st.sidebar.multiselect("👤 按记录人筛选", options=df["author"].unique(), default=df["author"].unique())
        filter_type = st.sidebar.multiselect("🏷️ 按研究方向筛选", options=df["research_type"].unique(), default=df["research_type"].unique())

    # --- 执行前端联动筛选逻辑 ---
    filtered_df = df.copy()
    if not df.empty:
        # 1. 记录人筛选
        if filter_author:
            filtered_df = filtered_df[filtered_df["author"].isin(filter_author)]
        # 2. 研究方向筛选
        if filter_type:
            filtered_df = filtered_df[filtered_df["research_type"].isin(filter_type)]
        # 3. 日期范围筛选
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_str = date_range[0].strftime("%Y-%m-%d")
            end_str = date_range[1].strftime("%Y-%m-%d")
            filtered_df = filtered_df[(filtered_df["date"] >= start_str) & (filtered_df["date"] <= end_str)]
        # 4. 关键词搜索（同时模糊匹配今日进展和代码参数）
        if search_keyword:
            filtered_df = filtered_df[
                filtered_df["progress"].str.contains(search_keyword, case=False, na=False) |
                filtered_df["code_or_params"].str.contains(search_keyword, case=False, na=False)
            ]

    # ==========================================
    # 核心升级：翻页器参数计算
    # ==========================================
    ITEMS_PER_PAGE = 5  # 每页显示的日志数量
    total_logs = len(filtered_df)
    total_pages = max(1, (total_logs + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    
    st.sidebar.markdown("---")
    current_page = st.sidebar.number_input("📄 当前页码", min_value=1, max_value=total_pages, value=1, step=1)
    st.sidebar.caption(f"共筛选出 {total_logs} 条记录，分为 {total_pages} 页")

    # --- 页面左右分栏布局 ---
    col1, col2 = st.columns([1, 2])

    # --- 左侧：新建日志表单 ---
    with col1:
        st.header("📝 写新日志")
        with st.form("new_log_form"):
            date = st.date_input("日期", datetime.today())
            author = st.session_state.user.email 
            
            research_type = st.radio(
                "研究方向", 
                ["临床预测模型 (如 AHF 早期休克预测)", "基础实验 (如 蛋白/RNA 提取)", "文献阅读与综述撰写", "其他"]
            )
            progress = st.text_area("今日进展", height=150, placeholder="今天清洗了哪些特征？调通了什么模型？完成了什么实验？")
            code_or_params = st.text_area("代码 snippet / 实验参数", height=120, placeholder="在此处粘贴关键的 Python/R/SQL 代码或实验条件")
            mood = st.slider("今日科研心情指数", 1, 10, 7)
            
            submitted = st.form_submit_button("提交日志", use_container_width=True)
            
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
                st.success("🎉 提交成功！")
                st.rerun()

    # --- 右侧：智能历史日志墙 ---
    with col2:
        st.header("🕰️ 历史日志墙")
        
        if filtered_df.empty:
            st.info("🔍 没有找到符合当前筛选条件的日志，换个关键词试试吧？")
        else:
            # 根据当前页码切片提取数据
            start_idx = (current_page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_df = filtered_df.iloc[start_idx:end_idx]
            
            # 渲染当前页的日志
            for index, row in page_df.iterrows():
                with st.container():
                    # 提取邮箱前缀作为昵称展示
                    display_name = row['author'].split('@')[0]
                    st.markdown(f"### {row['date']} | 👤 {display_name}")
                    st.caption(f"🏷️ 方向: {row['research_type']} | 🌟 心情: {row['mood']}/10")
                    st.write(row['progress'])
                    
                    if pd.notna(row['code_or_params']) and row['code_or_params'].strip() != "":
                        with st.expander("💾 查看代码 / 参数详情"):
                            st.code(row['code_or_params'])
                    st.markdown("---")

# ==========================================
# 页面路由控制
# ==========================================
if st.session_state.user is None:
    login_page()
else:
    main_page()