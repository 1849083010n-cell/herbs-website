import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import json
import os

# 页面配置
st.set_page_config(
    page_title="中医方剂药材共现查询系统",
    page_icon="🌿",
    layout="wide"
)

# 标题
st.title("🌿 中医方剂药材共现权重查询系统")
st.markdown("基于CSV格式数据的智能方剂推荐")

# 读取CSV数据
@st.cache_data
def load_csv_data():
    try:
        # 读取辨证方剂数据
        syndrome_df = pd.read_csv("肺部辩证与经典方 2.csv")
        
        # 读取药材共现矩阵
        cooccurrence_df = pd.read_csv("药材共现矩阵.csv")
        
        # 处理列名 - 检查并重命名第一列
        if cooccurrence_df.columns[0] == 'Unnamed: 0':
            cooccurrence_df = cooccurrence_df.rename(columns={'Unnamed: 0': '药材'})
        elif '药材' not in cooccurrence_df.columns:
            # 如果第一列不是'药材'，但包含药材名，重命名它
            cooccurrence_df = cooccurrence_df.rename(columns={cooccurrence_df.columns[0]: '药材'})
        
        return syndrome_df, cooccurrence_df
        
    except FileNotFoundError as e:
        st.error(f"文件未找到: {e}")
        st.info("""
        **请确保以下CSV文件存在于当前目录：**
        - 肺部辩证与经典方 2.csv
        - 药材共现矩阵.csv
        """)
        return None, None
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None, None

# 加载数据
syndrome_df, cooccurrence_df = load_csv_data()

if syndrome_df is None or cooccurrence_df is None:
    st.stop()

# 数据预处理 - 构建共现字典
try:
    cooccurrence_dict = {}
    for _, row in cooccurrence_df.iterrows():
        herb = row['药材']
        cooccurrence_dict[herb] = {}
        for other_herb in cooccurrence_df.columns[1:]:  # 跳过'药材'列
            if other_herb in row:
                cooccurrence_dict[herb][other_herb] = row[other_herb]
    
    st.success("✅ 数据加载成功！")
    
except Exception as e:
    st.error(f"数据预处理失败: {e}")
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
        if pd.notna(syndrome) and any(keyword in str(syndrome) for keyword in symptom_input.split()):
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
                    herbs_text = str(syndrome_info[prescription_col])
                    
                    # 解析药材（处理顿号、逗号分隔）
                    herbs = []
                    if '、' in herbs_text:
                        herbs = [herb.strip() for herb in herbs_text.split('、') if herb.strip()]
                    elif ',' in herbs_text:
                        herbs = [herb.strip() for herb in herbs_text.split(',') if herb.strip()]
                    else:
                        herbs = [herbs_text.strip()]
                    
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
                                '出现频次': herbs.count(herb)
                            })
                        else:
                            # 如果药材不在共现矩阵中，显示基本信息
                            herb_weights.append({
                                '药材': herb,
                                '平均共现': 0,
                                '总共现': 0,
                                '出现频次': herbs.count(herb),
                                '备注': '未在共现矩阵中找到'
                            })
                    
                    # 按总共现排序
                    herb_weights.sort(key=lambda x: x['总共现'], reverse=True)
                    
                    # 显示药材表格
                    if herb_weights:
                        weights_df = pd.DataFrame(herb_weights)
                        
                        # 配置列显示
                        column_config = {
                            "药材": "药材名称",
                            "平均共现": st.column_config.NumberColumn(
                                "平均共现权重",
                                help="该药材与方剂中其他药材的平均共现次数",
                                format="%.2f"
                            ),
                            "总共现": st.column_config.NumberColumn(
                                "总共现次数",
                                help="该药材与方剂中其他药材的总共现次数"
                            ),
                            "出现频次": st.column_config.NumberColumn(
                                "出现频次",
                                help="该药材在方剂中出现的次数"
                            )
                        }
                        
                        # 如果有备注列，添加到配置中
                        if '备注' in weights_df.columns:
                            column_config["备注"] = "备注信息"
                        
                        st.dataframe(weights_df, column_config=column_config, hide_index=True)
                        
                        # 可视化展示 - 只显示有共现数据的药材
                        valid_herbs = [h for h in herb_weights if h['总共现'] > 0]
                        if valid_herbs:
                            st.subheader("📊 药材共现权重可视化")
                            
                            # 选择可视化类型
                            viz_type = st.selectbox("选择图表类型", ["柱状图", "折线图"], key=f"viz_{i}")
                            
                            if viz_type == "柱状图":
                                chart_df = pd.DataFrame({
                                    '药材': [h['药材'] for h in valid_herbs],
                                    '总共现次数': [h['总共现'] for h in valid_herbs]
                                })
                                st.bar_chart(chart_df.set_index('药材'))
                            elif viz_type == "折线图":
                                chart_df = pd.DataFrame({
                                    '药材': [h['药材'] for h in valid_herbs],
                                    '平均共现权重': [h['平均共现'] for h in valid_herbs]
                                })
                                st.line_chart(chart_df.set_index('药材'))
                        else:
                            st.info("该方剂中的药材在共现矩阵中暂无数据")
                        
                    else:
                        st.info("暂无药材权重数据")
        
        if prescription_count == 0:
            st.warning("未找到对应的方剂信息")
    
    else:
        st.error("未找到匹配的证型信息")

else:
    # 初始状态显示说明和数据概览
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 数据概览")
        st.metric("药材数量", len(cooccurrence_df))
        st.metric("证型数量", len(syndrome_df))
        st.metric("器官类型", len(organs))
        
        # 显示数据预览
        with st.expander("数据预览"):
            tab1, tab2 = st.tabs(["辨证数据", "药材矩阵"])
            with tab1:
                st.dataframe(syndrome_df.head(3))
            with tab2:
                st.dataframe(cooccurrence_df.head(3))
    
    with col2:
        st.subheader("🎯 使用说明")
        st.markdown("""
        ### 查询步骤：
        1. **选择器官**（如：肺、脾）
        2. **输入症状关键词**或选择主症
        3. **点击查询**查看推荐方剂
        4. **查看药材共现权重**分析
        
        ### 功能特色：
        - 📊 **智能权重计算**：基于药材共现频率
        - 🔍 **症状匹配**：关键词自动匹配主症
        - 📈 **数据可视化**：多种图表展示权重
        - 💊 **多方案推荐**：显示多个经典方剂
        
        💡 **共现权重说明**：基于药材在历史方剂中同时出现的频率计算，权重越高表示药材组合越常见。
        """)
    
    # 显示特色功能
    st.subheader("✨ 系统特色")
    features = st.columns(3)
    with features[0]:
        st.markdown("**🔬 数据驱动**")
        st.markdown("基于真实药材共现矩阵，科学计算权重")
    with features[1]:
        st.markdown("**🌐 全面覆盖**")
        st.markdown("涵盖肺、脾等多个器官的辨证论治")
    with features[2]:
        st.markdown("**💡 智能推荐**")
        st.markdown("根据症状自动匹配最相关方剂")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <i>基于中医经典方剂与药材共现矩阵的智能推荐系统 | CSV格式数据版本</i>
</div>
""", unsafe_allow_html=True)
