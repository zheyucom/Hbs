import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import re
import html
import uuid
import urllib.parse # 仅保留用于修复手机端中文链接的轻量工具

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

if 'match_idx' not in st.session_state: st.session_state.match_idx = 0
if 'last_search' not in st.session_state: st.session_state.last_search = ""
if 'page_selector' not in st.session_state: st.session_state.page_selector = 1
ITEMS_PER_PAGE = 5

def highlight_text(text, keyword):
    if not isinstance(text, str) or not text:
        return ""
    escaped_text = html.escape(text)
    if keyword and keyword.strip():
        escaped_keyword = html.escape(keyword)
        pattern = re.compile(f"({re.escape(escaped_keyword)})", re.IGNORECASE)
        replacement = r"<mark style='background-color: #FFE600; color: #000; border-radius: 3px; padding: 0 3px; font-weight: bold;'>\1</mark>"
        return pattern.sub(replacement, escaped_text)
    return escaped_text

# ==========================================
# 模块 1：纯净版登录页面
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

    response = supabase.table("research_logs").select("*").order("date", desc=True).order("id", desc=True).execute()
    df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

    if not df.empty:
        df['short_author'] = df['author'].apply(lambda x: x.split('@')[0])
        df['date_obj'] = pd.to_datetime(df['date'])

    tab_logs, tab_stats, tab_review, tab_weekly = st.tabs([
        "📝 空间日志", 
        "📊 平行宇宙大屏", 
        "📑 综述生成器", 
        "📅 组会周报神器"
    ])

    # ------------------------------------------
    # 板块一：空间日志
    # ------------------------------------------
    with tab_logs:
        st.sidebar.header("⚙️ 检索与控制中心")
        search_keyword = st.sidebar.text_input("🔍 全局精准搜索", placeholder="输入关键字定位代码或进展...")

        if search_keyword != st.session_state.last_search:
            st.session_state.last_search = search_keyword
            st.session_state.match_idx = 0
            st.session_state.page_selector = 1

        filtered_df = df.copy()
        if not df.empty and search_keyword:
            filtered_df = filtered_df[
                filtered_df["progress"].str.contains(search_keyword, case=False, na=False) |
                filtered_df["code_or_params"].str.contains(search_keyword, case=False, na=False)
            ]

        total_logs = len(filtered_df)
        total_pages = max(1, (total_logs + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        if search_keyword and total_logs > 0:
            st.sidebar.markdown("### 🎯 搜索结果导航")
            total_hits = 0
            for _, row in filtered_df.iterrows():
                text_to_search = (str(row['progress']) if pd.notna(row['progress']) else "") + " " + (str(row['code_or_params']) if pd.notna(row['code_or_params']) else "")
                total_hits += len(re.findall(re.escape(search_keyword), text_to_search, re.IGNORECASE))
            
            st.sidebar.caption(f"💡 在 **{total_logs} 篇**日志中，共找到 **{total_hits} 个**匹配项")
            nav_col1, nav_col2, nav_col3 = st.sidebar.columns([1, 1.4, 1])
            
            def go_prev():
                if st.session_state.match_idx > 0:
                    st.session_state.match_idx -= 1
                    st.session_state.page_selector = (st.session_state.match_idx // ITEMS_PER_PAGE) + 1
            
            def go_next(total):
                if st.session_state.match_idx < total - 1:
                    st.session_state.match_idx += 1
                    st.session_state.page_selector = (st.session_state.match_idx // ITEMS_PER_PAGE) + 1

            nav_col1.button("⬆️ 上一篇", on_click=go_prev)
            nav_col3.button("⬇️ 下一篇", on_click=go_next, args=(total_logs,))
            nav_col2.markdown(f"<div style='text-align:center; padding-top:8px; font-size:14px;'><b>第 {st.session_state.match_idx + 1} 篇 / 共 {total_logs} 篇</b></div>", unsafe_allow_html=True)
            st.sidebar.markdown("---")

        st.sidebar.number_input("📄 当前页码", min_value=1, max_value=total_pages, step=1, key="page_selector")
        
        st.sidebar.markdown("---")
        if not filtered_df.empty:
            csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
            st.sidebar.download_button(
                label="📥 导出当前筛选日志 (CSV/Excel)",
                data=csv_data,
                file_name=f"research_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        col1, col2 = st.columns([1, 1.8])

        with col1:
            st.header("📝 写新日志")
            with st.form("new_log_form", clear_on_submit=True):
                date = st.date_input("日期", datetime.today())
                author = st.session_state.user.email 
                research_type = st.selectbox("研究方向", ["文献阅读与综述", "临床预测模型", "基础实验 (如 蛋白/RNA提取)", "其他"])
                
                st.markdown("**选择今日心情贴纸：**")
                mood_sticker = st.radio("心情", ["🥰 元气满满", "💡 灵感迸发", "🤯 疯狂踩坑", "😭 跑不出来", "☕ 佛系摸鱼", "🥱 疲惫不堪"], horizontal=True, label_visibility="collapsed")
                mood = st.slider("能量指数 (1-10)", 1, 10, 7)
                
                progress = st.text_area("今日进展", height=100)
                code_or_params = st.text_area("代码 / 实验参数 / 外部链接", height=100)
                
                uploaded_file = st.file_uploader("📎 上传文献 PDF 或 实验图片 (大小限10MB)", type=['pdf', 'png', 'jpg', 'jpeg'])
                
                submitted = st.form_submit_button("提交日志", use_container_width=True)
                
                if submitted and progress.strip():
                    file_url_to_save = ""
                    if uploaded_file is not None:
                        file_ext = uploaded_file.name.split('.')[-1]
                        unique_filename = f"{uuid.uuid4().hex}.{file_ext}" 
                        
                        try:
                            supabase.storage.from_("research_files").upload(
                                path=unique_filename,
                                file=uploaded_file.getvalue(),
                                file_options={"content-type": uploaded_file.type}
                            )
                            file_url_to_save = supabase.storage.from_("research_files").get_public_url(unique_filename)
                        except Exception as e:
                            st.warning(f"⚠️ 文件上传遇到小问题（日志文字已保存）：{e}")

                    new_data = {
                        "date": date.strftime("%Y-%m-%d"),
                        "author": author,
                        "research_type": research_type,
                        "progress": progress,
                        "code_or_params": code_or_params,
                        "mood": mood,
                        "mood_sticker": mood_sticker,
                        "file_url": file_url_to_save 
                    }
                    supabase.table("research_logs").insert(new_data).execute()
                    st.success("🎉 提交成功！")
                    st.rerun()

        with col2:
            st.header("🕰️ 历史日志墙")
            if filtered_df.empty:
                if search_keyword:
                    st.warning(f"没有找到包含「{search_keyword}」的日志哦。")
                else:
                    st.info("还没有任何记录，快写下第一篇吧！")
            else:
                start_idx = (st.session_state.page_selector - 1) * ITEMS_PER_PAGE
                page_df = filtered_df.iloc[start_idx:start_idx + ITEMS_PER_PAGE]
                
                for i in range(len(page_df)):
                    row = page_df.iloc[i]
                    global_idx = start_idx + i  
                    is_target = (search_keyword != "") and (global_idx == st.session_state.match_idx)
                    
                    with st.container():
                        if is_target:
                            st.markdown("<div id='active-target'></div>", unsafe_allow_html=True)
                            st.success(f"🎯 **当前定位目标** (第 {global_idx + 1} 篇 / 共 {total_logs} 篇)")
                            components.html(
                                "<script>window.parent.document.getElementById('active-target').scrollIntoView({behavior: 'smooth', block: 'center'});</script>",
                                height=0
                            )

                        display_name = row.get('short_author', row['author'].split('@')[0])
                        sticker_display = row.get('mood_sticker', '📝 记录') if pd.notna(row.get('mood_sticker')) else '📝 记录'
                        
                        st.markdown(f"### {sticker_display} | {row['date']}")
                        st.caption(f"👤 {display_name} | 🏷️ {row['research_type']} | 🔋 能量: {row['mood']}/10")
                        
                        highlighted_progress = highlight_text(row['progress'], search_keyword)
                        st.markdown(highlighted_progress, unsafe_allow_html=True)
                        
                        if pd.notna(row['code_or_params']) and row['code_or_params'].strip() != "":
                            with st.expander("💾 查看细节", expanded=is_target):
                                if search_keyword and search_keyword.lower() in row['code_or_params'].lower():
                                    highlighted_code = highlight_text(row['code_or_params'], search_keyword)
                                    st.markdown(f"<pre style='background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; white-space: pre-wrap; font-family: monospace;'><code>{highlighted_code}</code></pre>", unsafe_allow_html=True)
                                else:
                                    st.code(row['code_or_params'])
                        
                        # 💡 纯享云端版渲染逻辑：只做 URL 安全转码，抛弃所有臃肿请求
                        file_link = row.get('file_url', '')
                        if pd.notna(file_link) and file_link != "":
                            # 保证手机浏览器能看懂带中文的文件链接
                            safe_file_link = urllib.parse.quote(file_link, safe=":/%?=&")
                            
                            if any(ext in file_link.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                                st.markdown(f"""
                                    <div style="margin-top:10px; margin-bottom:5px;">
                                        <a href="{safe_file_link}" target="_blank" title="点击查看高清大图">
                                            <img src="{safe_file_link}" loading="lazy" style="width: 250px; max-width:100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); cursor: zoom-in; transition: transform 0.2s;">
                                        </a>
                                    </div>
                                    <span style="color: gray; font-size: 13px;">👆 点击图片查看高清大图</span>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"**[📎 点击这里下载 / 查看附件文献PDF]({safe_file_link})**")
                                
                        st.markdown("---")

    # ------------------------------------------
    # 板块二：平行宇宙大屏
    # ------------------------------------------
    with tab_stats:
        st.header("🌌 双人科研平行宇宙大屏")
        st.markdown("以时间为轴，看看你们俩的科研节奏和能量起伏！")
        
        if not df.empty:
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            stat_col1.metric("总并肩作战", f"{df['date'].nunique()} 天")
            stat_col2.metric("总科研结晶", f"{len(df)} 篇")
            stat_col3.metric("团队平均能量", f"{df['mood'].mean():.1f} / 10")
            st.divider()
            
            st.subheader("📈 每日科研产出走势 (打卡次数)")
            activity_df = df.groupby(['date', 'short_author']).size().unstack(fill_value=0)
            st.line_chart(activity_df)
            
            st.divider()
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("🔋 能量指数(心情) 波动曲线")
                mood_df = df.groupby(['date', 'short_author'])['mood'].mean().unstack(fill_value=None)
                st.area_chart(mood_df)
                
            with col_chart2:
                st.subheader("🏷️ 团队研究方向总览")
                st.bar_chart(df['research_type'].value_counts())
        else:
            st.info("数据还不够多，快去多写几篇日志激活看板吧！")

    # ------------------------------------------
    # 板块三：综述溯源生成器 
    # ------------------------------------------
    with tab_review:
        st.header("📑 文献阅读与综述一键排版")
        if df.empty:
            st.info("目前还没有任何日志哦。")
        else:
            review_df = df[df['research_type'].str.contains("文献阅读与综述", na=False)]
            if review_df.empty:
                st.warning("暂无记录。平时看文献别忘了打卡上传哦！")
            else:
                st.success(f"🔍 成功提取了 **{len(review_df)}** 篇相关的阅读笔记！")
                review_df = review_df.sort_values(by="date_obj", ascending=True)
                
                md_content = f"# 文献阅读梳理笔记\n\n> **生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n> **总计：** {len(review_df)} 篇\n\n---\n\n"
                for _, row in review_df.iterrows():
                    md_content += f"## 📅 {row['date']} | 记录人：{row.get('short_author')}\n\n**【核心总结】**\n{row['progress']}\n\n"
                    if pd.notna(row['code_or_params']) and str(row['code_or_params']).strip():
                        md_content += f"**【详细摘录】**\n> {row['code_or_params']}\n\n"
                        
                    if pd.notna(row.get('file_url', '')) and row['file_url'] != "":
                        safe_url = urllib.parse.quote(row['file_url'], safe=":/%?=&")
                        md_content += f"**[📎 原文链接]({safe_url})**\n\n"
                    md_content += "---\n\n"

                st.download_button(
                    label="📥 下载综述草稿 (.md)",
                    data=md_content.encode('utf-8-sig'),
                    file_name=f"文献综述草稿_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                st.text_area(label="草稿预览", value=md_content, height=300, label_visibility="collapsed")

    # ------------------------------------------
    # 板块四：组会周报一键生成神器 
    # ------------------------------------------
    with tab_weekly:
        st.header("📅 组会周报自动生成器")
        st.markdown("系统将自动提取指定时间段内的日志，按人员自动归类总结，助你一键搞定组会汇报 PPT 内容。")
        
        today = datetime.today()
        default_start = today - timedelta(days=7)
        week_range = st.date_input("选择周报周期", value=(default_start, today), key="weekly_date")
        
        if not df.empty and isinstance(week_range, (list, tuple)) and len(week_range) == 2:
            start_str = week_range[0].strftime("%Y-%m-%d")
            end_str = week_range[1].strftime("%Y-%m-%d")
            
            weekly_df = df[(df["date"] >= start_str) & (df["date"] <= end_str)]
            
            if weekly_df.empty:
                st.warning(f"在 {start_str} 到 {end_str} 期间没有打卡记录，难道这周都在摸鱼？😉")
            else:
                st.success(f"✅ 提取成功！本周共计 **{len(weekly_df)}** 条工作记录。")
                
                report_md = f"# 组会工作汇报 ({start_str} 至 {end_str})\n\n"
                
                authors = weekly_df['short_author'].unique()
                for author in authors:
                    report_md += f"## 👨‍🔬 汇报人：{author}\n\n"
                    author_df = weekly_df[weekly_df['short_author'] == author].sort_values(by="date_obj", ascending=True)
                    
                    types = author_df['research_type'].unique()
                    for r_type in types:
                        report_md += f"### 📌 专项：{r_type}\n"
                        type_df = author_df[author_df['research_type'] == r_type]
                        
                        for _, row in type_df.iterrows():
                            is_trouble = "踩坑" in str(row.get('mood_sticker', '')) or "跑不出来" in str(row.get('mood_sticker', ''))
                            prefix = "⚠️ [遇到问题] " if is_trouble else "✅ [推进] "
                            report_md += f"- **{row['date']}**: {prefix}{row['progress']}\n"
                            
                        report_md += "\n"
                    report_md += "---\n\n"
                
                st.download_button(
                    label="📥 下载 Markdown 周报格式",
                    data=report_md.encode('utf-8-sig'),
                    file_name=f"组会周报_{start_str}_to_{end_str}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="dl_weekly"
                )
                
                st.text_area(label="周报预览区", value=report_md, height=400, label_visibility="collapsed")

if st.session_state.user is None:
    login_page()
else:
    main_page()