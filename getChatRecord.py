import time
import mss
import os
import cv2
import pyautogui
import pytesseract
import numpy as np
import json
from datetime import datetime
from processImage import getMask
from PIL import Image, ImageGrab, ImageEnhance
pyautogui.FAILSAFE = True

# print('begin...')
# time.sleep(3)
# print('go!')
# # pyautogui.scroll(40)
# for i in range(10):
#     pyautogui.scroll(35)  # 向上滚动 100 单位
#     time.sleep(3)
# pyautogui.move(100, 0, duration=0)

# pyautogui.mouseDown(button='left')
# time.sleep(0.5)
# pyautogui.mouseUp(button='left') 
# pyautogui.scroll(30)

# import pytesseract
# from PIL import Image

# # 加载图片
# image = Image.open('example.png')

# # 使用 pytesseract 进行 OCR 识别
# text = pytesseract.image_to_string(image)

# # 输出识别到的文字
# print(text)
x1, y1 = 936, 198
x2, y2 = 1177, 596
region = (x1, y1, x2, y2)  # 截取从 (100, 200) 到 (900, 800) 的区域

# with mss.mss() as sct:
#     screenshot = sct.grab(region)
#     screenshot = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
# new_size = (screenshot.width * 2, screenshot.height * 2)
# high_res_screenshot = screenshot.resize(new_size, Image.ANTIALIAS)
# while True:
#     print(pyautogui.position())

if __name__ == '__main__':
    print('begin...')
    time.sleep(3)
    print('go!')
    position = pyautogui.position()
    current_time = datetime.now()
    if os.path.exists('data.json') and False:
        with open('data.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    else:
        results = []
    count = 0
    while True:
        count += 1
        if pyautogui.position() != position:
            break
        pyautogui.scroll(35)  # 向上滚动 100 单位
        with mss.mss() as sct:
            screenshot = sct.grab(region)
            screenshot = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
            try:
                result, current_time = getMask(screenshot, current_time)
                if result and result[-1] == result[0]:
                    result = result[: -1]
                result = result.reverse()
                results = result + results
            except Exception as e:
                with open("data.json", "w", encoding="utf-8") as json_file:
                    json.dump(results, json_file, ensure_ascii=False, indent=4)
                print(count)
        if count % 200 == 0:
            with open("data.json", "w", encoding="utf-8") as json_file:
                json.dump(results, json_file, ensure_ascii=False, indent=4)
            print('{} / 78700 processing...'.format(count))
    with open("data.json", "w", encoding="utf-8") as json_file:
        json.dump(results, json_file, ensure_ascii=False, indent=4)
    print(count)