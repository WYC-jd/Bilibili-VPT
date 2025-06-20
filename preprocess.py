import pandas as pd
import numpy as np
import re
import os

output_path = "./output/"
input_file = output_path + "bili.csv"
output_file = output_path + "bili_cleaned.csv"

# 创建不存在的目录
os.makedirs(output_path, exist_ok=True)


def clean_bilibili_data(input_path: str, output_path: str) -> pd.DataFrame:
    """
    完整数据清洗流程：
    1. 基础清洗（缺失值/重复值/格式标准化）
    2. 异常值处理
    3. 特征工程
    4. 数据标准化
    """
    # ========== 1. 数据加载与基础清洗 ==========
    df = pd.read_csv(input_path, sep=',', encoding='utf-8')
    
    # 1.1 列名标准化（去除空格/特殊字符）
    df.columns = [col.strip().replace('\n', '') for col in df.columns]
    
    # 1.2 处理缺失值
    df.fillna({
        '精确播放数': 0,
        '点赞数': 0,
        '投硬币枚数': 0,
        '收藏人数': 0,
        '转发人数': 0,
        '视频时长(秒)': df['视频时长(秒)'].median(),
        '视频简介': '无简介',
        '作者简介': '无简介'
    }, inplace=True)
    
    # 1.3 删除完全重复的行
    df.drop_duplicates(inplace=True)
    
    # ========== 2. 异常值处理 ==========
    # 2.1 过滤播放量为0或负数的记录
    df = df[df['精确播放数'] > 0]
    
    # 2.2 处理极端值（播放量>3倍标准差）
    play_mean, play_std = df['精确播放数'].mean(), df['精确播放数'].std()
    df = df[df['精确播放数'] <= play_mean + 3 * play_std]
    
    # 2.3 清洗时长异常值（<5秒或>6小时）
    df = df[(df['视频时长(秒)'] >= 5) & (df['视频时长(秒)'] <= 6*3600)]
    
    # ========== 3. 特征工程 ==========
    # 3.1 时间特征
    df['发布时间'] = pd.to_datetime(df['发布时间'])
    df['发布年份'] = df['发布时间'].dt.year
    df['发布月份'] = df['发布时间'].dt.month
    df['发布小时'] = df['发布时间'].dt.hour
    df['是否周末'] = df['发布时间'].dt.weekday >= 5
    
    # 3.2 互动比率特征
    df['点赞率'] = df['点赞数'] / df['精确播放数']
    df['收藏率'] = df['收藏人数'] / df['精确播放数']
    df['转发率'] = df['转发人数'] / df['精确播放数']
    df['互动指数'] = (df['点赞数']*0.4 + df['收藏人数']*0.3 + df['转发人数']*0.3) / df['精确播放数']
    
    # 3.3 文本特征清洗
    df['视频简介'] = df['视频简介'].apply(lambda x: re.sub(r'[^\w\s]', '', str(x)))  # 去标点
    df['标题长度'] = df['标题'].str.len()
    
    # 3.4 分类特征处理
    df['主标签'] = df['标签'].str.split(',').str[0].fillna('其他')
    
    # ========== 4. 数据标准化 ==========
    # 4.1 对数变换（缓解长尾分布）
    df['log_播放量'] = np.log1p(df['精确播放数'])
    
    # 4.2 数值特征标准化（可选，按模型需求）
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    df[['视频时长(秒)', '点赞数', '收藏人数']] = scaler.fit_transform(
        df[['视频时长(秒)', '点赞数', '收藏人数']]
    )
    
    # ========== 5. 保存结果 ==========
    # 删除中间列（保留清洗后特征）
    final_columns = [
        'log_播放量',         # 目标变量
        '点赞率', '收藏率', '转发率',  # 互动特征
        '视频时长(秒)', '标题长度',    # 内容特征  
        '发布小时', '是否周末',      # 时间特征
        '主标签'               # 分类特征
    ]
    df = df[final_columns]
    
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"清洗完成！最终保留 {len(final_columns)} 个特征，样例数据：\n{df.head(2)}")
    return df

# 执行清洗
if __name__ == "__main__":
    clean_df = clean_bilibili_data(input_file, output_file)