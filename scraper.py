import re
import os
import time
import requests
import tempfile
import threading
import subprocess
import browser_cookie3
import pandas as pd

from bs4 import BeautifulSoup
from openpyxl import Workbook

# ========== 配置项 ==========
print_lock = threading.Lock()

video_save_path = "./video/"  # 视频保存目录（仅在下载模式下使用）
log_save_path = "./log/"
output_path = "./output/"

input_file = log_save_path + "test.log" # "download_list.log" 
check_file = log_save_path + "video_list.log"
error_file = log_save_path + "video_errorlist.log"

log_file1 = log_save_path + "ffmpeg.log"
log_file2 = log_save_path + "youget.log"

ioput_file = output_path + "raw.xlsx"
output_file = output_path + "bili.csv"

# 创建不存在的目录
os.makedirs(video_save_path, exist_ok=True)
os.makedirs(log_save_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

if not os.path.exists(check_file):
    open(check_file, 'a').close()  # 创建空文件

headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip, deflate, br", "Upgrade-Insecure-Requests": "1", "Cache-Control": "max-age=0", }


def write_error_log(message):
    with open(error_file, "a") as file:
        file.write(message + "\n")

def is_url(video_id_or_url):
    return video_id_or_url.startswith("http") or video_id_or_url.startswith("https")

def get_video_url(video_id_or_url):
    if is_url(video_id_or_url):
        return video_id_or_url
    else:
        return f"https://www.bilibili.com/video/{video_id_or_url}"

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)

# ========== 加载动画 ==========
def loading_dots(stop_event, text="加载中", interval=0.5):
    while not stop_event.is_set():
        for i in range(4):
            if stop_event.is_set():
                break
            dots = '.' * i
            with print_lock:
                print(f"\r{text}{dots}   ", end='', flush=True)
            time.sleep(interval)
    # 清理行
    with print_lock:
        print(f"\r{' ' * (len(text) + 6)}", end='\r')


# ========== 合并音轨函数 ==========
def merge_audio_video(video_path, audio_path, output_path):
    ffmpeg_path = r"D:\ffmpeg.exe"  # ffmpeg.exe绝对路径

    command = [
        ffmpeg_path,
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        output_path
    ]

    flag = False

    try:
        # 保存到日志文件
        with open(log_file1, "w") as f:
            subprocess.run(command, stdout=f, stderr=f, check=True)
        safe_print(f"\n合并完成：{output_path}")

        flag = True

    except subprocess.CalledProcessError as e:
        safe_print(f"\n合并失败：{e}")

    return flag


# ========== 文件匹配和批量合并函数 ==========
def auto_merge_folder(folder_path, id_list, delete_source=True):
    # 文件名匹配形如：名字[00].mp4 和 名字[01].mp4
    pattern_video = re.compile(r"^(.*)\[00\]\.mp4$")
    pattern_audio = re.compile(r"^(.*)\[01\]\.mp4$")

    files = os.listdir(folder_path)
    video_files = {}
    audio_files = {}

    # 收集文件
    for f in files:
        v_match = pattern_video.match(f)
        a_match = pattern_audio.match(f)
        if v_match:
            base_name = v_match.group(1)
            video_files[base_name] = f
        elif a_match:
            base_name = a_match.group(1)
            audio_files[base_name] = f

    # 找到匹配对并合并
    for video_id_or_url, base_name in zip(id_list, video_files):
        if base_name in audio_files:
            video_path = os.path.join(folder_path, video_files[base_name])
            audio_path = os.path.join(folder_path, audio_files[base_name])
            output_path = os.path.join(folder_path, video_id_or_url.strip() + "_" + base_name + ".mp4")

            flag = merge_audio_video(video_path, audio_path, output_path)
            if flag:
                # === 在成功合并后追加 BV 号到记录文件 ===
                with open(check_file, "a", encoding="utf-8") as f:
                    f.write(f"{video_id_or_url}\n")


            if delete_source:
                os.remove(video_path)
                os.remove(audio_path)
                safe_print(f"已删除源文件: {video_files[base_name]}, {audio_files[base_name]}\n")


# ========== 下载视频函数 ==========
def download_video_by_url(id_list, quality="dash-flv720-AVC"): # 默认720p

    # 清晰度优先级链（从高到低）
    quality_priority = [
        'dash-hdflv2_4k-HEVC',   # 4k
        'dash-flv_p60-AVC',      # 1080p 60fps
        'dash-flv-AVC',          # 1080p
        'dash-flv720-AVC',       # 720p
    ]

    # 格式码 -> 显示名称
    quality_display_map = {
        'dash-hdflv2_4k-HEVC': '4K',
        'dash-flv_p60-AVC': '1080P 60fps',
        'dash-flv-AVC': '1080P',
        'dash-flv720-AVC': '720P',
    }


    # 从当前选择的清晰度开始向下降级
    try_start_index = quality_priority.index(quality)


    for i, video_id_or_url in enumerate(id_list, 1):
        url = get_video_url(video_id_or_url.strip())
        success = False
        last_exception = None

        for q in quality_priority[try_start_index:]:         
            print(f"第{i}个视频 开始下载: {url}, 清晰度: {quality_display_map.get(q, q)}")

            cmd = ["you-get", "--debug", "-o", video_save_path]
            if cookie_file_path:
                cmd += ["--cookies", cookie_file_path]  # 传入cookie文件
            if quality:
                cmd += ["--format=" + q]
            cmd.append(url)

            try:
                # 保存到日志文件
                with open(log_file2, "w") as f:
                    subprocess.run(cmd, stdout=f, stderr=f, check=True)

                print(f"第{i}个视频 下载完成: {url}, 清晰度: {quality_display_map.get(q, q)}")

                success = True
                break

            except subprocess.CalledProcessError as e:
                last_exception = e  # 记录异常
                print(f"第{i}个视频 下载失败 ({quality_display_map.get(q, q)})，尝试更低清晰度...")
                continue

        if not success:
            write_error_log(f"第{i}个视频下载失败（全部清晰度尝试失败）: {url} 错误：{str(last_exception)}")
            print(f"第{i}个视频 下载失败（全部清晰度失败）")
    
    print()
    stop_event = threading.Event()
    t = threading.Thread(target=loading_dots, args=(stop_event, "开始合并"))
    t.start()  # 启动动画线程

    auto_merge_folder(folder_path=video_save_path, id_list=id_list, delete_source=True)

    # 任务完成，停止动画
    stop_event.set()
    t.join()


# ========== 爬取信息函数 ==========
def extract_video_info(id_list, new_wb, new_ws):    
    for i, video_id_or_url in enumerate(id_list, 1):
        url = get_video_url(video_id_or_url.strip())
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            # 视频 aid、视频时长和作者 id
            initial_state_script = soup.find("script", string=re.compile("window.__INITIAL_STATE__"))
            initial_state_text = initial_state_script.string

            author_id_pattern = re.compile(r'"mid":(\d+)')
            video_aid_pattern = re.compile(r'"aid":(\d+)')
            video_duration_pattern = re.compile(r'"duration":(\d+)')

            author_id = author_id_pattern.search(initial_state_text).group(1)
            video_aid = video_aid_pattern.search(initial_state_text).group(1)
            video_duration_raw = int(video_duration_pattern.search(initial_state_text).group(1))
            video_duration = video_duration_raw - 2

            # 提取标题
            title_raw = soup.find("title").text
            title = re.sub(r"_哔哩哔哩_bilibili", "", title_raw).strip()

            # 提取标签
            keywords_content = soup.find("meta", itemprop="keywords")["content"]
            content_without_title = keywords_content.replace(title + ',', '')
            keywords_list = content_without_title.split(',')
            tags = ",".join(keywords_list[:-4])

            meta_description = soup.find("meta", itemprop="description")["content"]
            numbers = re.findall(
                r'[\s\S]*?视频播放量 (\d+)、弹幕量 (\d+)、点赞数 (\d+)、投硬币枚数 (\d+)、收藏人数 (\d+)、转发人数 (\d+)',
                meta_description)

            # 提取作者
            author_search = re.search(r"视频作者\s*([^,]+)", meta_description)
            if author_search:
                author = author_search.group(1).strip()
            else:
                author = "未找到作者"

            # 提取作者简介
            author_desc_pattern = re.compile(r'作者简介 (.+?),')
            author_desc_match = author_desc_pattern.search(meta_description)
            if author_desc_match:
                author_desc = author_desc_match.group(1)
            else:
                author_desc = "未找到作者简介"

            # 提取视频简介
            meta_parts = re.split(r',\s*', meta_description)
            if meta_parts:
                video_desc = meta_parts[0].strip()
            else:
                video_desc = "未找到视频简介"

            if numbers:
                views, danmaku, likes, coins, favorites, shares = [int(n) for n in numbers[0]]
                publish_date = soup.find("meta", itemprop="uploadDate")["content"]
                new_ws.append([title, url, author, author_id, views, danmaku, likes, coins, favorites, shares, publish_date, video_duration, video_desc, author_desc, tags, video_aid])
                print(f"第{i}行视频{url}已完成爬取")
            else:
                print(f"第{i}行视频 {url}未找到相关数据，可能为分集视频")

        except Exception as e:
            write_error_log(f"第{i}行视频发生错误：{e}")
            print(f"第{i}行发生错误，已记录到错误日志:出错数据为{video_id_or_url}")

    new_wb.save(ioput_file)
    print(f"视频信息已保存到 {ioput_file}")

def get_bilibili_cookies():
    # 读取 Chrome 的 Cookies
    cookies = browser_cookie3.chrome(domain_name="bilibili.com")
    
    # 创建临时文件，写cookies.txt格式
    tmp = tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.txt')
    for cookie in cookies:
        tmp.write(
            f"{cookie.domain}\t"
            f"{'TRUE' if cookie.domain.startswith('.') else 'FALSE'}\t"
            f"{cookie.path}\t"
            f"{'TRUE' if cookie.secure else 'FALSE'}\t"
            f"{int(cookie.expires) if cookie.expires else '0'}\t"
            f"{cookie.name}\t"
            f"{cookie.value}\n"
        )
    tmp.flush()
    tmp.close()
    time.sleep(5)
    safe_print(f"\nCOOKIE信息已保存到临时文件\n")
    
    return tmp.name


# ========== 下载视频包裹函数 ==========
def order1():
    # 字母映射到清晰度
    quality_map = {
        'a': 'dash-flv720-AVC',        # 720p
        'b': 'dash-flv-AVC',           # 1080p
        'c': 'dash-flv_p60-AVC',       # 1080p(60fps)
        'd': 'dash-hdflv2_4k-HEVC',    # 4k
        # 可以根据实际支持的格式添加更多
    }
    with open(check_file, "r") as file:
        c_list = file.readlines()
        c_set = set(c_list)

    # 过滤掉已经下载过的 BV
    filtered_list = [bvid for bvid in id_list if bvid not in c_set]

    print(f"共 {len(id_list)} 个待下载，已下载 {len(id_list) - len(filtered_list)} 个，剩余 {len(filtered_list)} 个\n")

    if not len(filtered_list) == 0:
        choice3 = input("请选择清晰度: a:720p, b:1080p, c:1080p(60fps), d:4k. 默认 720p : ").strip().lower()
        quality = quality_map.get(choice3, 'dash-flv720-AVC')  # 默认720p
        print()

        download_video_by_url(filtered_list, quality)

    else:
        print(f"无需下载视频\n")


# ========== 爬取信息包裹函数 ==========
def order2():
    new_wb = Workbook()
    new_ws = new_wb.active
    new_ws.append(
        ["标题", "链接", "up主", "up主id", "精确播放数", "历史累计弹幕数", "点赞数", "投硬币枚数", "收藏人数", "转发人数",
        "发布时间", "视频时长(秒)", "视频简介", "作者简介", "标签", "视频aid"])

    extract_video_info(id_list, new_wb, new_ws)  

    # 读取 xlsx 文件
    df = pd.read_excel(ioput_file, engine='openpyxl')  # 需要 openpyxl 库

    # 保存为 CSV
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"视频信息已处理 {output_file}")




# ========== 主逻辑 ==========
if __name__ == "__main__":
    
    stop_event = threading.Event()
    t = threading.Thread(target=loading_dots, args=(stop_event, "正在读取COOKIE，请稍等"))
    t.start()  # 启动动画线程

    # 创建临时文件储存cookie
    cookie_file_path = get_bilibili_cookies() # 可每次手动登录更新文件（不安全），方法：https://blog.csdn.net/qq_28821897/article/details/132002110

    # 任务完成，停止动画
    stop_event.set()
    t.join()

    # 询问是否下载视频
    choice1 = input("是否下载视频？[y/N] ：").strip().lower()
    download_video = choice1 == 'y'

    # 询问是否爬取视频信息
    choice2 = input("是否爬取视频信息？[y/N] ：").strip().lower()
    crawl_info = choice2 == 'y'

    print()

    with open(input_file, "r") as file:
         id_list = file.readlines()

    if download_video and crawl_info:
        print("执行：下载视频 + 爬取信息\n")
        order1()
        order2()


    elif download_video and not crawl_info:
        print("执行：只下载视频\n")
        order1()


    elif not download_video and crawl_info:
        print("执行：只爬取信息\n")
        order2()

    else:
        print("未选择任何操作\n")


    # 清理 cookie 文件
    if os.path.exists(cookie_file_path):
        os.remove(cookie_file_path)
        print()
        print("临时 cookie 文件已删除")
