
from PIL import Image, ImageDraw
#前车
def car_arrow_left(draw, width, height, offset_x=160, offset_y=120, vertical_length=5, horizontal_length=5, arrow_head_length=6, arrow_head_width=10,
               handle_width=2, smooth_gap=3):


    middle_x = width // 2 + offset_x
    middle_y = height // 2 + offset_y

    set_color = (255, 255, 255)



    # 绘制水平线
    draw.line([(middle_x, middle_y - vertical_length + smooth_gap),
               (middle_x - horizontal_length + arrow_head_length, middle_y - vertical_length)], fill=set_color,
              width=handle_width)

    # 绘制箭头的头部
    draw.polygon([(middle_x - horizontal_length, middle_y - vertical_length),
                  (
                  middle_x - horizontal_length + arrow_head_length, middle_y - vertical_length - arrow_head_width // 2),
                  (middle_x - horizontal_length + arrow_head_length,
                   middle_y - vertical_length + arrow_head_width // 2)],
                 fill=set_color)

def car_arrow_right(draw, width, height, offset_x=160, offset_y=120,vertical_length=5, horizontal_length=5, arrow_head_length=6,
                    arrow_head_width=10, handle_width=2, smooth_gap=3):


    middle_x = width // 2 + offset_x
    middle_y = height // 2 + offset_y

    set_color = (255, 255, 255)

    # 绘制水平线，但不绘制与垂直线交汇的部分
    draw.line([(middle_x, middle_y - vertical_length),
                   (middle_x + horizontal_length - arrow_head_length, middle_y - vertical_length)], fill=set_color,
                  width=handle_width)


    # 绘制箭头的头部
    draw.polygon([(middle_x + horizontal_length, middle_y - vertical_length),
                      (middle_x + horizontal_length - arrow_head_length,
                       middle_y - vertical_length - arrow_head_width // 2),
                      (middle_x + horizontal_length - arrow_head_length,
                       middle_y - vertical_length + arrow_head_width // 2)],
                     fill=set_color)
