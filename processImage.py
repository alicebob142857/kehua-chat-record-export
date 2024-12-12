import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import cv2
import pytesseract
from datetime import datetime, timedelta
import re

def getDistribution(img):
    gray_img = img.convert('L')
    img_array = np.array(gray_img)
    plt.figure(figsize=(10, 6))
    plt.hist(img_array.flatten(), bins=256, range=(0, 256), density=True, color='gray', alpha=0.7)
    plt.title('Histogram of Grayscale Values')
    plt.xlabel('Pixel Intensity (0-255)')
    plt.ylabel('Frequency')
    plt.grid(True)
    plt.show()

def getNumber(l):
    times = 1
    res = 0
    for i in l[::-1]:
        res += int(i) * times
        times *= 10
    return res

def isValidTime(l):
    flag = (getNumber(l[-2:]) < 60)
    if len(l) >= 4:
        flag = flag and (getNumber(l[-4: -2]) < 24)
    if len(l) >= 6:
        flag = flag and (getNumber(l[-6: -4]) < 32)
    if len(l) >= 8:
        flag = flag and (getNumber(l[-8: -6]) < 13)

def getDate(result):
    full_string = ''.join(result['text'])
    if full_string:
        for i in range(len(result['text'])):
            text = result['text'][i]
            if text.strip():  # 如果文本不为空
                y = result['top'][i]
        today = datetime.today()
        numbers = re.findall(r'\d', full_string)
        if not isValidTime(numbers):
            return None, 100000
        if len(numbers) == 12:
            date = datetime(getNumber(numbers[:4]), getNumber(numbers[4:6]), getNumber(numbers[6:8]), getNumber(numbers[8:10]), getNumber(numbers[10:12]), 0)
            return date, y
        elif len(numbers) == 8:
            data = datetime(today.year, getNumber(numbers[:2]), getNumber(numbers[2:4]), getNumber(numbers[4:6]), getNumber(numbers[6:8]), 0)
            return date, y
        elif len(numbers) == 4:
            weekday_map = {
                "星期一": 0,
                "星期二": 1,
                "星期三": 2,
                "星期四": 3,
                "星期五": 4,
                "星期六": 5,
                "星期天": 6
            }
            # 是否有星期信息
            for weekday_chinese, weekday_num in weekday_map.items():
                if weekday_chinese in full_string:
                    days_diff = (today.weekday() + 7 - weekday_num) % 7  # 计算与今天的差值
                    last_weekday = today - timedelta(days=days_diff)
                    return last_weekday.replace(hour=getNumber(numbers[:2]), minute=getNumber(numbers[2:4]), second=0), y
            return datetime(today.year, today.month, today.day, getNumber(numbers[:2]), getNumber(numbers[2:4]), 0), y

        else:
            return None, 100000
    return None, 100000

def getMask(img, initial_time):
    lower_blue = 230
    upper_blue = 240
    lower_gray = 120
    upper_gray = 130
    custom_config = r'--oem 3 --psm 6'

    gray_img = img.convert('L')
    img_array = np.array(gray_img)
    blue_mask = cv2.inRange(img_array, lower_blue, upper_blue)
    gray_mask = cv2.inRange(img_array, lower_gray, upper_gray)
    combined_mask = cv2.bitwise_or(blue_mask, gray_mask)
    blank_image = img_array.copy()
    # 轮廓检测
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if cv2.contourArea(contour) > 500 and h >= 45:
            lower_x = y + 10
            upper_x = lower_x + h - 15
            lower_y = x + 10
            upper_y = lower_y + w - 15
            image_block = img_array[lower_x: upper_x, lower_y: upper_y]
            blank_image[y-min(5, abs(y)): y+h+min(5, abs(y+h-blank_image.shape[0])), x-min(5, abs(x)): x+w+min(5, abs(x+w-blank_image.shape[1]))] = 255
            if image_block.shape[0] > 5 and image_block.shape[1] > 5 and image_block[5, 5] > 150:
                # 蓝色
                _, image_block = cv2.threshold(image_block, 100, 255, cv2.THRESH_BINARY)
                text = pytesseract.image_to_string(image_block, lang='chi_sim', config=custom_config)
                text = text.replace("\n", "")
                output.append({'speaker': 'kk', 'text': text, 'time': y})
            elif image_block.shape[0] > 5 and image_block.shape[1] > 5 and image_block[5, 5] <= 150:
                image_block = 255 - image_block
                _, image_block = cv2.threshold(image_block, 45, 255, cv2.THRESH_BINARY)
                text = pytesseract.image_to_string(image_block, lang='chi_sim', config=custom_config)
                text = text.replace("\n", "")
                output.append({'speaker': 'zz', 'text': text, 'time': y})
    result = pytesseract.image_to_data(blank_image, lang='chi_sim', config=custom_config, output_type=pytesseract.Output.DICT)
    date, y = getDate(result)
    for item in output:
        if item['time'] < y:
            item['time'] = str(initial_time)
        else:
            item['time'] = str(date)
    if output:
        return output, output[-1]['time']
    else:
        return [], initial_time

    # Image.fromarray(blank_image).show()
                

if __name__ == '__main__':
    img = Image.open('mss_screenshot.png')
    res, _ = getMask(img, datetime.now())
    print(_)