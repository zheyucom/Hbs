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

if 'user' not in st.session_state:
    st.session_state.user = None

# ==========================================
# 模块 1：纯净版登录页面
# ==========================================
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 欢迎来到专属科研空间</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>内部专属通道，请凭通行证登录</p>", unsafe_allow_html=True)
    st.write("") 
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("通行证账号", placeholder="输入您的专属账号")
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
# 模块 2：主界面（日志 + 数据看板）
# ==========================================
def main_page():
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

    # --- 获取全部数据 ---
    response = supabase.table("research_logs").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

    # 将页面分为两大板块：日常打卡 和 数据统计
    tab_logs, tab_stats = st.tabs(["📝 空间日志", "📊 数据看板"])

    with tab_logs:
        # --- 侧边栏检索 ---
        st.sidebar.header("⚙️ 检索与筛选中心")
        search_keyword = st.sidebar.text_input("🔍 关键词搜索", placeholder="输入代码、进展关键字...")
        today = datetime.today()
        start_default = today - timedelta(days=30)
        date_range = st.sidebar.date_input("📅 选择日期范围", value=(start_default, today))
        
        filter_author, filter_type = [], []
        if not df.empty:
            filter_author = st.sidebar.multiselect("👤 记录人筛选", options=df["author"].unique(), default=df["author"].unique())
            filter_type = st.sidebar.multiselect("🏷️ 方向筛选", options=df["research_type"].unique(), default=df["research_type"].unique())

        filtered_df = df.copy()
        if not df.empty:
            if filter_author:
                filtered_df = filtered_df[filtered_df["author"].isin(filter_author)]
            if filter_type:
                filtered_df = filtered_df[filtered_df["research_type"].isin(filter_type)]
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                filtered_df = filtered_df[(filtered_df["date"] >= date_range[0].strftime("%Y-%m-%d")) & 
                                          (filtered_df["date"] <= date_range[1].strftime("%Y-%m-%d"))]
            if search_keyword:
                filtered_df = filtered_df[
                    filtered_df["progress"].str.contains(search_keyword, case=False, na=False) |
                    filtered_df["code_or_params"].str.contains(search_keyword, case=False, na=False)
                ]

        ITEMS_PER_PAGE = 5
        total_logs = len(filtered_df)
        total_pages = max(1, (total_logs + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        
        st.sidebar.markdown("---")
        current_page = st.sidebar.number_input("📄 当前页码", min_value=1, max_value=total_pages, value=1, step=1)
        st.sidebar.caption(f"共 {total_logs} 条记录，分为 {total_pages} 页")

        col1, col2 = st.columns([1, 1.8])

        # --- 左侧：新建日志 (加入贴纸和文件上传) ---
        with col1:
            st.header("📝 写新日志")
            with st.form("new_log_form", clear_on_submit=True):
                date = st.date_input("日期", datetime.today())
                author = st.session_state.user.email 
                
                research_type = st.selectbox(
                    "研究方向", 
                    ["临床预测模型", "基础实验 (如 蛋白/RNA提取)", "文献阅读与综述", "其他"]
                )
                
                # 可爱贴纸选择
                sticker = st.radio("今日状态标签", ["✨ 稳步推进", "🤯 疯狂踩坑", "🎉 跑通/出结果啦", "☕ 摸鱼休整"], horizontal=True)
                
                progress = st.text_area("今日进展", height=100)
                code_or_params = st.text_area("代码 / 实验参数 / 外部链接", height=100)
                
                # 文件上传组件
                uploaded_file = st.file_uploader("上传图片或附件 (可选，请勿上传超大文件)", type=['png', 'jpg', 'jpeg', 'pdf', 'csv'])
                
                mood = st.slider("科研心情指数", 1, 10, 7)
                submitted = st.form_submit_button("提交日志", use_container_width=True)
                
                if submitted and progress.strip():
                    file_url = ""
                    # 处理文件上传逻辑
                    if uploaded_file is not None:
                        file_ext = uploaded_file.name.split('.')[-1]
                        # 用时间戳生成唯一文件名防止覆盖
                        file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{author.split('@')[0]}.{file_ext}"
                        try:
                            supabase.storage.from_("research_files").upload(file_name, uploaded_file.getvalue())
                            # 获取公开访问链接
                            file_url = supabase.storage.from_("research_files").get_public_url(file_name)
                        except Exception as e:
                            st.warning(f"文件上传失败，但日志会继续保存。报错: {e}")

                    new_data = {
                        "date": date.strftime("%Y-%m-%d"),
                        "author": author,
                        "research_type": research_type,
                        "progress": progress,
                        "code_or_params": code_or_params,
                        "mood": mood,
                        "sticker": sticker,
                        "file_url": file_url
                    }
                    supabase.table("research_logs").insert(new_data).execute()
                    st.success("🎉 提交成功！")
                    st.rerun()

        # --- 右侧：历史日志墙 ---
        with col2:
            st.header("🕰️ 历史日志墙")
            if filtered_df.empty:
                st.info("没有找到符合条件的日志。")
            else:
                start_idx = (current_page - 1) * ITEMS_PER_PAGE
                page_df = filtered_df.iloc[start_idx:start_idx + ITEMS_PER_PAGE]
                
                for index, row in page_df.iterrows():
                    with st.container():
                        display_name = row['author'].split('@')[0]
                        
                        # 处理旧数据中没有贴纸的情况
                        display_sticker = row.get('sticker', '✨ 稳步推进') if pd.notna(row.get('sticker')) else '✨ 稳步推进'
                        
                        st.markdown(f"### {display_sticker} | {row['date']}")
                        st.caption(f"👤 {display_name} | 🏷️ {row['research_type']} | 🌟 心情: {row['mood']}/10")
                        
                        st.write(row['progress'])
                        
                        if pd.notna(row['code_or_params']) and row['code_or_params'].strip() != "":
                            with st.expander("💾 查看代码 / 细节 / 链接"):
                                st.code(row['code_or_params'])
                                
                        # 如果有文件链接，展示图片或提供下载按钮
                        file_url_val = row.get('file_url', '')
                        if pd.notna(file_url_val) and file_url_val != "":
                            if any(ext in file_url_val.lower() for ext in ['.png', '.jpg', '.jpeg']):
                                st.image(file_url_val, use_container_width=True)
                            else:
                                st.markdown(f"[📎 点击下载附件/查看文档]({file_url_val})")
                                
                        st.markdown("---")

    # --- 数据看板板块 ---
    with tab_stats:
        st.header("📈 科研数据看板")
        if not df.empty:
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            
            # 基础指标统计
            stat_col1.metric("总打卡天数", f"{df['date'].nunique()} 天")
            stat_col2.metric("总日志数", f"{len(df)} 篇")
            stat_col3.metric("平均心情指数", f"{df['mood'].mean():.1f} / 10")
            
            st.divider()
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("各大类研究日志占比")
                type_counts = df['research_type'].value_counts()
                st.bar_chart(type_counts)
                
            with col_chart2:
                st.subheader("两人日志产出对比")
                author_counts = df['author'].apply(lambda x: x.split('@')[0]).value_counts()
                st.bar_chart(author_counts)
        else:
            st.info("数据还不够多，快去多写几篇日志激活看板吧！")

if st.session_state.user is None:
    login_page()
else:
    main_page()
    