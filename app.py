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

# 读取CSV数据并自动检测列名
@st.cache_data
def load_csv_data():
    try:
        # 读取辨证方剂数据
        syndrome_df = pd.read_csv("肺部辩证与经典方 2.csv")
        
        # 读取药材共现矩阵
        cooccurrence_df = pd.read_csv("药材共现矩阵.csv")
        
        # 显示列名信息用于调试
        st.sidebar.info(f"辨证数据列: {list(syndrome_df.columns)}")
        st.sidebar.info(f"药材矩阵列: {list(cooccurrence_df.columns)}")
        
        return syndrome_df, cooccurrence_df
        
    except FileNotFoundError as e:
        st.error(f"文件未找到: {e}")
        st.info("""
        **请确保以下CSV文件存在于当前目录：**
        - 肺部辩证与经典方 2.csv
        - 药材共现矩阵.csv
        
        **当前目录文件：**
        """ + "\n".join([f"- {f}" for f in os.listdir('.') if f.endswith('.csv')]))
        return None, None
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None, None

# 自动检测列名函数
def detect_column_names(df, possible_names):
    """
    自动检测数据框中的列名
    """
    for name in possible_names:
        if name in df.columns:
            return name
    # 如果没有找到，返回第一个列名
    return df.columns[0] if len(df.columns) > 0 else None

# 加载数据
syndrome_df, cooccurrence_df = load_csv_data()

if syndrome_df is None or cooccurrence_df is None:
    st.stop()

# 自动检测列名
organ_col = detect_column_names(syndrome_df, ['器官', 'Organ', 'organ', '脏器'])
symptom_col = detect_column_names(syndrome_df, ['主症', '症状', 'Symptom', 'symptom', '证型'])
exterior_interior_col = detect_column_names(syndrome_df, ['表里', '表里辨证', 'Exterior_Interior'])
cold_heat_col = detect_column_names(syndrome_df, ['寒热', '寒热辨证', 'Cold_Heat'])
deficiency_excess_col = detect_column_names(syndrome_df, ['虚实', '虚实辨证', 'Deficiency_Excess'])
pathogenesis_col = detect_column_names(syndrome_df, ['病机', 'Pathogenesis', '病机分析'])
treatment_principle_col = detect_column_names(syndrome_df, ['治疗原则', '治疗原则', 'Treatment_Principle'])

# 显示检测到的列名
st.sidebar.success(f"检测到器官列: {organ_col}")
st.sidebar.success(f"检测到主症列: {symptom_col}")

# 数据预处理 - 构建共现字典
try:
    cooccurrence_dict = {}
    herb_col = detect_column_names(cooccurrence_df, ['药材', 'Herb', 'herb', '中药', '药物'])
    
    for _, row in cooccurrence_df.iterrows():
        herb = row[herb_col]
        cooccurrence_dict[herb] = {}
        for other_herb in cooccurrence_df.columns:
            if other_herb != herb_col and other_herb in row:
                cooccurrence_dict[herb][other_herb] = row[other_herb]
    
    st.success("✅ 数据加载成功！")
    
except Exception as e:
    st.error(f"数据预处理失败: {e}")
    st.stop()

# 侧边栏 - 查询条件
st.sidebar.header("🔍 查询条件")

# 器官选择
try:
    organs = syndrome_df[organ_col].unique()
    selected_organ = st.sidebar.selectbox("选择器官", organs)
except KeyError as e:
    st.error(f"找不到器官列 '{organ_col}'，可用列: {list(syndrome_df.columns)}")
    st.stop()

# 根据器官筛选主症
organ_syndromes = syndrome_df[syndrome_df[organ_col] == selected_organ]
main_symptoms = organ_syndromes[symptom_col].unique()

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
        selected_symptom = st.sidebar.selectbox("匹配到的主症", matched_syndromes)
    else:
        selected_symptom = st.sidebar.selectbox("选择主症", main_symptoms)
else:
    selected_symptom = st.sidebar.selectbox("选择主症", main_symptoms)

# 查询按钮
if st.sidebar.button("🔎 查询方剂", type="primary"):
    # 获取匹配的方剂信息
    matched_prescriptions = organ_syndromes[organ_syndromes[symptom_col] == selected_symptom]
    
    if not matched_prescriptions.empty:
        st.header(f"📋 查询结果：{selected_organ} - {selected_symptom}")
        
        # 显示八纲辨证信息
        syndrome_info = matched_prescriptions.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if exterior_interior_col in syndrome_info:
                st.metric("表里", syndrome_info[exterior_interior_col])
            else:
                st.metric("表里", "未知")
        
        with col2:
            if cold_heat_col in syndrome_info:
                st.metric("寒热", syndrome_info[cold_heat_col])
            else:
                st.metric("寒热", "未知")
        
        with col3:
            if deficiency_excess_col in syndrome_info:
                st.metric("虚实", syndrome_info[deficiency_excess_col])
            else:
                st.metric("虚实", "未知")
        
        with col4:
            if pathogenesis_col in syndrome_info:
                st.metric("病机", syndrome_info[pathogenesis_col])
            else:
                st.metric("病机", "未知")
        
        if treatment_principle_col in syndrome_info:
            st.markdown(f"**治疗原则：** {syndrome_info[treatment_principle_col]}")
        
        # 显示方剂和药材
        st.subheader("💊 推荐方剂及药材")
        
        # 自动检测药材列
        herb_columns = []
        source_columns = []
        
        for col in syndrome_df.columns:
            if '药材' in col or 'Herb' in col or 'herb' in col:
                herb_columns.append(col)
            elif '来源' in col or 'Source' in col or '方剂' in col:
                source_columns.append(col)
        
        # 如果没有自动检测到，使用默认的列名模式
        if not herb_columns:
            herb_columns = [f'药材{i}' for i in range(1, 5)]
        if not source_columns:
            source_columns = [f'来源{i}' for i in range(1, 5)]
        
        # 遍历所有检测到的药材列
        prescription_count = 0
        for i, (herb_col, source_col) in enumerate(zip(herb_columns, source_columns)):
            if herb_col in syndrome_info and pd.notna(syndrome_info[herb_col]):
                prescription_count += 1
                
                source_name = syndrome_info[source_col] if source_col in syndrome_info and pd.notna(syndrome_info.get(source_col)) else f"方剂 {prescription_count}"
                
                with st.expander(f"方剂 {prescription_count}: {source_name}", expanded=True):
                    herbs_text = str(syndrome_info[herb_col])
                    
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
            st.info(f"可用的药材列: {herb_columns}")
    
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
                st.write("辨证数据列名:", list(syndrome_df.columns))
                st.dataframe(syndrome_df.head(3))
            with tab2:
                st.write("药材矩阵列名:", list(cooccurrence_df.columns))
                st.dataframe(cooccurrence_df.head(3))
    
    with col2:
        st.subheader("🎯 使用说明")
        st.markdown("""
        ### 查询步骤：
        1. **选择器官**（如：肺、脾）
        2. **输入症状关键词**或选择主症
        3. **点击查询**查看推荐方剂
        4. **查看药材共现权重**分析
        
        ### 检测到的列名：
        - **器官列**: `{organ_col}`
        - **主症列**: `{symptom_col}`
        - **表里列**: `{exterior_interior_col}`
        - **寒热列**: `{cold_heat_col}`
        - **虚实列**: `{deficiency_excess_col}`
        
        💡 **共现权重说明**：基于药材在历史方剂中同时出现的频率计算，权重越高表示药材组合越常见。
        """.format(
            organ_col=organ_col,
            symptom_col=symptom_col,
            exterior_interior_col=exterior_interior_col,
            cold_heat_col=cold_heat_col,
            deficiency_excess_col=deficiency_excess_col
        ))

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <i>基于中医经典方剂与药材共现矩阵的智能推荐系统 | 自动列名检测版本</i>
</div>
""", unsafe_allow_html=True)
