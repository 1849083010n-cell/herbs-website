import streamlit as st
import pandas as pd
import numpy as np
import subprocess
import sys
import os

# 检查并安装缺失的依赖
def install_package(package):
    try:
        __import__(package)
        return True
    except ImportError:
        st.warning(f"正在安装缺失的依赖: {package}")
        try:
            if sys.platform == "win32":
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            else:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            return True
        except:
            return False

# 安装必要包
required_packages = ['pandas', 'numpy', 'openpyxl']
for package in required_packages:
    if not install_package(package):
        st.error(f"无法安装 {package}，请手动安装")

# 页面配置
st.set_page_config(
    page_title="中医方剂查询系统",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 中医方剂药材查询系统")

# 检查依赖
try:
    import openpyxl
    import pandas as pd
    import numpy as np
    st.success("✅ 依赖检查通过！")
except ImportError as e:
    st.error(f"❌ 依赖缺失: {e}")
    st.stop()

# 读取数据
@st.cache_data
def load_data():
    try:
        # 读取辨证方剂数据
        syndrome_df = pd.read_excel("肺部辩证与经典方 2.xlsx")
        
        # 读取药材共现矩阵
        cooccurrence_df = pd.read_excel("药材共现矩阵.xlsx")
        cooccurrence_df = cooccurrence_df.rename(columns={'Unnamed: 0': '药材'})
        
        return syndrome_df, cooccurrence_df
    except Exception as e:
        st.error(f"数据读取失败: {e}")
        return None, None

# 主应用
def main():
    # 加载数据
    with st.spinner('正在加载数据...'):
        syndrome_df, cooccurrence_df = load_data()
    
    if syndrome_df is None:
        st.error("无法加载数据文件，请检查：")
        st.info("""
        1. 确保Excel文件在正确目录
        2. 确保文件没有被其他程序打开
        3. 尝试重新安装依赖：`pip install openpyxl`
        """)
        return
    
    st.success(f"✅ 成功加载 {len(syndrome_df)} 条辨证数据")
    st.success(f"✅ 成功加载 {len(cooccurrence_df)} 种药材数据")
    
    # 显示数据预览
    st.subheader("📊 数据预览")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**辨证方剂数据**")
        st.dataframe(syndrome_df.head(3))
    
    with col2:
        st.write("**药材数据**")
        st.dataframe(cooccurrence_df.head(3))
    
    # 简单查询功能
    st.subheader("🔍 简单查询")
    
    # 器官选择
    organs = syndrome_df['器官'].unique()
    selected_organ = st.selectbox("选择器官", organs)
    
    # 主症选择
    organ_data = syndrome_df[syndrome_df['器官'] == selected_organ]
    symptoms = organ_data['主症'].unique()
    selected_symptom = st.selectbox("选择主症", symptoms)
    
    if st.button("查询方剂"):
        result = organ_data[organ_data['主症'] == selected_symptom].iloc[0]
        
        st.subheader("💊 推荐方剂")
        
        # 显示方剂信息
        cols = st.columns(2)
        with cols[0]:
            st.write(f"**八纲辨证**: {result['表里']}-{result['寒热']}-{result['虚实']}")
            st.write(f"**治疗原则**: {result['治疗原则']}")
            st.write(f"**病机**: {result['病机']}")
        
        # 显示药材
        st.write("**推荐药材**:")
        for i in range(1, 5):
            herb_col = f'药材{i}'
            source_col = f'来源{i}'
            if herb_col in result and pd.notna(result[herb_col]):
                st.write(f"- **{result[source_col]}**: {result[herb_col]}")

if __name__ == "__main__":
    main()
