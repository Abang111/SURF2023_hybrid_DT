# -*- coding: utf-8 -*-
"""
Created on Sun Aug  6 19:00:23 2023

@author: Tian2
"""



def draw_arrow_up(draw, width, height, arrow_length=180, arrow_head_length=60, arrow_head_width=40, handle_width=20):
    offset_x = -50  # 向左移动3个像素
    offset_y = -50  # 向上移动5个像素

    middle_x = width // 2 + offset_x  # 将箭头向左移动offset_x个像素
    middle_y = height // 2 + offset_y  # 将箭头向上移动offset_y个像素
    arrow_tip = middle_y - arrow_length // 2
    arrow_base = middle_y + arrow_length // 2 - arrow_head_length
    
    green_color = (255, 255, 255)  # 绿色
    
    # 使用绿色绘制箭头的杆
    draw.line([(middle_x, arrow_tip + arrow_head_length), (middle_x, arrow_base)], fill=green_color, width=handle_width)
    
    draw.polygon([(middle_x, arrow_tip),
              (middle_x - round(arrow_head_width / 2), arrow_tip + arrow_head_length),
              (middle_x + round(arrow_head_width / 2), arrow_tip + arrow_head_length)], 
              fill=green_color)
    return
    
    
def draw_arrow_right(draw, width, height, arrow_length=16, arrow_head_length=5, arrow_head_width=4, handle_width=2):
    offset_x = -7  # 向左移动
    offset_y = -5  # 向上移动

    middle_x = width // 2 + offset_x  # 将箭头向左移动offset_x个像素
    middle_y = height // 2 + offset_y  # 将箭头向上移动offset_y个像素
    arrow_tip = middle_x + arrow_length // 2  
    arrow_base = middle_x - arrow_length // 2 + arrow_head_length  
    
    green_color = (255,255, 255)  
    
    # 使用绿色绘制箭头的杆
    draw.line([(arrow_tip - arrow_head_length, middle_y), (arrow_base, middle_y)], fill=green_color, width=handle_width)
    
    # 使用绿色绘制箭头的头部
    draw.polygon([(arrow_tip, middle_y),
                  (arrow_tip - arrow_head_length, middle_y - arrow_head_width // 2),
                  (arrow_tip - arrow_head_length, middle_y + arrow_head_width // 2)], 
                  fill=green_color)
    return


def draw_arrow_left(draw, width, height, arrow_length=16, arrow_head_length=5, arrow_head_width=4, handle_width=2):
    offset_x = -5  
    offset_y = -6  # 向下移动

    middle_x = width // 2 + offset_x  # 将箭头向右移动offset_x个像素
    middle_y = height // 2 + offset_y  # 将箭头向下移动offset_y个像素
    arrow_tip = middle_x - arrow_length // 2  # 箭头尖端现在在左侧
    arrow_base = middle_x + arrow_length // 2 - arrow_head_length  # 箭头基部现在在右侧
    
    green_color = (255, 255, 255)  # 绿色
    
    # 使用绿色绘制箭头的杆
    draw.line([(arrow_tip + arrow_head_length, middle_y), (arrow_base, middle_y)], fill=green_color, width=handle_width)
    
    # 使用绿色绘制箭头的头部
    draw.polygon([(arrow_tip, middle_y),
                  (arrow_tip + arrow_head_length, middle_y - arrow_head_width // 2),
                  (arrow_tip + arrow_head_length, middle_y + arrow_head_width // 2)], 
                  fill=green_color)
    return