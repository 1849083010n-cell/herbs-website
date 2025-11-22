import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import json

# 页面配置
st.set_page_config(
    page_title="中医方剂药材共现查询系统",
    page_icon="🌿",
    layout="wide"
)

# 标题
st.title("🌿 中医方剂药材共现权重查询系统")
st.markdown("基于药材共现矩阵的智能方剂推荐")

# 读取数据 - 使用xlrd作为备选
@st.cache_data
def load_data():
    try:
        # 尝试使用openpyxl
        syndrome_df = pd.read_excel("肺部辩证与经典方 2.xlsx", engine='openpyxl')
        cooccurrence_df = pd.read_excel("药材共现矩阵.xlsx", engine='openpyxl')
    except ImportError:
        try:
            # 尝试使用xlrd
            syndrome_df = pd.read_excel("肺部辩证与经典方 2.xlsx", engine='xlrd')
            cooccurrence_df = pd.read_excel("药材共现矩阵.xlsx", engine='xlrd')
        except:
            # 最后尝试默认引擎
            syndrome_df = pd.read_excel("肺部辩证与经典方 2.xlsx")
            cooccurrence_df = pd.read_excel("药材共现矩阵.xlsx")
    
    cooccurrence_df = cooccurrence_df.rename(columns={'Unnamed: 0': '药材'})
    
    return syndrome_df, cooccurrence_df

# 显示安装提示
try:
    syndrome_df, cooccurrence_df = load_data()
except Exception as e:
    st.error(f"数据加载失败: {e}")
    st.info("""
    **请安装必要的依赖包：**
    ```bash
    pip install openpyxl pandas streamlit numpy
    ```
    
    或者使用：
    ```bash
    pip install xlrd
    ```
    """)
    st.stop()

# 其余代码保持不变...
