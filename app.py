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
st.markdown("基于器官-症状-八纲辨证的精准方剂推荐")

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
    
    # 检测八纲辨证列
    eight_principles = {
        'exterior_interior': ['表里', '表里辨证', 'Exterior_Interior'],
        'cold_heat': ['寒热', '寒热辨证', 'Cold_Heat'],
        'deficiency_excess': ['虚实', '虚实辨证', 'Deficiency_Excess']
    }
    
    for key, possible_names in eight_principles.items():
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

# 构建查询数据结构
def build_query_structure(df, columns_info):
    """构建完整的查询数据结构"""
    query_structure = {}
    
    for _, row in df.iterrows():
        organ = row[columns_info['organ']] if 'organ' in columns_info else None
        symptom = row[columns_info['symptom']] if 'symptom' in columns_info else None
        
        if pd.isna(organ) or pd.isna(symptom):
            continue
        
        # 获取八纲辨证信息
        exterior_interior = row.get(columns_info.get('exterior_interior'), '')
        cold_heat = row.get(columns_info.get('cold_heat'), '')
        deficiency_excess = row.get(columns_info.get('deficiency_excess'), '')
        
        # 获取病机和治疗原则
        pathogenesis = row.get(columns_info.get('pathogenesis'), '')
        treatment_principle = row.get(columns_info.get('treatment_principle'), '')
        
        # 初始化器官
        if organ not in query_structure:
            query_structure[organ] = {}
        
        # 初始化主症
        symptom_key = f"{symptom}"
        if symptom_key not in query_structure[organ]:
            query_structure[organ][symptom_key] = {
                'exterior_interior': exterior_interior,
                'cold_heat': cold_heat,
                'deficiency_excess': deficiency_excess,
                'pathogenesis': pathogenesis,
                'treatment_principle': treatment_principle,
                'prescriptions': []
            }
        
        # 添加方剂信息
        for i, (herb_col, source_col) in enumerate(zip(columns_info['herb_columns'], columns_info['source_columns'])):
            if herb_col in row and pd.notna(row[herb_col]):
                herbs = parse_herbs(row[herb_col])
                source = row[source_col] if source_col in row and pd.notna(row.get(source_col)) else f"经典方剂{i+1}"
                
                if herbs:
                    query_structure[organ][symptom_key]['prescriptions'].append({
                        'source': source,
                        'herbs': herbs
                    })
    
    return query_structure

# 构建查询结构
query_structure = build_query_structure(syndrome_df, columns_info)

# 获取所有可能的选项
all_organs = list(query_structure.keys())
all_symptoms = list(set(symptom for organ in query_structure.values() for symptom in organ.keys()))
all_exterior_interior = list(set(info['exterior_interior'] for organ in query_structure.values() for info in organ.values() if info['exterior_interior']))
all_cold_heat = list(set(info['cold_heat'] for organ in query_structure.values() for info in organ.values() if info['cold_heat']))
all_deficiency_excess = list(set(info['deficiency_excess'] for organ in query_structure.values() for info in organ.values() if info['deficiency_excess']))

# 右侧边栏 - 精准查询
with st.sidebar:
    st.header("🔍 精准查询")
    
    # 器官选择
    selected_organ = st.selectbox("选择器官", [""] + all_organs, key="sidebar_organ")
    
    # 症状选择（可根据器官过滤）
    if selected_organ:
        organ_symptoms = list(query_structure[selected_organ].keys())
        selected_symptom = st.selectbox("选择症状", [""] + organ_symptoms, key="sidebar_symptom")
    else:
        selected_symptom = st.selectbox("选择症状", [""] + all_symptoms, key="sidebar_symptom")
    
    # 八纲辨证选择
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_exterior_interior = st.selectbox("表里", [""] + all_exterior_interior, key="sidebar_exterior")
    with col2:
        selected_cold_heat = st.selectbox("寒热", [""] + all_cold_heat, key="sidebar_cold_heat")
    with col3:
        selected_deficiency_excess = st.selectbox("虚实", [""] + all_deficiency_excess, key="sidebar_deficiency")
    
    # 查询按钮
    search_button = st.button("🔎 开始查询", type="primary", use_container_width=True)
    
    # 清空按钮
    if st.button("🔄 清空条件", use_container_width=True):
        st.rerun()

# 主内容区域
if search_button:
    # 执行查询
    results = []
    
    for organ, symptoms in query_structure.items():
        # 器官筛选
        if selected_organ and organ != selected_organ:
            continue
            
        for symptom, info in symptoms.items():
            # 症状筛选
            if selected_symptom and symptom != selected_symptom:
                continue
            
            # 八纲辨证筛选
            if (selected_exterior_interior and 
                info['exterior_interior'] != selected_exterior_interior):
                continue
                
            if (selected_cold_heat and 
                info['cold_heat'] != selected_cold_heat):
                continue
                
            if (selected_deficiency_excess and 
                info['deficiency_excess'] != selected_deficiency_excess):
                continue
            
            results.append({
                'organ': organ,
                'symptom': symptom,
                'info': info
            })
    
    # 显示查询结果
    if results:
        st.header("📋 查询结果")
        
        for i, result in enumerate(results):
            organ = result['organ']
            symptom = result['symptom']
            info = result['info']
            
            st.subheader(f"{organ} - {symptom}")
            
            # 显示辨证信息
            col1, col2 = st.columns(2)
            
            with col1:
                # 八纲辨证
                st.markdown("**🎯 八纲辨证**")
                eight_data = {
                    "表里": info['exterior_interior'],
                    "寒热": info['cold_heat'], 
                    "虚实": info['deficiency_excess']
                }
                for principle, value in eight_data.items():
                    if value:
                        st.write(f"- **{principle}**: {value}")
                
                # 病机
                if info['pathogenesis']:
                    st.markdown("**🧬 病机分析**")
                    st.info(info['pathogenesis'])
            
            with col2:
                # 治疗原则
                if info['treatment_principle']:
                    st.markdown("**💡 治疗原则**")
                    st.success(info['treatment_principle'])
                
                # 统计信息
                st.markdown("**📊 方剂统计**")
                prescription_count = len(info['prescriptions'])
                total_herbs = sum(len(pres['herbs']) for pres in info['prescriptions'])
                st.metric("推荐方剂", prescription_count)
                st.metric("总药材数", total_herbs)
            
            # 显示方剂详情
            st.markdown("**💊 推荐方剂及来源**")
            
            if info['prescriptions']:
                for j, prescription in enumerate(info['prescriptions']):
                    with st.expander(f"📖 方剂 {j+1}: {prescription['source']}", expanded=True):
                        # 方剂基本信息
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown("**🌿 组成药材**")
                            herbs = prescription['herbs']
                            for k, herb in enumerate(herbs):
                                st.write(f"{k+1}. {herb}")
                        
                        with col2:
                            st.markdown("**📚 方剂信息**")
                            st.metric("药材数量", len(herbs))
                            st.metric("来源", prescription['source'])
                            
                            # 君臣佐使分析
                            if len(herbs) >= 3:
                                st.markdown("**⚖️ 配伍分析**")
                                st.write(f"- 君药: {herbs[0]}")
                                st.write(f"- 臣药: {herbs[1]}")
                                if len(herbs) > 2:
                                    st.write(f"- 佐使: {', '.join(herbs[2:])}")
            
            st.markdown("---")
    
    else:
        st.warning("❌ 未找到匹配的方剂")
        st.info("""
        **建议：**
        - 检查查询条件是否过于严格
        - 尝试放宽某些条件
        - 或使用左侧的层级浏览功能
        """)

else:
    # 初始页面 - 层级浏览功能
    st.info("🎯 请在右侧边栏输入查询条件，或使用下方的层级浏览")
    
    # 层级浏览
    st.header("🏗️ 层级浏览")
    
    # 第一层：选择器官
    selected_browse_organ = st.selectbox("选择器官", [""] + all_organs, key="browse_organ")
    
    if selected_browse_organ:
        # 第二层：选择症状
        organ_symptoms = list(query_structure[selected_browse_organ].keys())
        selected_browse_symptom = st.selectbox("选择症状", [""] + organ_symptoms, key="browse_symptom")
        
        if selected_browse_symptom:
            # 显示详细信息
            symptom_info = query_structure[selected_browse_organ][selected_browse_symptom]
            
            st.subheader(f"📋 {selected_browse_organ} - {selected_browse_symptom}")
            
            # 显示核心信息
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🎯 八纲辨证**")
                eight_data = {
                    "表里": symptom_info['exterior_interior'],
                    "寒热": symptom_info['cold_heat'],
                    "虚实": symptom_info['deficiency_excess']
                }
                for principle, value in eight_data.items():
                    if value:
                        st.write(f"- **{principle}**: {value}")
                
                if symptom_info['pathogenesis']:
                    st.markdown("**🧬 病机分析**")
                    st.info(symptom_info['pathogenesis'])
            
            with col2:
                if symptom_info['treatment_principle']:
                    st.markdown("**💡 治疗原则**")
                    st.success(symptom_info['treatment_principle'])
                
                st.markdown("**📊 统计信息**")
                prescription_count = len(symptom_info['prescriptions'])
                total_herbs = sum(len(pres['herbs']) for pres in symptom_info['prescriptions'])
                st.metric("方剂数量", prescription_count)
                st.metric("药材总数", total_herbs)
            
            # 显示方剂
            if symptom_info['prescriptions']:
                st.markdown("**💊 推荐方剂**")
                for i, prescription in enumerate(symptom_info['prescriptions']):
                    with st.expander(f"📖 {prescription['source']}", expanded=True):
                        st.markdown("**🌿 组成药材**")
                        for j, herb in enumerate(prescription['herbs']):
                            st.write(f"{j+1}. {herb}")
                        
                        st.markdown("**📚 来源信息**")
                        st.info(f"方剂来源: {prescription['source']}")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <i>中医智能辨证论治系统 | 支持精准查询与层级浏览</i>
</div>
""", unsafe_allow_html=True)
