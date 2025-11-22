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
    
    # 数据预处理
    cooccurrence_dict = {}
    for _, row in cooccurrence_df.iterrows():
        herb = row['药材']
        cooccurrence_dict[herb] = {}
        for other_herb in cooccurrence_df.columns[1:]:
            cooccurrence_dict[herb][other_herb] = row[other_herb]
    
except Exception as e:
    st.error(f"数据加载失败: {e}")
    st.stop()

# 侧边栏 - 查询条件
st.sidebar.header("🔍 查询条件")

# 器官选择
organs = syndrome_df['器官'].unique()
selected_organ = st.sidebar.selectbox("选择器官", organs)

# 根据器官筛选主症
organ_syndromes = syndrome_df[syndrome_df['器官'] == selected_organ]
main_symptoms = organ_syndromes['主症'].unique()

# 症状输入
symptom_input = st.sidebar.text_input("输入症状关键词", placeholder="例如：咳嗽、黄痰、发热")

# 主症选择（可根据症状自动匹配）
if symptom_input:
    # 简单关键词匹配
    matched_syndromes = []
    for syndrome in main_symptoms:
        if any(keyword in syndrome for keyword in symptom_input.split()):
            matched_syndromes.append(syndrome)
    
    if matched_syndromes:
        selected_syndrome = st.sidebar.selectbox("匹配到的主症", matched_syndromes)
    else:
        selected_syndrome = st.sidebar.selectbox("选择主症", main_symptoms)
else:
    selected_syndrome = st.sidebar.selectbox("选择主症", main_symptoms)

# 查询按钮
if st.sidebar.button("🔎 查询方剂", type="primary"):
    # 获取匹配的方剂信息
    matched_prescriptions = organ_syndromes[organ_syndromes['主症'] == selected_syndrome]
    
    if not matched_prescriptions.empty:
        st.header(f"📋 查询结果：{selected_organ} - {selected_syndrome}")
        
        # 显示八纲辨证信息
        syndrome_info = matched_prescriptions.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("表里", syndrome_info['表里'])
        with col2:
            st.metric("寒热", syndrome_info['寒热'])
        with col3:
            st.metric("虚实", syndrome_info['虚实'])
        with col4:
            st.metric("病机", syndrome_info['病机'])
        
        st.markdown(f"**治疗原则：** {syndrome_info['治疗原则']}")
        
        # 显示方剂和药材
        st.subheader("💊 推荐方剂及药材")
        
        # 遍历所有方剂列
        prescription_count = 0
        for i in range(1, 5):  # 假设最多4个方剂
            prescription_col = f'药材{i}'
            source_col = f'来源{i}'
            
            if prescription_col in syndrome_info and pd.notna(syndrome_info[prescription_col]):
                prescription_count += 1
                
                with st.expander(f"方剂 {prescription_count}: {syndrome_info[source_col] if pd.notna(syndrome_info.get(source_col)) else '经典方剂'}", expanded=True):
                    herbs_text = syndrome_info[prescription_col]
                    
                    # 解析药材（简单的逗号分隔）
                    herbs = [herb.strip() for herb in herbs_text.split('、') if herb.strip()]
                    
                    # 计算每个药材的共现权重
                    herb_weights = []
                    for herb in herbs:
                        if herb in cooccurrence_dict:
                            # 计算该药材与其他药材的平均共现次数
                            other_herbs = [h for h in herbs if h != herb]
                            if other_herbs:
                                cooccur_values = [cooccurrence_dict[herb].get(other, 0) for other in other_herbs]
                                avg_cooccur = np.mean(cooccur_values) if cooccur_values else 0
                                total_cooccur = sum(cooccur_values)
                            else:
                                avg_cooccur = 0
                                total_cooccur = 0
                            
                            herb_weights.append({
                                '药材': herb,
                                '平均共现': round(avg_cooccur, 2),
                                '总共现': total_cooccur,
                                '出现频次': len([h for h in herbs if h == herb])
                            })
                    
                    # 按总共现排序
                    herb_weights.sort(key=lambda x: x['总共现'], reverse=True)
                    
                    # 显示药材表格
                    if herb_weights:
                        weights_df = pd.DataFrame(herb_weights)
                        st.dataframe(
                            weights_df,
                            column_config={
                                "药材": "药材名称",
                                "平均共现": st.column_config.NumberColumn(
                                    "平均共现权重",
                                    help="该药材与方剂中其他药材的平均共现次数"
                                ),
                                "总共现": st.column_config.NumberColumn(
                                    "总共现次数",
                                    help="该药材与方剂中其他药材的总共现次数"
                                )
                            },
                            hide_index=True
                        )
                        
                        # 可视化展示
                        st.subheader("📊 药材共现权重可视化")
                        
                        # 选择可视化类型
                        viz_type = st.selectbox("选择图表类型", ["柱状图", "雷达图"], key=f"viz_{i}")
                        
                        if viz_type == "柱状图":
                            chart_df = pd.DataFrame({
                                '药材': [h['药材'] for h in herb_weights],
                                '总共现次数': [h['总共现'] for h in herb_weights]
                            })
                            st.bar_chart(chart_df.set_index('药材'))
                        
                    else:
                        st.info("暂无共现权重数据")
        
        if prescription_count == 0:
            st.warning("未找到对应的方剂信息")
    
    else:
        st.error("未找到匹配的证型信息")

else:
    # 初始状态显示说明
    st.info("👈 请在左侧边栏选择查询条件，然后点击查询按钮")
    
    # 显示数据概览
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 数据概览")
        st.metric("药材数量", len(cooccurrence_df))
        st.metric("证型数量", len(syndrome_df))
    
    with col2:
        st.subheader("🎯 使用说明")
        st.markdown("""
        1. **选择器官**（如：肺、脾）
        2. **输入症状关键词**或选择主症
        3. **点击查询**查看推荐方剂
        4. **查看药材共现权重**分析
        
        💡 共现权重基于药材在历史方剂中同时出现的频率计算
        """)

# 页脚
st.markdown("---")
st.markdown("*基于中医经典方剂与药材共现矩阵的智能推荐系统*")
