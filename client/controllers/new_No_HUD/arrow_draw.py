# -*- coding: utf-8 -*-
"""
Created on Wed Aug  9 00:15:03 2023

@author: Tian2
"""



from PIL import Image, ImageDraw

def arrow_left(draw, width, height, vertical_length=20, horizontal_length=20, arrow_head_length=10, arrow_head_width=6, handle_width=2, smooth_gap=3):

    offset_x = -60  
    offset_y = -20  

    middle_x = width // 2 + offset_x  
    middle_y = height // 2 + offset_y  
    
    set_color = (255, 255, 255)  
    
    # 绘制垂直线
    draw.line([(middle_x, middle_y), (middle_x, middle_y - vertical_length + smooth_gap)], fill=set_color, width=handle_width)
    
    # 绘制水平线
    draw.line([(middle_x, middle_y - vertical_length + smooth_gap), (middle_x - horizontal_length + arrow_head_length, middle_y - vertical_length)], fill=set_color, width=handle_width)
    
    # 绘制箭头的头部
    draw.polygon([(middle_x - horizontal_length, middle_y - vertical_length),
                  (middle_x - horizontal_length + arrow_head_length, middle_y - vertical_length - arrow_head_width // 2),
                  (middle_x - horizontal_length + arrow_head_length, middle_y - vertical_length + arrow_head_width // 2)], 
                  fill=set_color)
    
    
def arrow_right(draw, width, height, vertical_length=20, horizontal_length=20, arrow_head_length=10, arrow_head_width=6, handle_width=2, smooth_gap=3):

    offset_x = -90  
    offset_y = -20  

    middle_x = width // 2 + offset_x  
    middle_y = height // 2 + offset_y  
    
    set_color = (255, 255, 255)  
    
    curve_distance = smooth_gap  # 贝塞尔曲线控制点与直线交点的距离

    # 绘制垂直线，但不绘制与水平线交汇的部分
    draw.line([(middle_x, middle_y), (middle_x, middle_y - vertical_length + curve_distance)], fill=set_color, width=handle_width)
    
    # 绘制水平线，但不绘制与垂直线交汇的部分
    draw.line([(middle_x, middle_y - vertical_length), (middle_x + horizontal_length - arrow_head_length, middle_y - vertical_length)], fill=set_color, width=handle_width)
    
    # 使用贝塞尔曲线连接垂直和水平线
    draw.line([(middle_x, middle_y - vertical_length + curve_distance), (middle_x + curve_distance, middle_y - vertical_length)], fill=set_color, width=handle_width)
    
    # 绘制箭头的头部
    draw.polygon([(middle_x + horizontal_length, middle_y - vertical_length),
                  (middle_x + horizontal_length - arrow_head_length, middle_y - vertical_length - arrow_head_width // 2),
                  (middle_x + horizontal_length - arrow_head_length, middle_y - vertical_length + arrow_head_width // 2)],
                  fill=set_color)
    
    
def arrow_up(draw, width, height, arrow_length=26, arrow_head_length=10, arrow_head_width=8, handle_width=3, handle_gap=3):
    offset_x = -80
    offset_y = -48

    middle_x = width // 2 + offset_x
    middle_y = height // 2 + offset_y
    arrow_tip = middle_y - arrow_length // 2
    arrow_base = middle_y + arrow_length // 2
    handle_start = arrow_tip + arrow_head_length
    
    set_color = (255, 255, 255)  # 绿色
    
    # 使用绿色绘制箭头的杆
    draw.line([(middle_x, handle_start + handle_gap), (middle_x, arrow_base)], fill=set_color, width=handle_width)
    
    # 箭头的剑柄
    draw.line([(middle_x - arrow_head_width // 2, handle_start), (middle_x + arrow_head_width // 2, handle_start)], fill=set_color, width=handle_width)
    
    # 绘制箭头的头部
    draw.polygon([(middle_x, arrow_tip),
                  (middle_x - round(arrow_head_width / 2), arrow_tip + arrow_head_length),
                  (middle_x + round(arrow_head_width / 2), arrow_tip + arrow_head_length)], 
                  fill=set_color)



'''
#以下是一个画板测试模块，作者为Abang111，初步把默认显示屏分辨率作为1024*1024
    
# 创建一个新图像
img_width = 300
img_height = 300
img = Image.new('RGBA', (img_width, img_height), color=(0, 0, 0, 255))
draw = ImageDraw.Draw(img)

# 在图像上绘制左转箭头
arrow_right(draw, img_width, img_height)

# 显示图像
img.show()

'''