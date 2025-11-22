import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import itertools

# 页面配置
st.set_page_config(
    page_title="中医方剂智能查询系统",
    page_icon="🌿",
    layout="wide"
)

# 标题
st.title("🌿 中医方剂智能查询系统")
st.markdown("基于器官-主症-病机-治疗原则-药材的完整辨证体系")

# 读取CSV数据
@st.cache_data
def load_syndrome_data():
    try:
        # 读取辨证方剂数据
        syndrome_df = pd.read_csv("肺部辩证与经典方 2.csv")
        return syndrome_df
    except FileNotFoundError:
        st.error("找不到文件：肺部辩证与经典方 2.csv")
        st.info("请确保CSV文件在当前目录中")
        return None
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None

# 加载数据
syndrome_df = load_syndrome_data()

if syndrome_df is None:
    st.stop()

# 显示数据列名用于调试
st.sidebar.info(f"数据列名: {list(syndrome_df.columns)}")

# 自动检测列名函数
def detect_columns(df):
    """自动检测各种列名"""
    columns_info = {}
    
    # 检测关键列名
    key_columns = {
        'organ': ['器官', 'Organ', 'organ', '脏器'],
        'symptom': ['主症', '症状', 'Symptom', 'symptom', '证型'],
        'pathogenesis': ['病机', 'Pathogenesis', '病机分析', '病因病机'],
        'treatment_principle': ['治疗原则', 'Treatment_Principle', '治法', '治疗法则']
    }
    
    for key, possible_names in key_columns.items():
        for name in possible_names:
            if name in df.columns:
                columns_info[key] = name
                break
        else:
            # 如果没有找到，尝试其他逻辑
            if key == 'organ':
                columns_info[key] = df.columns[0] if len(df.columns) > 0 else None
            elif key == 'symptom':
                columns_info[key] = df.columns[1] if len(df.columns) > 1 else None
    
    # 检测八纲辨证列（可选）
    optional_columns = {
        'exterior_interior': ['表里', '表里辨证', 'Exterior_Interior'],
        'cold_heat': ['寒热', '寒热辨证', 'Cold_Heat'],
        'deficiency_excess': ['虚实', '虚实辨证', 'Deficiency_Excess']
    }
    
    for key, possible_names in optional_columns.items():
        for name in possible_names:
            if name in df.columns:
                columns_info[key] = name
                break
    
    # 检测药材和来源列
    columns_info['herb_columns'] = []
    columns_info['source_columns'] = []
    
    # 检测药材列
    for i in range(1, 6):
        herb_found = False
        for pattern in [f'药材{i}', f'Herb{i}', f'herb{i}', f'方药{i}']:
            if pattern in df.columns:
                columns_info['herb_columns'].append(pattern)
                herb_found = True
                break
        if not herb_found:
            # 尝试模糊匹配
            for col in df.columns:
                if any(keyword in col for keyword in ['药材', 'Herb', 'herb', '方药']) and str(i) in col:
                    if col not in columns_info['herb_columns']:
                        columns_info['herb_columns'].append(col)
                        break
    
    # 检测来源列
    for i in range(1, 6):
        source_found = False
        for pattern in [f'来源{i}', f'Source{i}', f'source{i}', f'方剂来源{i}']:
            if pattern in df.columns:
                columns_info['source_columns'].append(pattern)
                source_found = True
                break
        if not source_found:
            # 尝试模糊匹配
            for col in df.columns:
                if any(keyword in col for keyword in ['来源', 'Source', 'source', '方剂']) and str(i) in col:
                    if col not in columns_info['source_columns']:
                        columns_info['source_columns'].append(col)
                        break
    
    # 如果自动检测失败，使用默认列名
    if not columns_info['herb_columns']:
        columns_info['herb_columns'] = [f'药材{i}' for i in range(1, 4)]
    if not columns_info['source_columns']:
        columns_info['source_columns'] = [f'来源{i}' for i in range(1, 4)]
    
    return columns_info

# 检测列名
columns_info = detect_columns(syndrome_df)

# 显示检测结果
st.sidebar.success(f"器官列: {columns_info.get('organ', '未找到')}")
st.sidebar.success(f"主症列: {columns_info.get('symptom', '未找到')}")
st.sidebar.success(f"病机列: {columns_info.get('pathogenesis', '未找到')}")
st.sidebar.success(f"治疗原则列: {columns_info.get('treatment_principle', '未找到')}")
st.sidebar.success(f"药材列: {columns_info['herb_columns']}")
st.sidebar.success(f"来源列: {columns_info['source_columns']}")

# 解析药材文本
def parse_herbs(herbs_text):
    """解析药材文本，支持多种分隔符"""
    if pd.isna(herbs_text):
        return []
    
    herbs_text = str(herbs_text).strip()
    if not herbs_text:
        return []
    
    # 尝试不同的分隔符
    if '、' in herbs_text:
        herbs = [herb.strip() for herb in herbs_text.split('、') if herb.strip()]
    elif ',' in herbs_text:
        herbs = [herb.strip() for herb in herbs_text.split(',') if herb.strip()]
    elif '，' in herbs_text:
        herbs = [herb.strip() for herb in herbs_text.split('，') if herb.strip()]
    elif ' ' in herbs_text:
        herbs = [herb.strip() for herb in herbs_text.split(' ') if herb.strip()]
    else:
        herbs = [herbs_text.strip()]
    
    return herbs

# 构建完整的查询数据结构
def build_complete_query_structure(df, columns_info):
    """构建器官-主症-病机-治疗原则-药材的完整结构"""
    query_structure = {}
    
    for _, row in df.iterrows():
        organ = row[columns_info['organ']] if 'organ' in columns_info else None
        symptom = row[columns_info['symptom']] if 'symptom' in columns_info else None
        
        if pd.isna(organ) or pd.isna(symptom):
            continue
        
        # 获取病机和治疗原则
        pathogenesis = row.get(columns_info.get('pathogenesis'), '')
        treatment_principle = row.get(columns_info.get('treatment_principle'), '')
        
        # 初始化器官
        if organ not in query_structure:
            query_structure[organ] = {}
        
        # 初始化主症（包含病机和治疗原则）
        symptom_key = f"{symptom}"
        if symptom_key not in query_structure[organ]:
            query_structure[organ][symptom_key] = {
                'pathogenesis': pathogenesis,
                'treatment_principle': treatment_principle,
                'exterior_interior': row.get(columns_info.get('exterior_interior'), ''),
                'cold_heat': row.get(columns_info.get('cold_heat'), ''),
                'deficiency_excess': row.get(columns_info.get('deficiency_excess'), ''),
                'prescriptions': []
            }
        
        # 添加方剂信息
        for i, (herb_col, source_col) in enumerate(zip(columns_info['herb_columns'], columns_info['source_columns'])):
            if herb_col in row and pd.notna(row[herb_col]):
                herbs = parse_herbs(row[herb_col])
                source = row[source_col] if source_col in row and pd.notna(row.get(source_col)) else f"经典方剂{i+1}"
                
                if herbs:  # 只有有药材时才添加
                    # 检查是否已存在相同来源的方剂
                    existing_prescription = None
                    for pres in query_structure[organ][symptom_key]['prescriptions']:
                        if pres['source'] == source:
                            existing_prescription = pres
                            break
                    
                    if existing_prescription:
                        # 合并药材（去重）
                        existing_herbs = set(existing_prescription['herbs'])
                        new_herbs = set(herbs)
                        combined_herbs = list(existing_herbs.union(new_herbs))
                        existing_prescription['herbs'] = combined_herbs
                    else:
                        query_structure[organ][symptom_key]['prescriptions'].append({
                            'source': source,
                            'herbs': herbs
                        })
    
    return query_structure

# 构建查询结构
query_structure = build_complete_query_structure(syndrome_df, columns_info)

st.success(f"✅ 数据加载成功！共 {len(query_structure)} 个器官")

# 侧边栏 - 查询条件
st.sidebar.header("🔍 查询条件")

# 器官选择
organs = list(query_structure.keys())
selected_organ = st.sidebar.selectbox("选择器官", organs)

# 主症选择
if selected_organ in query_structure:
    symptoms = list(query_structure[selected_organ].keys())
    selected_symptom = st.sidebar.selectbox("选择主症", symptoms)
else:
    selected_symptom = None

# 症状关键词搜索
symptom_search = st.sidebar.text_input("搜索症状关键词", placeholder="输入症状关键词进行过滤")

if symptom_search:
    filtered_symptoms = [symptom for symptom in symptoms if symptom_search in str(symptom)]
    if filtered_symptoms:
        selected_symptom = st.sidebar.selectbox("匹配到的主症", filtered_symptoms)
    else:
        st.sidebar.warning("未找到匹配的主症")

# 查询结果显示
if selected_organ and selected_symptom:
    symptom_info = query_structure[selected_organ][selected_symptom]
    
    st.header(f"📋 辨证论治详情：{selected_organ} - {selected_symptom}")
    
    # 显示核心辨证信息
    st.subheader("🎯 核心辨证信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 病机显示
        if symptom_info['pathogenesis']:
            st.markdown("**🧬 病机分析**")
            st.info(symptom_info['pathogenesis'])
        
        # 八纲辨证显示
        st.markdown("**📊 八纲辨证**")
        eight_principles = []
        if symptom_info['exterior_interior']:
            eight_principles.append(f"表里: {symptom_info['exterior_interior']}")
        if symptom_info['cold_heat']:
            eight_principles.append(f"寒热: {symptom_info['cold_heat']}")
        if symptom_info['deficiency_excess']:
            eight_principles.append(f"虚实: {symptom_info['deficiency_excess']}")
        
        if eight_principles:
            for principle in eight_principles:
                st.write(f"- {principle}")
        else:
            st.write("- 八纲信息待补充")
    
    with col2:
        # 治疗原则显示
        if symptom_info['treatment_principle']:
            st.markdown("**💡 治疗原则**")
            st.success(symptom_info['treatment_principle'])
        
        # 统计信息
        st.markdown("**📈 方剂统计**")
        prescription_count = len(symptom_info['prescriptions'])
        total_herbs = sum(len(pres['herbs']) for pres in symptom_info['prescriptions'])
        unique_herbs = len(set(herb for pres in symptom_info['prescriptions'] for herb in pres['herbs']))
        
        st.metric("方剂数量", prescription_count)
        st.metric("总药材数", total_herbs)
        st.metric("独特药材", unique_herbs)
    
    # 显示推荐方剂
    st.subheader("💊 推荐方剂")
    
    if symptom_info['prescriptions']:
        for i, prescription in enumerate(symptom_info['prescriptions']):
            with st.expander(f"📖 方剂 {i+1}: {prescription['source']}", expanded=True):
                # 方剂基本信息
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("**🌿 组成药材**")
                    herbs = prescription['herbs']
                    for j, herb in enumerate(herbs):
                        st.write(f"{j+1}. {herb}")
                
                with col2:
                    st.markdown("**📊 药材分析**")
                    st.metric("药材数量", len(herbs))
                    st.metric("君药", herbs[0] if herbs else "无")
                    
                    # 药材配伍特点
                    if len(herbs) >= 3:
                        st.markdown("**配伍特点**")
                        st.write(f"- 君药: {herbs[0]}")
                        st.write(f"- 臣药: {herbs[1]}")
                        if len(herbs) > 2:
                            st.write(f"- 佐使: {', '.join(herbs[2:])}")
                
                # 药材组合分析
                if len(herbs) > 1:
                    st.markdown("**🔄 核心药对**")
                    core_pairs = []
                    if len(herbs) >= 2:
                        core_pairs.append(f"{herbs[0]} + {herbs[1]}")
                    if len(herbs) >= 3:
                        core_pairs.append(f"{herbs[0]} + {herbs[2]}")
                    
                    for pair in core_pairs:
                        st.write(f"- {pair}")
    else:
        st.warning("该证型下暂无方剂信息")
        
    # 显示所有药材汇总
    st.subheader("📦 药材总览")
    all_herbs = set()
    for prescription in symptom_info['prescriptions']:
        all_herbs.update(prescription['herbs'])
    
    if all_herbs:
        herbs_list = list(all_herbs)
        cols = 4
        rows = (len(herbs_list) + cols - 1) // cols
        
        for i in range(rows):
            col_list = st.columns(cols)
            for j in range(cols):
                idx = i * cols + j
                if idx < len(herbs_list):
                    with col_list[j]:
                        st.info(herbs_list[idx])
    else:
        st.info("暂无药材信息")

else:
    # 初始页面 - 显示系统概览
    st.info("👈 请在左侧选择器官和主症开始查询")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🏥 系统概览")
        
        # 统计信息
        total_organs = len(query_structure)
        total_symptoms = sum(len(symptoms) for symptoms in query_structure.values())
        total_prescriptions = sum(len(symptom['prescriptions']) for organ in query_structure.values() for symptom in organ.values())
        
        # 计算总药材数
        all_herbs_set = set()
        for organ in query_structure.values():
            for symptom in organ.values():
                for prescription in symptom['prescriptions']:
                    all_herbs_set.update(prescription['herbs'])
        
        st.metric("辨证体系", f"{total_organs}器官 {total_symptoms}证型")
        st.metric("方剂库", f"{total_prescriptions}个经典方剂")
        st.metric("药材库", f"{len(all_herbs_set)}种药材")
        
        # 显示器官证型分布
        with st.expander("📋 器官证型分布"):
            for organ, symptoms in query_structure.items():
                symptom_count = len(symptoms)
                prescription_count = sum(len(symptom['prescriptions']) for symptom in symptoms.values())
                st.write(f"- **{organ}**: {symptom_count}个证型, {prescription_count}个方剂")
    
    with col2:
        st.subheader("🎯 系统特色")
        st.markdown("""
        ### 🌟 完整辨证体系
        **器官 → 主症 → 病机 → 治疗原则 → 药材**
        
        ### 📚 核心功能
        - **病机分析** - 深入理解疾病发生发展机制
        - **治疗原则** - 明确治疗方向和策略  
        - **方剂推荐** - 多个经典方剂对比参考
        - **药材分析** - 详细解析药材配伍关系
        
        ### 🔍 查询流程
        1. **选择器官** - 确定病变部位
        2. **选择主症** - 明确临床表现
        3. **分析病机** - 理解病理机制
        4. **确定治则** - 制定治疗策略
        5. **选用方药** - 选择具体方剂药材
        """)
    
    # 显示快速查询示例
    st.subheader("🚀 快速开始")
    example_cols = st.columns(3)
    
    # 获取前3个器官的示例
    example_count = 0
    for organ in list(query_structure.keys())[:3]:
        if example_count < 3:
            symptoms = list(query_structure[organ].keys())
            if symptoms:
                symptom = symptoms[0]
                with example_cols[example_count]:
                    st.markdown(f"**{organ} - {symptom}**")
                    symptom_info = query_structure[organ][symptom]
                    if symptom_info['pathogenesis']:
                        st.caption(symptom_info['pathogenesis'][:50] + "...")
                    if st.button("查看详情", key=f"example_{organ}"):
                        st.session_state.selected_organ = organ
                        st.session_state.selected_symptom = symptom
                        st.rerun()
                    example_count += 1

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <i>中医智能辨证论治系统 | 基于器官-主症-病机-治疗原则-药材的完整体系</i>
</div>
""", unsafe_allow_html=True)
