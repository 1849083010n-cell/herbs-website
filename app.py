import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import os

# 页面配置
st.set_page_config(
    page_title="中医方剂药材共现查询系统 - CSV版",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 中医方剂药材共现查询系统")
st.markdown("基于CSV格式数据的智能方剂推荐")

# 检查CSV文件是否存在
def check_csv_files():
    required_files = [
        "肺部辩证与经典方 2.csv",
        "药材共现矩阵.csv"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    return missing_files

# 读取CSV数据
@st.cache_data
def load_csv_data():
    try:
        # 读取辨证方剂数据
        syndrome_df = pd.read_csv("肺部辩证与经典方 2.csv")
        
        # 读取药材共现矩阵
        cooccurrence_df = pd.read_csv("药材共现矩阵.csv")
        
        # 检查并修复列名
        if 'Unnamed: 0' in cooccurrence_df.columns:
            cooccurrence_df = cooccurrence_df.rename(columns={'Unnamed: 0': '药材'})
        elif cooccurrence_df.columns[0] == '药材':
            # 第一列已经是药材名，不需要重命名
            pass
        else:
            # 将第一列命名为药材
            cooccurrence_df = cooccurrence_df.rename(columns={cooccurrence_df.columns[0]: '药材'})
        
        return syndrome_df, cooccurrence_df
        
    except Exception as e:
        st.error(f"CSV文件读取失败: {e}")
        return None, None

# 主应用
def main():
    # 检查文件
    missing_files = check_csv_files()
    if missing_files:
        st.error("❌ 缺少必要的CSV文件：")
        for file in missing_files:
            st.write(f"- {file}")
        st.info("""
        **请先将Excel文件转换为CSV格式：**
        
        1. 运行转换脚本：
        ```bash
        python3 convert_to_csv.py
        ```
        
        2. 或者手动导出为CSV格式
        """)
        return
    
    # 加载数据
    with st.spinner('正在加载CSV数据...'):
        syndrome_df, cooccurrence_df = load_csv_data()
    
    if syndrome_df is None or cooccurrence_df is None:
        st.error("数据加载失败，请检查CSV文件格式")
        return
    
    st.success(f"✅ 成功加载 {len(syndrome_df)} 条辨证数据")
    st.success(f"✅ 成功加载 {len(cooccurrence_df)} 种药材数据")
    
    # 构建共现字典
    cooccurrence_dict = {}
    try:
        for _, row in cooccurrence_df.iterrows():
            herb = row['药材']
            cooccurrence_dict[herb] = {}
            for other_herb in cooccurrence_df.columns[1:]:
                if other_herb != '药材':
                    cooccurrence_dict[herb][other_herb] = row[other_herb]
    except Exception as e:
        st.error(f"构建共现字典失败: {e}")
        return
    
    # 数据预览
    st.subheader("📊 数据预览")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**辨证方剂数据**")
        st.dataframe(syndrome_df.head(3))
    
    with col2:
        st.write("**药材共现矩阵**")
        st.dataframe(cooccurrence_df.head(3))
    
    # 查询界面
    st.sidebar.header("🔍 查询条件")
    
    # 器官选择
    organs = syndrome_df['器官'].unique()
    selected_organ = st.sidebar.selectbox("选择器官", organs)
    
    # 根据器官筛选主症
    organ_syndromes = syndrome_df[syndrome_df['器官'] == selected_organ]
    main_symptoms = organ_syndromes['主症'].unique()
    
    # 症状输入和匹配
    symptom_input = st.sidebar.text_input("输入症状关键词", placeholder="例如：咳嗽、黄痰、发热")
    
    if symptom_input:
        # 简单关键词匹配
        matched_syndromes = []
        for syndrome in main_symptoms:
            if any(keyword in str(syndrome) for keyword in symptom_input.split()):
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
                        
                        # 解析药材（简单的顿号或逗号分隔）
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
                                    '总共现': total_cooccur
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
                                        help="该药材与方剂中其他药材的平均共现次数",
                                        format="%.2f"
                                    ),
                                    "总共现": st.column_config.NumberColumn(
                                        "总共现次数",
                                        help="该药材与方剂中其他药材的总共现次数"
                                    )
                                },
                                hide_index=True
                            )
                        else:
                            st.info("暂无共现权重数据")
            
            if prescription_count == 0:
                st.warning("未找到对应的方剂信息")
        
        else:
            st.error("未找到匹配的证型信息")

# 运行应用
if __name__ == "__main__":
    main()
