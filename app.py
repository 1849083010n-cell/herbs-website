import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import itertools

# 页面配置
st.set_page_config(
    page_title="中医方剂药材共现查询系统",
    page_icon="🌿",
    layout="wide"
)

# 标题
st.title("🌿 中医方剂药材共现权重查询系统")
st.markdown("基于方剂内药材共现关系的智能推荐")

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

# 从方剂数据构建共现矩阵
@st.cache_data
def build_cooccurrence_matrix(syndrome_df):
    """
    从所有方剂中构建药材共现矩阵
    """
    cooccurrence_dict = defaultdict(lambda: defaultdict(int))
    all_herbs = set()
    
    # 收集所有药材列
    herb_columns = []
    for col in syndrome_df.columns:
        if any(keyword in col for keyword in ['药材', 'Herb', 'herb']):
            herb_columns.append(col)
    
    # 如果没有检测到药材列，使用默认模式
    if not herb_columns:
        herb_columns = [f'药材{i}' for i in range(1, 5)]
    
    st.sidebar.info(f"检测到的药材列: {herb_columns}")
    
    # 遍历每一行（每个证型）
    for _, row in syndrome_df.iterrows():
        # 收集该证型的所有药材
        current_herbs = []
        
        for herb_col in herb_columns:
            if herb_col in row and pd.notna(row[herb_col]):
                herbs_text = str(row[herb_col])
                # 解析药材
                if '、' in herbs_text:
                    herbs = [herb.strip() for herb in herbs_text.split('、') if herb.strip()]
                elif ',' in herbs_text:
                    herbs = [herb.strip() for herb in herbs_text.split(',') if herb.strip()]
                else:
                    herbs = [herbs_text.strip()]
                
                current_herbs.extend(herbs)
                all_herbs.update(herbs)
        
        # 计算该方剂内药材的共现关系
        if len(current_herbs) > 1:
            for herb1, herb2 in itertools.combinations(set(current_herbs), 2):
                cooccurrence_dict[herb1][herb2] += 1
                cooccurrence_dict[herb2][herb1] += 1
    
    return dict(cooccurrence_dict), all_herbs

# 加载数据
syndrome_df = load_syndrome_data()

if syndrome_df is None:
    st.stop()

# 构建共现矩阵
with st.spinner("正在构建药材共现矩阵..."):
    cooccurrence_dict, all_herbs = build_cooccurrence_matrix(syndrome_df)

st.success(f"✅ 数据加载成功！共分析 {len(syndrome_df)} 个证型，发现 {len(all_herbs)} 种药材")

# 自动检测列名
def detect_column_names(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return df.columns[0] if len(df.columns) > 0 else None

organ_col = detect_column_names(syndrome_df, ['器官', 'Organ', 'organ', '脏器'])
symptom_col = detect_column_names(syndrome_df, ['主症', '症状', 'Symptom', 'symptom', '证型'])
exterior_interior_col = detect_column_names(syndrome_df, ['表里', '表里辨证', 'Exterior_Interior'])
cold_heat_col = detect_column_names(syndrome_df, ['寒热', '寒热辨证', 'Cold_Heat'])
deficiency_excess_col = detect_column_names(syndrome_df, ['虚实', '虚实辨证', 'Deficiency_Excess'])
pathogenesis_col = detect_column_names(syndrome_df, ['病机', 'Pathogenesis', '病机分析'])
treatment_principle_col = detect_column_names(syndrome_df, ['治疗原则', '治疗原则', 'Treatment_Principle'])

# 侧边栏 - 查询条件
st.sidebar.header("🔍 查询条件")

# 器官选择
try:
    organs = syndrome_df[organ_col].unique()
    selected_organ = st.sidebar.selectbox("选择器官", organs)
except KeyError as e:
    st.error(f"找不到器官列，可用列: {list(syndrome_df.columns)}")
    st.stop()

# 根据器官筛选主症
organ_syndromes = syndrome_df[syndrome_df[organ_col] == selected_organ]
main_symptoms = organ_syndromes[symptom_col].unique()

# 症状输入
symptom_input = st.sidebar.text_input("输入症状关键词", placeholder="例如：咳嗽、黄痰、发热")

# 主症选择
if symptom_input:
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
    matched_prescriptions = organ_syndromes[organ_syndromes[symptom_col] == selected_symptom]
    
    if not matched_prescriptions.empty:
        st.header(f"📋 查询结果：{selected_organ} - {selected_symptom}")
        
        # 显示八纲辨证信息
        syndrome_info = matched_prescriptions.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if exterior_interior_col in syndrome_info:
                st.metric("表里", syndrome_info[exterior_interior_col])
        
        with col2:
            if cold_heat_col in syndrome_info:
                st.metric("寒热", syndrome_info[cold_heat_col])
        
        with col3:
            if deficiency_excess_col in syndrome_info:
                st.metric("虚实", syndrome_info[deficiency_excess_col])
        
        with col4:
            if pathogenesis_col in syndrome_info:
                st.metric("病机", syndrome_info[pathogenesis_col])
        
        if treatment_principle_col in syndrome_info:
            st.markdown(f"**治疗原则：** {syndrome_info[treatment_principle_col]}")
        
        # 显示方剂和药材
        st.subheader("💊 推荐方剂及药材")
        
        # 检测药材列
        herb_columns = []
        source_columns = []
        
        for col in syndrome_df.columns:
            if any(keyword in col for keyword in ['药材', 'Herb', 'herb']):
                herb_columns.append(col)
            elif any(keyword in col for keyword in ['来源', 'Source', '方剂']):
                source_columns.append(col)
        
        if not herb_columns:
            herb_columns = [f'药材{i}' for i in range(1, 5)]
        if not source_columns:
            source_columns = [f'来源{i}' for i in range(1, 5)]
        
        # 遍历所有方剂
        prescription_count = 0
        for i, (herb_col, source_col) in enumerate(zip(herb_columns, source_columns)):
            if herb_col in syndrome_info and pd.notna(syndrome_info[herb_col]):
                prescription_count += 1
                
                source_name = syndrome_info[source_col] if source_col in syndrome_info and pd.notna(syndrome_info.get(source_col)) else f"方剂 {prescription_count}"
                
                with st.expander(f"方剂 {prescription_count}: {source_name}", expanded=True):
                    herbs_text = str(syndrome_info[herb_col])
                    
                    # 解析药材
                    herbs = []
                    if '、' in herbs_text:
                        herbs = [herb.strip() for herb in herbs_text.split('、') if herb.strip()]
                    elif ',' in herbs_text:
                        herbs = [herb.strip() for herb in herbs_text.split(',') if herb.strip()]
                    else:
                        herbs = [herbs_text.strip()]
                    
                    # 计算共现权重
                    herb_weights = []
                    for herb in herbs:
                        if herb in cooccurrence_dict:
                            # 计算该药材与其他药材的共现次数
                            other_herbs = [h for h in herbs if h != herb]
                            if other_herbs:
                                cooccur_values = [cooccurrence_dict[herb].get(other, 0) for other in other_herbs]
                                avg_cooccur = np.mean(cooccur_values) if cooccur_values else 0
                                total_cooccur = sum(cooccur_values)
                                max_cooccur = max(cooccur_values) if cooccur_values else 0
                            else:
                                avg_cooccur = 0
                                total_cooccur = 0
                                max_cooccur = 0
                            
                            herb_weights.append({
                                '药材': herb,
                                '平均共现': round(avg_cooccur, 2),
                                '总共现': total_cooccur,
                                '最大共现': max_cooccur,
                                '出现频次': herbs.count(herb)
                            })
                        else:
                            herb_weights.append({
                                '药材': herb,
                                '平均共现': 0,
                                '总共现': 0,
                                '最大共现': 0,
                                '出现频次': herbs.count(herb),
                                '备注': '新药材'
                            })
                    
                    # 排序
                    herb_weights.sort(key=lambda x: x['总共现'], reverse=True)
                    
                    # 显示表格
                    if herb_weights:
                        weights_df = pd.DataFrame(herb_weights)
                        
                        column_config = {
                            "药材": "药材名称",
                            "平均共现": st.column_config.NumberColumn(
                                "平均共现权重",
                                help="与该方剂中其他药材的平均共现次数",
                                format="%.2f"
                            ),
                            "总共现": st.column_config.NumberColumn(
                                "总共现次数", 
                                help="与该方剂中其他药材的总共现次数"
                            ),
                            "最大共现": st.column_config.NumberColumn(
                                "最大共现次数",
                                help="与该方剂中某一药材的最大共现次数"
                            ),
                            "出现频次": st.column_config.NumberColumn(
                                "出现频次",
                                help="该药材在方剂中出现的次数"
                            )
                        }
                        
                        if '备注' in weights_df.columns:
                            column_config["备注"] = "备注信息"
                        
                        st.dataframe(weights_df, column_config=column_config, hide_index=True)
                        
                        # 可视化
                        valid_herbs = [h for h in herb_weights if h['总共现'] > 0]
                        if valid_herbs:
                            st.subheader("📊 药材共现关系可视化")
                            
                            viz_type = st.selectbox("选择图表类型", ["柱状图-总共现", "柱状图-平均共现"], key=f"viz_{i}")
                            
                            if "总共现" in viz_type:
                                chart_data = pd.DataFrame({
                                    '药材': [h['药材'] for h in valid_herbs],
                                    '共现次数': [h['总共现'] for h in valid_herbs]
                                })
                                st.bar_chart(chart_data.set_index('药材'))
                            else:
                                chart_data = pd.DataFrame({
                                    '药材': [h['药材'] for h in valid_herbs],
                                    '平均共现': [h['平均共现'] for h in valid_herbs]
                                })
                                st.bar_chart(chart_data.set_index('药材'))
                            
                            # 显示共现关系网络
                            st.subheader("🕸️ 药材共现关系网络")
                            cooccur_pairs = []
                            for j, herb1 in enumerate(herbs):
                                for k, herb2 in enumerate(herbs):
                                    if j < k and herb1 in cooccurrence_dict and herb2 in cooccurrence_dict[herb1]:
                                        count = cooccurrence_dict[herb1][herb2]
                                        if count > 0:
                                            cooccur_pairs.append(f"{herb1} ↔ {herb2} (共现{count}次)")
                            
                            if cooccur_pairs:
                                for pair in cooccur_pairs[:10]:  # 显示前10对
                                    st.write(f"- {pair}")
                            else:
                                st.info("该方剂中的药材组合为新的共现关系")
                        else:
                            st.info("该方剂中的药材组合为新的共现模式")
        
        if prescription_count == 0:
            st.warning("未找到对应的方剂信息")

else:
    # 初始状态
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 系统概览")
        st.metric("证型数量", len(syndrome_df))
        st.metric("药材种类", len(all_herbs))
        st.metric("器官类型", len(organs))
        
        with st.expander("数据统计"):
            st.write(f"- 总方剂数: {len(syndrome_df)}")
            st.write(f"- 总药材数: {len(all_herbs)}")
            st.write(f"- 共现关系数: {sum(len(v) for v in cooccurrence_dict.values()) // 2}")
            
            # 显示最常见的药材
            herb_frequency = defaultdict(int)
            for herb in all_herbs:
                herb_frequency[herb] = sum(1 for v in cooccurrence_dict[herb].values() if v > 0)
            
            top_herbs = sorted(herb_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
            st.write("最常见药材:")
            for herb, freq in top_herbs:
                st.write(f"  - {herb}: {freq}次共现")
    
    with col2:
        st.subheader("🎯 使用说明")
        st.markdown("""
        ### 查询步骤：
        1. **选择器官**（如：肺、脾）
        2. **输入症状关键词**或选择主症  
        3. **点击查询**查看推荐方剂
        4. **查看药材共现权重**分析
        
        ### 系统特色：
        - 🔬 **动态共现计算**：实时分析药材组合关系
        - 📊 **多维度权重**：平均、总计、最大共现
        - 🕸️ **关系网络**：显示药材间的关联强度
        - 💡 **智能发现**：识别新的药材组合模式
        
        💡 **共现权重**：基于所有方剂中药材同时出现的频率计算
        """)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <i>基于方剂内药材共现关系的智能推荐系统 | 单文件动态计算版本</i>
</div>
""", unsafe_allow_html=True)
