# B站视频处理工具集（Bilibili-VPT） - V0.1

## 项目概述
本项目包含**4**个主要脚本，用于从 **B站(Bilibili) 获取视频信息、下载视频、去除水印、数据清洗**。这些工具可以帮助用户进行B站视频的数据分析和内容处理。

功能整合和修改自以下**Github/博客**：
   - **1. bv号爬取：** https://blog.csdn.net/Smile_to_destiny/article/details/132642215
   - **2. 去水印：** https://blog.csdn.net/weixin_63253486/article/details/131421022
   - **3. 视频信息爬虫：** https://github.com/Ghauster/Bilivideoinfo

如有疑问，也可询问原作者。

---

## 文件说明
**1.** bvid.py - B站视频ID爬取工具

- **1.1 功能：**
    - 根据关键词列表搜索B站视频
    - 提取搜索结果中的视频BV号
    - 先将每个关键词对应的BV号列表保存到bvid文件夹中
    - 再将所有bvid文件夹里的BV号列表去重合并，保存为download_list.log到log文件夹中

- **1.2 使用方法：**
    - 创建keywords.log文件，每行一个搜索关键词
    - 运行脚本：python bvid.py
    - 结果保存在./bvid/目录下，格式为{关键词}BV号.log

**2.** scraper.py - 视频信息爬取与下载工具

- **2.1 功能：**
    - 从BV号列表中下载视频（支持多种清晰度）
    - 爬取视频详细信息（播放量、点赞数、标签等）
    - 自动合并音视频轨道
    - 支持使用浏览器cookie登录获取高清资源
  
- **2.2 使用方法：**
    - 准备BV号列表文件./log/download_list.log
    - 运行脚本：python scraper.py

    - 根据提示选择操作：
        - 是否下载视频
        - 是否爬取视频信息
        - 选择视频清晰度（720p/1080p/4K等）

    - 结果保存在：
        - 视频文件：./video/
        - 视频信息：./output/bili.csv

**3.** video.py - 视频水印去除工具

- **3.1 功能：**
    - 去除视频中的水印
    - 支持批量处理

- **3.2 使用方法：**
    - 确保视频文件已下载到./video/
    - 运行脚本：python video.py

    - 选择操作：
        - 1：去水印（需手动框选水印区域）
        - 2：去字幕 **（尚未完善，请勿使用）**

    - 处理后的视频保存在./video/watermark/

**4.** preprocess.py - 数据清洗工具
- **4.1 功能：**
    - 清洗B站视频数据
    - 处理缺失值和异常值
    - 特征工程（计算互动率、时间特征等）
    - 数据标准化

- **4.2 使用方法：**
    - 确保有原始数据文件./output/bili.csv
    - 运行脚本：python preprocess.py
    - 清洗后的数据保存在./output/bili_cleaned.csv

---

## 目录结构
```bash
├── bvid/                # 存储初始BV号文件
├── log/                 # 日志等文件
│   ├──  ffmpeg.log           # ffmpeg日志
│   ├──  youget.log           # youget日志
│   ├──  video_errorlist.log  # 爬取视频信息错误日志
│   ├──  keywords.log         # 搜索关键词列表
│   ├──  download_list.log    # 要下载的bv号列表
│   ├──  video_list.log       # 已下载的bv号列表
│   └──  watermark_list.log   # 已去除水印的bv号列表
│
├── output/              # 输出文件（CSV/Excel）
├── video/               # 视频文件
│   └── watermark/       # 去水印后的视频
│
├── bvid.py              # BV号爬取脚本
├── scraper.py           # 视频下载与信息爬取脚本
├── video.py             # 视频处理脚本
└── preprocess.py        # 数据清洗脚本
```

---

## 注意事项

**1. 文件**
- 仅 **keywords.log** 需要手动生成；
- 如果没有用 bvid.py 生成的 **download_list.log** 来进行视频下载和信息爬取，需要自己手动生成；


**2. 配置**
- 使用前请确保已安装**Chrome浏览器**和对应版本的**ChromeDriver**；
- 根据py文件安装**库**, 以下列出重要库
    ```bash
    selenium 
    beautifulsoup4 
    pandas 
    numpy 
    openpyxl 
    requests 
    browser-cookie3 
    moviepy 
    opencv-python
    ```

**3. 功能**
- 下载高清视频需要提供**B站登录cookie**（会自动生成，cookie临时文件在程序完成后自动删除）；

- 去**水印**功能需要**手动**框选区域，效果取决于原始视频质量，视频处理需要**较长时间**，请耐心等待；

- **去字幕功能尚未完善，请勿使用**；
