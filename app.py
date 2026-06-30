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
# ==========================================
# 模块 1：登录与注册页面 (升级版)
# ==========================================
def login_page():
    # 居中显示标题
    st.markdown("<h1 style='text-align: center;'>🔐 欢迎来到专属科研空间</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>请先登录或注册您的账号</p>", unsafe_allow_html=True)
    st.write("") # 占位空行
    
    # 居中布局设置 (利用列来实现)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔑 登录", "✨ 注册"])
        
        # --- 登录模块 ---
        with tab1:
            with st.form("login_form"):
                email = st.text_input("邮箱", placeholder="输入您的邮箱")
                password = st.text_input("密码", type="password", placeholder="输入您的密码")
                submit_login = st.form_submit_button("立即登录", use_container_width=True)
                
                if submit_login:
                    if not email or not password:
                        st.warning("邮箱和密码都要填哦！")
                    else:
                        try:
                            # 尝试登录
                            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = response.user
                            st.rerun() # 登录成功直接刷新页面进入主空间
                        except Exception as e:
                            err_msg = str(e)
                            # 捕捉具体的错误类型给出友好提示
                            if "Email not confirmed" in err_msg:
                                st.error("⚠️ 登录失败：邮箱未确认。\n请检查 Supabase 后台 Authentication -> Providers -> Email 中的 'Confirm email' 是否真的处于关闭状态并保存了！")
                            elif "Invalid login credentials" in err_msg:
                                st.error("❌ 登录失败：邮箱或密码不正确，请重新核对一下哦。")
                            else:
                                st.error(f"登录遇到未知问题：{err_msg}")

        # --- 注册模块 ---
        with tab2:
            with st.form("register_form"):
                new_email = st.text_input("邮箱", placeholder="输入常用邮箱")
                new_password = st.text_input("密码", type="password", placeholder="至少需要6位字符哦")
                submit_reg = st.form_submit_button("注册并进入空间", use_container_width=True)
                
                if submit_reg:
                    if not new_email or len(new_password) < 6:
                        st.warning("请填写邮箱，且密码至少需要6位哦！")
                    else:
                        try:
                            # 尝试注册
                            response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                            
                            # 核心破解法：判断是否触发了 Supabase 的“防枚举保护”(已有账号但假装注册成功)
                            if response.user and getattr(response.user, 'identities', None) is not None and len(response.user.identities) == 0:
                                st.warning("👀 哎呀，这个邮箱已经注册过啦！请直接点击左侧的「登录」标签页登录哦。")
                            else:
                                st.success("🎉 注册成功！正在为您自动跳转...")
                                st.session_state.user = response.user
                                st.rerun() # 注册成功直接带状态进入主空间
                                
                        except Exception as e:
                            err_msg = str(e)
                            if "already registered" in err_msg or "already exists" in err_msg:
                                st.warning("👀 哎呀，这个邮箱已经注册过啦！请直接点击左侧的「登录」标签页登录哦。")
                            else:
                                st.error(f"注册遇到问题：{err_msg}")

                                
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