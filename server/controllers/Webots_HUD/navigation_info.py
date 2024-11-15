# -*- coding: utf-8 -*-
"""
Created on Wed Aug  9 15:01:48 2023

@author: Tian2
"""
import arrow_draw
from PIL import Image, ImageDraw, ImageFont

def navigation_info_left(draw, width, height, text, font_path="arial.ttf", font_size=10):
    # 加载字体
    font = ImageFont.truetype(font_path, font_size)
    
    # 计算文本大小以确定位置
    text_width, text_height = draw.textsize(text, font=font)
    
    # 创建新的图像来绘制文本
    text_image = Image.new("RGBA", (text_width, text_height), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_image)
    
    # 在新图像上绘制文本
    text_draw.text((0, 0), text, font=font, fill=(255, 255, 255))

    angle=7


    # 旋转新图像
    rotated_text_image = text_image.rotate(-angle, resample=Image.BICUBIC, expand=True)
    
    offset_x = -78  # 可以根据需要调整此偏移量
    offset_y = -50   # 根据文本高度和箭头的位置调整此偏移量

    middle_x = width // 2 + offset_x
    middle_y = height // 2 + offset_y

    rotated_width, rotated_height = rotated_text_image.size
    position = (middle_x - rotated_width // 2, middle_y - rotated_height)

    # 使用旋转后的文本图像
    draw.bitmap(position, rotated_text_image, fill=(255, 255, 255))
    
    
def navigation_info_up(draw, width, height, text, font_path="arial.ttf", font_size=9):
    # 加载字体
    font = ImageFont.truetype(font_path, font_size)
    
    # 计算文本大小以确定位置
    text_width, text_height = draw.textsize(text, font=font)
    
    # 创建新的图像来绘制文本
    text_image = Image.new("RGBA", (text_width, text_height), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_image)
    
    # 在新图像上绘制文本
    text_draw.text((0, 0), text, font=font, fill=(255, 255, 255))

    angle=3


    # 旋转新图像
    rotated_text_image = text_image.rotate(-angle, resample=Image.BICUBIC, expand=True)
    
    offset_x = -78  # 可以根据需要调整此偏移量
    offset_y = -50   # 根据文本高度和箭头的位置调整此偏移量

    middle_x = width // 2 + offset_x
    middle_y = height // 2 + offset_y

    rotated_width, rotated_height = rotated_text_image.size
    position = (middle_x - rotated_width // 2, middle_y - rotated_height)

    # 使用旋转后的文本图像
    draw.bitmap(position, rotated_text_image, fill=(255, 255, 255))    
    
    
def navigation_info_right(draw, width, height, text, font_path="arial.ttf", font_size=9):
    # 加载字体
    font = ImageFont.truetype(font_path, font_size)
    
    # 计算文本大小以确定位置
    text_width, text_height = draw.textsize(text, font=font)
    
    # 创建新的图像来绘制文本
    text_image = Image.new("RGBA", (text_width, text_height), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_image)
    
    # 在新图像上绘制文本
    text_draw.text((0, 0), text, font=font, fill=(255, 255, 255))

    angle=3


    # 旋转新图像
    rotated_text_image = text_image.rotate(-angle, resample=Image.BICUBIC, expand=True)
    
    offset_x = -78  # 可以根据需要调整此偏移量
    offset_y = -50   # 根据文本高度和箭头的位置调整此偏移量

    middle_x = width // 2 + offset_x
    middle_y = height // 2 + offset_y

    rotated_width, rotated_height = rotated_text_image.size
    position = (middle_x - rotated_width // 2, middle_y - rotated_height)

    # 使用旋转后的文本图像
    draw.bitmap(position, rotated_text_image, fill=(255, 255, 255))    
    
'''
# 示例
image = Image.new("RGB", (300, 300), (0, 0, 0))
draw = ImageDraw.Draw(image)
arrow_draw.arrow_left(draw, 300, 300)
navigation_info(draw, 300, 300, "1.1km")
image.show()
'''