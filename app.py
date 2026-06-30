import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import re

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

# --- 核心高光渲染函数 ---
def highlight_text(text, keyword):
    """如果存在关键字，则使用 HTML 的 mark 标签进行黄色高光标注"""
    if not isinstance(text, str) or not text:
        return ""
    if keyword and keyword.strip():
        # 忽略大小写的正则替换，加入好看的黄色背景圆角样式
        pattern = re.compile(f"({re.escape(keyword)})", re.IGNORECASE)
        replacement = r"<mark style='background-color: #FFE600; color: #000000; border-radius: 3px; padding: 2px 4px; font-weight: bold;'>\1</mark>"
        return pattern.sub(replacement, text)
    return text

# ==========================================
# 模块 1：登录页面 (保持不变)
# ==========================================
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 欢迎来到专属科研空间</h1>", unsafe_allow_html=True)
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
# 模块 2：主界面 (加入高光搜索与贴纸)
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
            
    st.divider()

    # --- 获取全部数据 ---
    response = supabase.table("research_logs").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

    # --- 侧边栏全局检索 ---
    st.sidebar.header("⚙️ 检索中心")
    search_keyword = st.sidebar.text_input("🔍 全局精准搜索", placeholder="输入任意字词，自动高光定位...")
    
    # --- 动态过滤逻辑 ---
    filtered_df = df.copy()
    if not df.empty and search_keyword:
        # 只要“今日进展”或“代码参数”中包含该词，就保留该行
        filtered_df = filtered_df[
            filtered_df["progress"].str.contains(search_keyword, case=False, na=False) |
            filtered_df["code_or_params"].str.contains(search_keyword, case=False, na=False)
        ]

    col1, col2 = st.columns([1, 1.8])

    # --- 左侧：新建日志 ---
    with col1:
        st.header("📝 写新日志")
        with st.form("new_log_form", clear_on_submit=True):
            date = st.date_input("日期", datetime.today())
            author = st.session_state.user.email 
            
            research_type = st.selectbox(
                "研究方向", 
                ["临床预测模型", "基础实验 (如 蛋白/RNA提取)", "文献阅读与综述", "其他"]
            )
            
            # 🌟 新增：萌系心情贴纸选择
            st.markdown("**选择今日心情贴纸：**")
            mood_sticker = st.radio(
                "心情贴纸",
                ["🥰 元气满满", "💡 灵感迸发", "🤯 疯狂踩坑", "😭 跑不出来", "☕ 佛系摸鱼", "🥱 疲惫不堪"],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            mood = st.slider("能量指数 (1-10)", 1, 10, 7)
            progress = st.text_area("今日进展", height=100)
            code_or_params = st.text_area("代码 / 实验参数", height=100)
            
            submitted = st.form_submit_button("提交日志", use_container_width=True)
            
            if submitted and progress.strip():
                new_data = {
                    "date": date.strftime("%Y-%m-%d"),
                    "author": author,
                    "research_type": research_type,
                    "progress": progress,
                    "code_or_params": code_or_params,
                    "mood": mood,
                    "mood_sticker": mood_sticker # 保存贴纸数据
                }
                supabase.table("research_logs").insert(new_data).execute()
                st.success("🎉 提交成功！")
                st.rerun()

    # --- 右侧：高光历史日志墙 ---
    with col2:
        st.header("🕰️ 历史日志墙")
        
        if filtered_df.empty:
            if search_keyword:
                st.warning(f"没有找到包含「{search_keyword}」的日志哦。")
            else:
                st.info("还没有任何记录，快写下第一篇吧！")
        else:
            for index, row in filtered_df.iterrows():
                with st.container():
                    display_name = row['author'].split('@')[0]
                    # 获取贴纸，兼容没有贴纸的旧数据
                    sticker_display = row.get('mood_sticker', '📝 记录') if pd.notna(row.get('mood_sticker')) else '📝 记录'
                    
                    st.markdown(f"### {sticker_display} | {row['date']}")
                    st.caption(f"👤 {display_name} | 🏷️ {row['research_type']} | 🔋 能量: {row['mood']}/10")
                    
                    # 渲染带有高光的今日进展
                    highlighted_progress = highlight_text(row['progress'], search_keyword)
                    st.markdown(highlighted_progress, unsafe_allow_html=True)
                    
                    # 渲染带有高光的代码与参数区
                    if pd.notna(row['code_or_params']) and row['code_or_params'].strip() != "":
                        with st.expander("💾 查看代码 / 细节"):
                            # 如果包含搜索词，为了让高光生效，以 HTML 的 pre 格式渲染；否则正常用 st.code 渲染
                            if search_keyword and search_keyword.lower() in row['code_or_params'].lower():
                                highlighted_code = highlight_text(row['code_or_params'], search_keyword)
                                st.markdown(f"<pre style='background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem;'><code>{highlighted_code}</code></pre>", unsafe_allow_html=True)
                            else:
                                st.code(row['code_or_params'])
                                
                    st.markdown("---")

if st.session_state.user is None:
    login_page()
else:
    main_page()
    