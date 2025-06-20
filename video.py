import os
import re
import sys
import cv2
import numpy
from moviepy import editor


VIDEO_PATH = './video/'
OUTPUT_PATH = VIDEO_PATH + 'watermark/'
TEMP_VIDEO = 'temp.mp4'

log_save_path = "./log/"
input_file = log_save_path + "video_list.log"
check_file = log_save_path + "watermark_list.log"
 
# 创建不存在的目录
os.makedirs(VIDEO_PATH, exist_ok=True)
os.makedirs(log_save_path, exist_ok=True)

if not os.path.exists(check_file):
    open(check_file, 'a').close()  # 创建空文件

class WatermarkRemover():
 
    def __init__(self, threshold: int, kernel_size: int):
        self.threshold = threshold  # 阈值分割所用阈值
        self.kernel_size = kernel_size  # 膨胀运算核尺寸
 
 
    #根据用户手动选择的ROI（Region of Interest，感兴趣区域）框选水印或字幕位置。
    def select_roi(self, img: numpy.ndarray, hint: str) -> list:
        '''
    框选水印或字幕位置，SPACE或ENTER键退出
    :param img: 显示图片
    :return: 框选区域坐标
    '''
        if img is None:
            print("Error: 输入图像为 None！")
            return []

        # 计算缩放比例，使窗口适合屏幕
        screen_width, screen_height = 1920, 1080  # 可以根据实际情况调整或获取屏幕分辨率
        max_width = screen_width * 0.8
        max_height = screen_height * 0.8
    
        height, width = img.shape[:2]
        scale = min(max_width / width, max_height / height)
    
        # 保持宽高比缩放图像
        resize_img = cv2.resize(img, (int(width * scale), int(height * scale)))
    
        # 显示缩放后的图像
        roi = cv2.selectROI(hint, resize_img, False, False)
        cv2.destroyAllWindows()
    
        # 将ROI坐标转换回原始图像尺寸
        watermark_roi = [
            int(roi[0] / scale),
            int(roi[1] / scale),
            int(roi[2] / scale),
            int(roi[3] / scale)
        ]
        return watermark_roi
 
 
    #对输入的蒙版进行膨胀运算，扩大蒙版的范围
    def dilate_mask(self, mask: numpy.ndarray) -> numpy.ndarray:
 
        '''
    对蒙版进行膨胀运算
    :param mask: 蒙版图片
    :return: 膨胀处理后蒙版
    '''
        kernel = numpy.ones((self.kernel_size, self.kernel_size), numpy.uint8)
        mask = cv2.dilate(mask, kernel)
        return mask
    
    #根据手动选择的ROI区域，在单帧图像中生成水印或字幕的蒙版。
    def generate_single_mask(self, img: numpy.ndarray, roi: list, threshold: int) -> numpy.ndarray:
        '''
    通过手动选择的ROI区域生成单帧图像的水印蒙版
    :param img: 单帧图像
    :param roi: 手动选择区域坐标
    :param threshold: 二值化阈值
    :return: 水印蒙版
    '''
        # 区域无效，程序退出
        if len(roi) != 4:
            print('NULL ROI!')
            sys.exit()
 
        # 复制单帧灰度图像ROI内像素点
        roi_img = numpy.zeros((img.shape[0], img.shape[1]), numpy.uint8)
        start_x, end_x = int(roi[1]), int(roi[1] + roi[3])
        start_y, end_y = int(roi[0]), int(roi[0] + roi[2])
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        roi_img[start_x:end_x, start_y:end_y] = gray[start_x:end_x, start_y:end_y]
 
        # 阈值分割
        _, mask = cv2.threshold(roi_img, threshold, 255, cv2.THRESH_BINARY)
        return mask
 
    #通过截取视频中多帧图像生成多张水印蒙版，并通过逻辑与计算生成最终的水印蒙版
    def generate_watermark_mask(self, video_path: str) -> numpy.ndarray:
        '''
    截取视频中多帧图像生成多张水印蒙版，通过逻辑与计算生成最终水印蒙版
    :param video_path: 视频文件路径
    :return: 水印蒙版
    '''
        print(f"正在分析视频以生成水印蒙版: {video_path}")
        video = cv2.VideoCapture(video_path)
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            print(f"Error: 无法打开视频文件 '{video_path}'！")
            return None

        for _ in range(5):  # 跳过前5帧,避免黑屏
            video.read() 

        success, frame = video.read()
        if not success or frame is None:
            print("Error: 无法读取视频帧！")
            return None


        print("请在弹出的窗口中选择水印区域，按 SPACE 或 ENTER 确认")

        roi = self.select_roi(frame, 'select watermark ROI')
        mask = numpy.ones((frame.shape[0], frame.shape[1]), numpy.uint8)
        mask.fill(255)
 
        step = video.get(cv2.CAP_PROP_FRAME_COUNT) // 5
        index = 0
        while success:
            if index % step == 0:
                mask = cv2.bitwise_and(mask, self.generate_single_mask(frame, roi, self.threshold))
            success, frame = video.read()
            index += 1
        video.release()
        print("水印蒙版分析完成！")

        return self.dilate_mask(mask)
 
    #根据手动选择的ROI区域，在单帧图像中生成字幕的蒙版。
    def generate_subtitle_mask(self, frame: numpy.ndarray, roi: list) -> numpy.ndarray:
        '''
    通过手动选择ROI区域生成单帧图像字幕蒙版
    :param frame: 单帧图像
    :param roi: 手动选择区域坐标
    :return: 字幕蒙版
    '''
        mask = self.generate_single_mask(frame, [0, roi[1], frame.shape[1], roi[3]], self.threshold)  # 仅使用ROI横坐标区域
        return self.dilate_mask(mask)
 
    def inpaint_image(self, img: numpy.ndarray, mask: numpy.ndarray) -> numpy.ndarray:
        '''
    修复图像
    :param img: 单帧图像
    :parma mask: 蒙版
    :return: 修复后图像
    '''
        telea = cv2.inpaint(img, mask, 1, cv2.INPAINT_TELEA)
        return telea
 
 
    def merge_audio(self, input_path: str, output_path: str, temp_path: str):
        '''
    合并音频与处理后视频
    :param input_path: 原视频文件路径
    :param output_path: 封装音视频后文件路径
    :param temp_path: 无声视频文件路径
    '''
        print(f"正在合并音频: {input_path} -> {output_path}")

        flag = False

        try:
            with editor.VideoFileClip(input_path) as video:
                audio = video.audio
                with editor.VideoFileClip(temp_path) as opencv_video:
                    clip = opencv_video.set_audio(audio)
                    clip.to_videofile(output_path)
            print(f"音视频合并成功: {output_path}")
            
            flag = True

        except Exception as e:
            print(f"合并音频失败: {e}")

        return flag


    def remove_video_watermark(self, id_list, filtered_list):
        '''
    去除视频水印
    '''
        if not os.path.exists(OUTPUT_PATH):
            os.makedirs(OUTPUT_PATH)
            print(f"创建输出目录: {OUTPUT_PATH}")
        
        print(f"\n共 {len(id_list)} 个待清除水印，无水印 {len(id_list) - len(filtered_list)} 个，剩余 {len(filtered_list)} 个\n")

        if len(filtered_list) == 0:
           print(f"无需清除水印\n")
           return None

        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv')  # 支持的视频格式

        filenames = sorted(
                    [os.path.join(VIDEO_PATH, i) 
                    for i in os.listdir(VIDEO_PATH)
                    if i.lower().endswith(valid_extensions)  # 只处理视频文件
                    ], 
                    key=lambda x: os.path.getctime(x) # 先来后到
        )

        if not filenames:
            print("Error: 未找到视频文件！请检查路径：", VIDEO_PATH)
            sys.exit()

        print(f"找到 {len(filenames)} 个视频文件:")
        for name in filenames:
            print(f"  - {name}")
        mask = None
        
        skip_count = len(id_list) - len(filtered_list)

        skip_indices = range(0, skip_count)  # 跳过前skip_count个

        for i, name in enumerate(filenames):
            if i in skip_indices:
                continue  # 跳过本次循环

            print(f"\n正在处理视频 ({i+1}/{len(filenames)}): {name}")
  
            # 生成水印蒙版
            mask = self.generate_watermark_mask(name)
            if mask is None:
                print(f"无法为视频 {name} 生成水印遮罩，跳过")
                continue

            # 创建待写入文件对象
            video = cv2.VideoCapture(name)
            if not video.isOpened():
                print(f"Error: 无法打开视频文件 '{name}'！")
                continue

            fps = video.get(cv2.CAP_PROP_FPS)
            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            size = (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))

            print(f"视频信息: {fps} FPS, {frame_count} 帧, 分辨率: {size[0]}x{size[1]}")

            video_writer = cv2.VideoWriter(TEMP_VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
            if not video_writer.isOpened():
                print(f"Error: 无法创建输出视频文件 '{TEMP_VIDEO}'！")
                video.release()
                continue

 
            # 逐帧处理图像
            success, frame = video.read()
 
            while success:
                frame = self.inpaint_image(frame, mask)
                video_writer.write(frame)
                success, frame = video.read()
 
            video.release()
            video_writer.release()
 
            # 封装视频
            (_, filename) = os.path.split(name)
            output_path = os.path.join(OUTPUT_PATH, filename.split('.')[0] + '_no_watermark.mp4')  # 输出文件路径
            print(f"正在合并音频...")

            flag = self.merge_audio(name, output_path, TEMP_VIDEO)
            # === 在成功合并后追加 BV 号到记录文件 ===
            if flag:
                with open(check_file, "a", encoding="utf-8") as f:
                    f.write(f"{self.extract_bvid(name)}\n")

            print(f"输出视频已保存: {output_path}")
 
        if os.path.exists(TEMP_VIDEO):
            os.remove(TEMP_VIDEO)
            print("临时文件已清理")

 
    def remove_video_subtitle(self):
        '''
    去除视频字幕
    '''
        if not os.path.exists(OUTPUT_PATH):
            os.makedirs(OUTPUT_PATH)
        
        valid_extensions = ('.mp4', '.avi', '.mov', '.mkv')  # 支持的视频格式

        filenames = [os.path.join(VIDEO_PATH, i)
                    for i in os.listdir(VIDEO_PATH)
                    if i.lower().endswith(valid_extensions)  # 只处理视频文件
                    ]
        if not filenames:
            print("Error: 未找到视频文件！请检查路径：", VIDEO_PATH)
            sys.exit()
        roi = []
 
        for i, name in enumerate(filenames):
            # 创建待写入文件对象
            video = cv2.VideoCapture(name)
            fps = video.get(cv2.CAP_PROP_FPS)
            size = (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            video_writer = cv2.VideoWriter(TEMP_VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
 
            # 逐帧处理图像
            success, frame = video.read()
            if i == 0:
                roi = self.select_roi(frame, 'select subtitle ROI')
 
            while success:
                mask = self.generate_subtitle_mask(frame, roi)
                frame = self.inpaint_image(frame, mask)
                video_writer.write(frame)
                success, frame = video.read()
 
            video.release()
            video_writer.release()
 
            # 封装视频
            (_, filename) = os.path.split(name)
            output_path = os.path.join(OUTPUT_PATH, filename.split('.')[0] + '_no_sub.mp4')  # 输出文件路径
            self.merge_audio(name, output_path, TEMP_VIDEO)
 
        if os.path.exists(TEMP_VIDEO):
            os.remove(TEMP_VIDEO)
            print("临时文件已清理")
        

    def extract_bvid(self, filename):
        '''
    从文件名提取 BV 号（兼容各种格式）
    支持的格式：
      - "BV1xx411x7xx.mp4"
      - "BV1xx411x7xx_标题.mp4"
      - "前缀_BV1xx411x7xx_后缀.mp4"
    '''
        pattern = re.compile(r'(BV[0-9A-Za-z]{10})')  # BV号固定11位（BV+10位字符）
        match = pattern.search(filename)
        return match.group(1) if match else None

 
if __name__ == '__main__':
    sel=input('请选择 1：去水印, 2: 去字幕\n')
    if sel=='1':
        remover = WatermarkRemover(threshold=80, kernel_size=5)

        with open(input_file, "r") as file:
            id_list = file.readlines()

        with open(check_file, "r") as file:
            c_list = file.readlines()
            c_set = set(c_list)

        # 过滤掉已经下载过的 BV
        filtered_list = [bvid for bvid in id_list if bvid not in c_set]

        remover.remove_video_watermark(id_list, filtered_list)

    if sel=='2':
        remover = WatermarkRemover(threshold=80, kernel_size=5)
        remover.remove_video_subtitle()