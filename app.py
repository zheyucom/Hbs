import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import re
import html # 引入 html 库解决 object 报错

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

# --- 初始化搜索与分页的状态管理 ---
if 'match_idx' not in st.session_state: st.session_state.match_idx = 0
if 'last_search' not in st.session_state: st.session_state.last_search = ""
if 'page_selector' not in st.session_state: st.session_state.page_selector = 1
ITEMS_PER_PAGE = 5

# --- 核心高光渲染函数 (已修复 HTML 逃逸 BUG) ---
def highlight_text(text, keyword):
    if not isinstance(text, str) or not text:
        return ""
    # 1. 逃逸所有的危险字符（把 < 和 > 变成安全文本，防止变成 [object]）
    escaped_text = html.escape(text)
    if keyword and keyword.strip():
        escaped_keyword = html.escape(keyword)
        pattern = re.compile(f"({re.escape(escaped_keyword)})", re.IGNORECASE)
        # 2. 插入高光标签，保留代码里的空格和换行
        replacement = r"<mark style='background-color: #FFE600; color: #000; border-radius: 3px; padding: 0 3px; font-weight: bold;'>\1</mark>"
        return pattern.sub(replacement, escaped_text)
    return escaped_text

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
# 模块 2：主界面
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

    # --- 侧边栏：全局搜索 ---
    st.sidebar.header("⚙️ 检索中心")
    search_keyword = st.sidebar.text_input("🔍 全局精准搜索", placeholder="输入关键字定位代码或进展...")

    # 如果更换了搜索词，重置搜索进度和页码
    if search_keyword != st.session_state.last_search:
        st.session_state.last_search = search_keyword
        st.session_state.match_idx = 0
        st.session_state.page_selector = 1

    # --- 动态过滤逻辑 ---
    filtered_df = df.copy()
    if not df.empty and search_keyword:
        filtered_df = filtered_df[
            filtered_df["progress"].str.contains(search_keyword, case=False, na=False) |
            filtered_df["code_or_params"].str.contains(search_keyword, case=False, na=False)
        ]

    # --- 侧边栏：智能导航系统 ---
    total_logs = len(filtered_df)
    total_pages = max(1, (total_logs + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    if search_keyword and total_logs > 0:
        st.sidebar.markdown("### 🎯 搜索结果导航")
        nav_col1, nav_col2, nav_col3 = st.sidebar.columns([1, 1.2, 1])
        
        # 导航按钮回调逻辑
        def go_prev():
            if st.session_state.match_idx > 0:
                st.session_state.match_idx -= 1
                st.session_state.page_selector = (st.session_state.match_idx // ITEMS_PER_PAGE) + 1
        
        def go_next(total):
            if st.session_state.match_idx < total - 1:
                st.session_state.match_idx += 1
                st.session_state.page_selector = (st.session_state.match_idx // ITEMS_PER_PAGE) + 1

        nav_col1.button("⬆️ 上一个", on_click=go_prev)
        nav_col3.button("⬇️ 下一个", on_click=go_next, args=(total_logs,))
        nav_col2.markdown(f"<div style='text-align:center; padding-top:8px;'><b>{st.session_state.match_idx + 1} / {total_logs}</b></div>", unsafe_allow_html=True)
        st.sidebar.markdown("---")

    # 分页控制
    st.sidebar.number_input("📄 当前页码", min_value=1, max_value=total_pages, step=1, key="page_selector")

    col1, col2 = st.columns([1, 1.8])

    # --- 左侧：新建日志 (含贴纸) ---
    with col1:
        st.header("📝 写新日志")
        with st.form("new_log_form", clear_on_submit=True):
            date = st.date_input("日期", datetime.today())
            author = st.session_state.user.email 
            research_type = st.selectbox("研究方向", ["临床预测模型", "基础实验 (如 蛋白/RNA提取)", "文献阅读与综述", "其他"])
            
            st.markdown("**选择今日心情贴纸：**")
            mood_sticker = st.radio("心情", ["🥰 元气满满", "💡 灵感迸发", "🤯 疯狂踩坑", "😭 跑不出来", "☕ 佛系摸鱼", "🥱 疲惫不堪"], horizontal=True, label_visibility="collapsed")
            
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
                    "mood_sticker": mood_sticker 
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
            # 提取当前页的数据
            start_idx = (st.session_state.page_selector - 1) * ITEMS_PER_PAGE
            page_df = filtered_df.iloc[start_idx:start_idx + ITEMS_PER_PAGE]
            
            for i in range(len(page_df)):
                row = page_df.iloc[i]
                global_idx = start_idx + i  # 在所有筛选结果中的绝对索引
                
                # 判断当前这条日志是不是“导航仪”正在聚焦的目标
                is_target = (search_keyword != "") and (global_idx == st.session_state.match_idx)
                
                with st.container():
                    # 如果是被定位的目标，插入锚点和视觉提示
                    if is_target:
                        st.markdown("<div id='active-target'></div>", unsafe_allow_html=True)
                        st.success(f"🎯 **当前定位目标** (匹配结果 {global_idx + 1}/{total_logs})")
                        # 注入极简 JS 代码，实现平滑滚动至当前元素
                        components.html(
                            "<script>window.parent.document.getElementById('active-target').scrollIntoView({behavior: 'smooth', block: 'center'});</script>",
                            height=0
                        )

                    display_name = row['author'].split('@')[0]
                    sticker_display = row.get('mood_sticker', '📝 记录') if pd.notna(row.get('mood_sticker')) else '📝 记录'
                    
                    st.markdown(f"### {sticker_display} | {row['date']}")
                    st.caption(f"👤 {display_name} | 🏷️ {row['research_type']} | 🔋 能量: {row['mood']}/10")
                    
                    # 渲染带有高光的今日进展
                    highlighted_progress = highlight_text(row['progress'], search_keyword)
                    st.markdown(highlighted_progress, unsafe_allow_html=True)
                    
                    # 渲染带有高光的代码与参数区
                    if pd.notna(row['code_or_params']) and row['code_or_params'].strip() != "":
                        # 如果是定位目标，折叠面板自动展开 (expanded=is_target)
                        with st.expander("💾 查看代码 / 细节", expanded=is_target):
                            if search_keyword and search_keyword.lower() in row['code_or_params'].lower():
                                highlighted_code = highlight_text(row['code_or_params'], search_keyword)
                                st.markdown(f"<pre style='background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; white-space: pre-wrap; font-family: monospace;'><code>{highlighted_code}</code></pre>", unsafe_allow_html=True)
                            else:
                                st.code(row['code_or_params'])
                    st.markdown("---")

if st.session_state.user is None:
    login_page()
else:
    main_page()