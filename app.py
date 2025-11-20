import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 配置区域 (请修改这里)
# ==========================================
# 1. 填入你的 Google Sheet ID (从链接里复制的那一长串)
SHEET_ID = '1ED2BAyqD5nyS6M-i6z7o2GoNA6cacsgh0Eua8gIwq4g'  # <--- 把你的ID填在这里
# 2. 填入工作表名称 (通常是 Sheet1)
SHEET_NAME = 'crcl_rating' 

# ==========================================
# 核心逻辑
# ==========================================
st.set_page_config(page_title="CRCL 投研看板", layout="wide")
st.title("📊 Circle Internet Group (CRCL) 动态投研时间轴")

# 构建 CSV 下载链接
csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

@st.cache_data(ttl=60) # 缓存60秒，意味着老板刷新页面最多延迟1分钟看到新数据
def load_data():
    try:
        # 读取数据
        df = pd.read_csv(csv_url)
        
        # 清洗列名（防止Excel里多打了空格）
        df.columns = df.columns.str.strip()
        
        # 转换数据格式
        df['Date'] = pd.to_datetime(df['Date'])
        df['Target'] = pd.to_numeric(df['Target'], errors='coerce')
        df['Actual_Price'] = pd.to_numeric(df['Actual_Price'], errors='coerce')
        
        # 计算逻辑
        df['Upside'] = (df['Target'] - df['Actual_Price']) / df['Actual_Price']
        df['Upside_Text'] = df['Upside'].apply(lambda x: f"+{x:.1%}" if x > 0 else f"{x:.1%}")
        
        return df
    except Exception as e:
        return None

df = load_data()

if df is None:
    st.error("无法读取数据。请检查：1. Google Sheet ID 是否正确。 2. 分享权限是否设为 '知道链接者可见'。")
    st.stop()

# 侧边栏筛选
st.sidebar.header("🔍 筛选选项")
issuers = list(df['Issuer'].unique()) if 'Issuer' in df.columns else []
selected_issuers = st.sidebar.multiselect("选择投行:", issuers, default=issuers)
show_notes = st.sidebar.checkbox("在图表上显示备注", value=True)

# 数据过滤
if not selected_issuers:
    st.warning("请至少选择一家投行。")
    st.stop()

filtered_df = df[df['Issuer'].isin(selected_issuers)].sort_values('Date')

# 绘图
fig = go.Figure()

# 颜色池
colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b']
color_map = {issuer: colors[i % len(colors)] for i, issuer in enumerate(issuers)}

for issuer in filtered_df['Issuer'].unique():
    subset = filtered_df[filtered_df['Issuer'] == issuer]
    c = color_map.get(issuer, 'black')
    
    fig.add_trace(go.Scatter(
        x=subset['Date'], y=subset['Target'],
        mode='lines+markers', name=issuer,
        marker=dict(size=10, symbol='diamond', color=c),
        line=dict(width=2, color=c),
        text=subset.apply(lambda row: (
            f"<b>{row['Issuer']}</b><br>"
            f"评级: {row['Rating']}<br>"
            f"目标价: ${row['Target']}<br>"
            f"实际价: ${row['Actual_Price']}<br>"
            f"空间: {row['Upside_Text']}<br>"
            f"<i>{row['Note']}</i>"
        ), axis=1),
        hovertemplate="%{text}<extra></extra>"
    ))
    
    # 标注
    if show_notes:
        for _, row in subset.iterrows():
            note_text = str(row['Note'])
            short_note = note_text[:8] + ".." if len(note_text) > 8 else note_text
            fig.add_annotation(
                x=row['Date'], y=row['Target'],
                text=short_note,
                showarrow=True, arrowhead=1, yshift=10,
                font=dict(size=9, color=c)
            )

# 实际股价参考线
fig.add_trace(go.Scatter(
    x=filtered_df['Date'], y=filtered_df['Actual_Price'],
    mode='lines', name='实际股价',
    line=dict(color='gray', dash='dot', width=1), opacity=0.5
))

fig.update_layout(
    title="投行目标价 vs 实际股价趋势",
    yaxis_title="价格 ($)", 
    hovermode="x unified",
    height=600,
    legend=dict(orientation="h", y=1.02, x=1, xanchor="right")
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("查看原始数据表格"):
    st.dataframe(filtered_df.style.format({'Target': '{:.2f}', 'Actual_Price': '{:.2f}', 'Upside': '{:.2%}'}))
