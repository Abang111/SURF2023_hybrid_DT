
from controller import Display
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from vehicle import Driver
import arrow_draw
import traci
import time

import car_info
import navigation_info
import car_arrow_draw
import speed_limit
from PIL import Image, ImageDraw, ImageFont



#robot = Robot()
driver = Driver()

sensorsNames = [
    "front",
    "front right 0",
    "front right 1",
    "front right 2",
    "front left 0",
    "front left 1",
    "front left 2",
    "rear",
    "rear left",
    "rear right",
    "right",
    "left"
   ]
sensors = {}
for name in sensorsNames:
    sensors[name] = driver.getDevice("distance sensor " + name)
    sensors[name].enable(10)
currentLane = 1
vehicle_id = "your_vehicle_id"

timestep = int(driver.getBasicTimeStep())
hud_display = driver.getDevice("HUD_DISPLAY")
hud_display_width = hud_display.getWidth()
hud_display_height = hud_display.getHeight()

print(hud_display_width)
print(hud_display_height/2)


#aaaaa=driver.getCurrentSpeed()
#print(aaaaa)

def is_vehicle_on_side(side):
    """Check (using the 3 appropriated front distance sensors) if there is a car in front."""
    for i in range(3):
        name = "front " + side + " " + str(i)
        if sensors[name].getValue() > 0.8 * sensors[name].getMaxValue():
            return True
    return False
def draw_hud(recieve_speed):

    # 使用Pillow创建一个新的图像
    img = Image.new('RGBA', (hud_display_width, hud_display_height), color=(0, 0, 0, 0))
    # 为HUD的背景添加半透明的黑色图层
    alpha_layer = Image.new('RGBA', (hud_display_width, hud_display_height), (0, 0, 0, 128))  # 可以调整最后一个参数来控制透明度
    img = Image.alpha_composite(img, alpha_layer)
    
    
    # 设置文本颜色和大小
    font_size = 10
    font = ImageFont.truetype("C:/Users/guoka/Desktop/my_project/font/Pixelarial11/PIXEAB__.TTF", font_size)


    #显示速度信息
    recieve_speed = max(0, recieve_speed)
    speed_text = "{:.0f}".format(recieve_speed)

    x_position = 127
    y_position = 220

    # 阴影的颜色和偏移
    shadow_color = (10, 10, 10)  #阴影背景
    shadow_offset = (1, 1)

    # 创建只有阴影的图像
    shadow_img = Image.new('RGBA', (hud_display_width, hud_display_height), color=(0, 0, 0, 255))
    shadow_draw = ImageDraw.Draw(shadow_img)

    # 在此图像上绘制阴影文本
    draw = ImageDraw.Draw(img)
    
    draw.text((x_position, y_position), speed_text, font=font, fill=(0,255,0))
    # 获取文本的大小
    text_width, text_height = draw.textsize(speed_text, font=font)
    # 计算矩形的坐标
    rect_left = x_position - 3  # 为文本留出一些边距
    rect_top = y_position - 3
    rect_right = x_position + text_width + 1.5
    rect_bottom = y_position + text_height + 3
    # 绘制灰色背景矩形
    draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(200, 200, 200))

    # 再绘制文本的轮廓
    outline_color = (0, 0, 0)  # color for outline
    outline_width = 1  # Maintain the outline width to make it cleaner
    for x_offset in range(-outline_width, outline_width+1):
        for y_offset in range(-outline_width, outline_width+1):
            draw.text((x_position + x_offset, y_position + y_offset), speed_text, font=font, fill=outline_color)

    # 最后绘制主文本
    draw.text((x_position, y_position), speed_text, font=font, fill=(0,255, 0))
    
    # 添加旋转变换
    # angle = 5
    # img = img.rotate(-angle, resample=Image.BICUBIC, expand=False)
    
    #为了绘制箭头，不受旋转影响，再次获取图像上下文！
    draw= ImageDraw.Draw(img)  # 由于图像已经旋转，我们需要重新获取绘图上下文
    
    # 添加限速标志
    limit = traci.vehicle.getAllowedSpeed  # 假设限速为50km/h
    speed_limit.draw_speed_limit(img, limit) #限速标识
    
    if arrow_visible:
        arrow_draw.arrow_right(draw, hud_display_width, hud_display_height) #生成箭头代码
        navigation_info.navigation_info_right(draw, hud_display_width, hud_display_height, "3.4km")

    #绘制车况示意图
    #本车
    rect_left = 87 
    rect_top = 190
    rect_right = 97
    rect_bottom = 200
    draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    #前车
    F_distance = int(sensors["front"].getValue())
    if F_distance < 3:
       rect_left = 84
       rect_top = 160
       rect_right = 100
       rect_bottom = 175
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(255, 0, 0))
    #后车
    rect_left = 84  
    rect_top = 215
    rect_right = 100
    rect_bottom = 230


    draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], outline=(0, 0, 255))


    frontRange = sensors["front"].getMaxValue()
    frontDistance = sensors["front"].getValue()
    if sensors["front left 1"].getValue() < 8 :
        # 左前
        rect_left = 104
        rect_top = 160  # 根据 distance_left 调整正方形的 top
        rect_right = 115
        rect_bottom = 175  # 根据 distance_left 调整正方形的 bottom
        draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    if sensors["front right 1"].getValue() < 8 :
      #右前
        rect_left = 64
        rect_top = 160  # 根据 distance_left 调整正方形的 top
        rect_right = 75
        rect_bottom = 175  # 根据 distance_left 调整正方形的 bottom
        draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))

    if sensors["rear left"].getValue() < 8 :
        # 右后
        rect_left = 104
        rect_top = 215  # 根据 distance_left 调整正方形的 top
        rect_right = 115
        rect_bottom = 230  # 根据 distance_left 调整正方形的 bottom
        draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    if sensors["rear right"].getValue() < 8:
        # 左后
        rect_left = 64
        rect_top = 215  # 根据 distance_left 调整正方形的 top
        rect_right = 75
        rect_bottom = 230  # 根据 distance_left 调整正方形的 bottom
        draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))

    if sensors["right"].getValue() < 3:
        # 右车
        rect_left =  104
        rect_top = 190  # 根据 distance_left 调整正方形的 top
        rect_right = 115
        rect_bottom = 200  # 根据 distance_left 调整正方形的 bottom
        draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    if sensors["left"].getValue() < 3:
        # 左车
        rect_left = 64
        rect_top = 190  # 根据 distance_left 调整正方形的 top
        rect_right = 75
        rect_bottom = 200  # 根据 distance_left 调整正方形的 bottom
        draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    #后车车距
    last_distance = 0
    R_distance = int(sensors["rear"].getValue())
    if R_distance < 10:
       car_info.draw_distance(img, R_distance)
    # 后车速度信息

       x_offset = 85
       y_offset = 215
       time_interval = 1  # 时间间隔为 1 秒
       speed = int(abs((last_distance - R_distance) / time_interval))
       last_distance = R_distance
       car_info.draw_speed(img, speed, x_offset, y_offset)
    # 前车车距


    # 将图像转换为R
    img_rgb = img.convert('RGB')


    # 使用numpy转换Pillow图像
    img_rgb = img_rgb.transpose(Image.FLIP_TOP_BOTTOM)
    img_rgb = img_rgb.transpose(Image.FLIP_LEFT_RIGHT)
    img_data = np.array(img_rgb)
    img_data_flatten = img_data.tobytes()
#    vertical_offset = hud_display_height - img.height

    # 用转换后的数据创建Webots图像
    hud_display_image = hud_display.imageNew(img_data_flatten, Display.RGB, hud_display_width, hud_display_height)
    hud_display.imagePaste(hud_display_image, 0, 0, False)
    hud_display.imageDelete(hud_display_image)


gps = driver.getDevice("gps")
gps.enable(10)


#camera = driver.getDevice("camera")
#uncomment those lines to enable the camera
#camera.enable(10)
#camera.recognitionEnable(50)

# 在循环外部初始化状态变量
arrow_visible = True
last_toggle_time = 0

# 亮和暗状态的持续时间
on_duration = 0.75  # 亮状态持续时间
off_duration = 0.5  # 暗状态持续时间



speed_file = open("C:/Users/guoka/Desktop/FYP.txt", "w")
rear_distance_file = open("C:/Users/guoka/Desktop/rear_distance.txt", "w")
front_distance_file = open("C:/Users/guoka/Desktop/front_distance.txt", "w")
current_position_file = open("C:/Users/guoka/Desktop/current_position.txt", "w")

while driver.step() != -1:
    current_time = driver.getTime()

    if arrow_visible:
        if current_time - last_toggle_time >= on_duration:
            arrow_visible = False
            last_toggle_time = current_time
    else:
        if current_time - last_toggle_time >= off_duration:
            arrow_visible = True
            last_toggle_time = current_time

    position = gps.getValues()
    rear_distance = sensors["rear"].getValue()  # Assuming you have a function to get rear distance
    front_distance = sensors["front"].getValue()  # Assuming you have a function to get front distance
    current_speed = driver.getCurrentSpeed()

    draw_hud(current_speed)
    print(current_speed)

    # Write current speed to file every second
    speed_file.write(f"{current_time},{current_speed}\n")
    speed_file.flush()  # Ensure the data is written immediately

    rear_distance_file.write(f"{current_time},{rear_distance}\n")
    rear_distance_file.flush()

    front_distance_file.write(f"{current_time},{front_distance}\n")
    front_distance_file.flush()

    current_position_file.write(f"{current_time},{position}\n")
    current_position_file.flush()











