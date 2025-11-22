import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import itertools

# 页面配置
st.set_page_config(
    page_title="中医方剂查询系统",
    page_icon="🌿",
    layout="wide"
)

# 标题
st.title("🌿 中医方剂药材查询系统")
st.markdown("基于器官-主症-方剂-药材的层级查询")

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
    
    # 检测器官列
    for name in ['器官', 'Organ', 'organ', '脏器']:
        if name in df.columns:
            columns_info['organ'] = name
            break
    else:
        columns_info['organ'] = df.columns[0] if len(df.columns) > 0 else None
    
    # 检测主症列
    for name in ['主症', '症状', 'Symptom', 'symptom', '证型']:
        if name in df.columns:
            columns_info['symptom'] = name
            break
    else:
        columns_info['symptom'] = df.columns[1] if len(df.columns) > 1 else None
    
    # 检测八纲辨证列
    for name in ['表里', '表里辨证', 'Exterior_Interior']:
        if name in df.columns:
            columns_info['exterior_interior'] = name
            break
    
    for name in ['寒热', '寒热辨证', 'Cold_Heat']:
        if name in df.columns:
            columns_info['cold_heat'] = name
            break
    
    for name in ['虚实', '虚实辨证', 'Deficiency_Excess']:
        if name in df.columns:
            columns_info['deficiency_excess'] = name
            break
    
    # 检测病机和治疗原则
    for name in ['病机', 'Pathogenesis', '病机分析']:
        if name in df.columns:
            columns_info['pathogenesis'] = name
            break
    
    for name in ['治疗原则', 'Treatment_Principle']:
        if name in df.columns:
            columns_info['treatment_principle'] = name
            break
    
    # 检测药材和来源列
    columns_info['herb_columns'] = []
    columns_info['source_columns'] = []
    
    # 检测药材列（药材1, 药材2, 药材3...）
    for i in range(1, 6):  # 检查最多5个药材列
        for pattern in [f'药材{i}', f'Herb{i}', f'herb{i}']:
            if pattern in df.columns:
                columns_info['herb_columns'].append(pattern)
                break
        else:
            # 如果没有找到标准格式，尝试其他模式
            for col in df.columns:
                if '药材' in col and str(i) in col:
                    columns_info['herb_columns'].append(col)
                    break
    
    # 检测来源列（来源1, 来源2, 来源3...）
    for i in range(1, 6):  # 检查最多5个来源列
        for pattern in [f'来源{i}', f'Source{i}', f'source{i}']:
            if pattern in df.columns:
                columns_info['source_columns'].append(pattern)
                break
        else:
            # 如果没有找到标准格式，尝试其他模式
            for col in df.columns:
                if '来源' in col and str(i) in col:
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
st.sidebar.success(f"器官列: {columns_info['organ']}")
st.sidebar.success(f"主症列: {columns_info['symptom']}")
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
    else:
        herbs = [herbs_text.strip()]
    
    return herbs

# 构建查询数据结构
def build_query_structure(df, columns_info):
    """构建器官-主症-来源-药材的查询结构"""
    query_structure = {}
    
    for _, row in df.iterrows():
        organ = row[columns_info['organ']]
        symptom = row[columns_info['symptom']]
        
        if pd.isna(organ) or pd.isna(symptom):
            continue
        
        # 初始化器官
        if organ not in query_structure:
            query_structure[organ] = {}
        
        # 初始化主症
        if symptom not in query_structure[organ]:
            query_structure[organ][symptom] = {
                'exterior_interior': row.get(columns_info.get('exterior_interior'), ''),
                'cold_heat': row.get(columns_info.get('cold_heat'), ''),
                'deficiency_excess': row.get(columns_info.get('deficiency_excess'), ''),
                'pathogenesis': row.get(columns_info.get('pathogenesis'), ''),
                'treatment_principle': row.get(columns_info.get('treatment_principle'), ''),
                'prescriptions': []
            }
        
        # 添加方剂信息
        prescriptions = []
        for i, (herb_col, source_col) in enumerate(zip(columns_info['herb_columns'], columns_info['source_columns'])):
            if herb_col in row and pd.notna(row[herb_col]):
                herbs = parse_herbs(row[herb_col])
                source = row[source_col] if source_col in row and pd.notna(row.get(source_col)) else f"方剂{i+1}"
                
                if herbs:  # 只有有药材时才添加
                    prescriptions.append({
                        'source': source,
                        'herbs': herbs
                    })
        
        # 合并相同主症的方剂信息
        query_structure[organ][symptom]['prescriptions'].extend(prescriptions)
    
    return query_structure

# 构建查询结构
query_structure = build_query_structure(syndrome_df, columns_info)

st.success(f"✅ 数据加载成功！共 {len(query_structure)} 个器官，{sum(len(symptoms) for symptoms in query_structure.values())} 个主症")

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
    
    st.header(f"📋 查询结果：{selected_organ} - {selected_symptom}")
    
    # 显示辨证信息
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if symptom_info['exterior_interior']:
            st.metric("表里", symptom_info['exterior_interior'])
        if symptom_info['cold_heat']:
            st.metric("寒热", symptom_info['cold_heat'])
    
    with col2:
        if symptom_info['deficiency_excess']:
            st.metric("虚实", symptom_info['deficiency_excess'])
        if symptom_info['pathogenesis']:
            st.metric("病机", symptom_info['pathogenesis'])
    
    with col3:
        if symptom_info['treatment_principle']:
            st.markdown("**治疗原则**")
            st.info(symptom_info['treatment_principle'])
    
    # 显示方剂信息
    st.subheader("💊 推荐方剂")
    
    if symptom_info['prescriptions']:
        for i, prescription in enumerate(symptom_info['prescriptions']):
            with st.expander(f"方剂 {i+1}: {prescription['source']}", expanded=True):
                # 显示药材列表
                st.markdown("**组成药材:**")
                for j, herb in enumerate(prescription['herbs']):
                    st.write(f"- {herb}")
                
                # 药材统计
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("药材数量", len(prescription['herbs']))
                with col2:
                    unique_herbs = len(set(prescription['herbs']))
                    st.metric("独特药材", unique_herbs)
                
                # 药材分析
                if len(prescription['herbs']) > 1:
                    st.markdown("**药材组合分析:**")
                    herb_pairs = list(itertools.combinations(prescription['herbs'], 2))
                    st.write(f"- 共有 {len(herb_pairs)} 种药材组合")
                    st.write(f"- 前3种组合: {', '.join(['+'.join(pair) for pair in herb_pairs[:3]])}")
    else:
        st.warning("该主症下暂无方剂信息")

else:
    # 初始页面 - 显示系统概览
    st.info("👈 请在左侧选择器官和主症开始查询")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 系统概览")
        
        # 统计信息
        total_organs = len(query_structure)
        total_symptoms = sum(len(symptoms) for symptoms in query_structure.values())
        total_prescriptions = 0
        
        # 计算总方剂数
        for organ in query_structure.values():
            for symptom in organ.values():
                total_prescriptions += len(symptom['prescriptions'])
        
        st.metric("器官数量", total_organs)
        st.metric("主症数量", total_symptoms)
        st.metric("方剂总数", total_prescriptions)
        
        # 显示器官列表
        with st.expander("📋 器官列表"):
            for organ in organs:
                symptom_count = len(query_structure[organ])
                st.write(f"- **{organ}** ({symptom_count}个主症)")
    
    with col2:
        st.subheader("🎯 使用说明")
        st.markdown("""
        ### 查询流程：
        1. **选择器官** - 从左侧选择要查询的器官
        2. **选择主症** - 选择具体的证型主症
        3. **查看方剂** - 浏览推荐的经典方剂
        
        ### 系统特色：
        - 🏗️ **层级结构** - 器官 → 主症 → 方剂 → 药材
        - 📚 **多来源方剂** - 每个主症包含多个经典方剂
        - 🔍 **智能搜索** - 支持症状关键词过滤
        - 📊 **组合分析** - 分析药材配伍关系
        
        ### 数据来源：
        - 《伤寒论》、《温病条辨》等经典著作
        - 历代名医经验方剂
        - 现代临床应用方剂
        """)
    
    # 显示示例查询
    st.subheader("✨ 快速查询示例")
    example_cols = st.columns(3)
    
    examples = [
        {"organ": "肺", "symptom": "风寒犯肺", "description": "咳嗽、白痰、畏寒"},
        {"organ": "肺", "symptom": "风热犯肺", "description": "咳嗽、黄痰、发热"},
        {"organ": "脾", "symptom": "脾气虚", "description": "食欲差、腹胀、乏力"}
    ]
    
    for i, example in enumerate(examples):
        if example["organ"] in query_structure and example["symptom"] in query_structure[example["organ"]]:
            with example_cols[i]:
                st.markdown(f"**{example['organ']} - {example['symptom']}**")
                st.caption(example["description"])
                if st.button("查看详情", key=f"example_{i}"):
                    st.session_state.selected_organ = example["organ"]
                    st.session_state.selected_symptom = example["symptom"]
                    st.rerun()

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <i>中医方剂智能查询系统 | 基于器官-主症-方剂-药材层级结构</i>
</div>
""", unsafe_allow_html=True)
