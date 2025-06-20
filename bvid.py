from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time, os


log_save_path = "./log/"
output_path = "./output/"

output_file = log_save_path + "download_list.log"

# 创建不存在的目录
os.makedirs(log_save_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)

def write_bvids_to_txt(filename, bv_list):
    # 确保bvid文件夹存在，如果不存在则创建
    os.makedirs('bvid', exist_ok=True)
    
    # 拼接完整的文件路径
    filepath = os.path.join('bvid', filename)

    with open(filepath, 'a', encoding='utf-8') as f:
        for bvid in bv_list:
            if bvid != "cheese":
                f.write(bvid + '\n')  # 每行写一个BV号


def spider_bvid(keyword):
    """
    利用seleniume获取搜索结果的bvid，供给后续程序使用
    :param keyword: 搜索关键词
    :return: 生成去重的output_filename = f'{keyword}BV号.txt'
    """
    # 保存的文件名
    input_filename = f'{keyword}BV号.log'
    

    print(f"爬虫,启动!")

    # 启动爬虫
    options = Options()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/120.0.0.0 Safari/537.36")
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    browser = webdriver.Chrome(options=options)  # 设置无界面爬虫
    browser.set_window_size(1400, 900)  # 设置全屏，注意把窗口设置太小的话可能导致有些button无法点击
    browser.get('https://bilibili.com')
    # 刷新一下，防止搜索button被登录弹框遮住
    browser.refresh()
    print("============成功进入B站首页！！！===========")

    input = browser.find_element(By.CLASS_NAME, 'nav-search-input')
    button = browser.find_element(By.CLASS_NAME, 'nav-search-btn')
 
    # 输入关键词并点击搜索
    input.send_keys(keyword)
    button.click()
    print(f'==========成功搜索{keyword}相关内容==========')

    # 设置窗口
    all_h = browser.window_handles
    browser.switch_to.window(all_h[1])
 
    # B站最多显示34页
    total_page = 34
 
    for i in range(0, total_page):
        # url 需要根据不同关键词进行调整内容！！！
        # 这里的url需要自己先搜索一下然后复制网址进来

        if i == 1:
            print(f"跳过骨架屏\n")
            continue  # 为骨架屏，直接跳过这一轮，不执行下面代码

        url = (f"https://search.bilibili.com/all?keyword={keyword}"
               f"&from_source=webtop_search&spm_id_from=333.1007&search_source=5&page={i}")

        if i == 0 :
            print(f"===========正在尝试获取第{i + 1}页网页内容===========")
            print(f"===========本次的url为：{url}===========")
        else :
            print(f"===========正在尝试获取第{i}页网页内容===========")
            print(f"===========本次的url为：{url}===========")

        browser.get(url)
        # 这里请求访问网页的时间也比较久(可能因为我是macos)，所以是否需要等待因设备而异
        # 取消刷新并长时间休眠爬虫以避免爬取太快导致爬虫抓取到js动态加载源码
        # browser.refresh()
        print('正在等待页面加载：3')
        time.sleep(1)
        print('正在等待页面加载：2')
        time.sleep(1)
        print('正在等待页面加载：1')
        time.sleep(2)


        # 直接分析网页
        html = browser.page_source
        # print("网页源码" + html) 用于判断是否获取成功
        soup = BeautifulSoup(html, 'lxml')
        infos = soup.find_all(class_='bili-video-card')
        bv_id_list = []
        for info in infos:
            # 只定位视频链接
            href = info.find('a').get('href')
            # 拆分
            split_url_data = href.split('/')
            # 利用循环删除拆分出现的空白
            for element in split_url_data:
                if element == '':
                    split_url_data.remove(element)
            # 打印检验内容
            # print(split_url_data)
            # 获取bvid
            bvid = split_url_data[2]
 
            # 利用if语句直接去重
            if bvid not in bv_id_list:
                bv_id_list.append(bvid)

            
        # bv_id_list 是BV号列表，input_filename 是目标文件名
        write_bvids_to_txt(input_filename, bv_id_list)

        # 输出提示进度
        print('写入文件成功')
        if i == 0 :
            print("===========成功获取第" + str(i + 1) + "次===========\n")
        else :
            print("===========成功获取第" + str(i) + "次===========\n")
        time.sleep(1)
        i += 1
 
    # 退出爬虫
    browser.quit()
 
    # 打印信息显示是否成功
    print(f'==========爬取完成。退出爬虫==========')


if __name__ == "__main__":
    # 打开要爬取的关键词列表文件
    with open("keywords.log", "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f 
                   if line.strip() and not line.startswith("#")]

    # 循环处理每个关键词
    for keyword in keywords:
        print(f"开始爬取关键词: {keyword}")
        spider_bvid(keyword)
        print(f"已完成关键词: {keyword}")

    print("所有关键词处理完毕！")

    folder_path = "./bvid"  # 存放 LOG 的文件夹路径

    # 读取所有 BV 号并去重（仅保留以 "BV" 开头的）
    bv_set = set()
    for filename in os.listdir(folder_path):
        if filename.endswith(".log"):
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()  # 去除首尾空白字符
                    if line.startswith("BV"):  # 仅保留以 "BV" 开头的行
                        bv_set.add(line)

    # 写入新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(bv_set))

    print(f"合并完成，共 {len(bv_set)} 个唯一 BV 号。")
 
 