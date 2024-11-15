
from controller import Display
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from vehicle import Driver
import arrow_draw
import navigation_info
import speed_limit


#robot = Robot()
driver = Driver()
timestep = int(driver.getBasicTimeStep())
hud_display = driver.getDevice("HUD_DISPLAY")
hud_display_width = hud_display.getWidth()
hud_display_height = hud_display.getHeight()

print(hud_display_width)
print(hud_display_height/2)


#aaaaa=driver.getCurrentSpeed()
#print(aaaaa)


def draw_hud(recieve_speed):
    # 使用Pillow创建一个新的图像
    img = Image.new('RGBA', (hud_display_width, hud_display_height), color=(0, 0, 0, 0))
    # 为HUD的背景添加半透明的黑色图层
    alpha_layer = Image.new('RGBA', (hud_display_width, hud_display_height), (0, 0, 0, 128))  # 可以调整最后一个参数来控制透明度
    img = Image.alpha_composite(img, alpha_layer)
    
    
    # 设置文本颜色和大小
    font_size = 30
    font = ImageFont.truetype("C:/Users/Tian2/Desktop/SURF/font/Pixelarial11/PIXEAB__.TTF", font_size)


    # 显示速度信息
    recieve_speed = max(0, recieve_speed)
    speed_text = "{:.0f}".format(recieve_speed)

    x_position = 25
    y_position = 235

    # 阴影的颜色和偏移
    shadow_color = (10, 10, 10)  #阴影背景
    shadow_offset = (1, 1) 

    # 创建只有阴影的图像
    shadow_img = Image.new('RGBA', (hud_display_width, hud_display_height), color=(0, 0, 0, 255))
    shadow_draw = ImageDraw.Draw(shadow_img)

    # 在此图像上绘制阴影文本
    shadow_draw.text((x_position + shadow_offset[0], y_position + shadow_offset[1]), speed_text, font=font, fill=shadow_color)
    
    # 将阴影图像与主图像组合
    img = Image.alpha_composite(img, shadow_img)

    # 再次获取主图像的绘图上下文
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
    angle = 15
    img = img.rotate(-angle, resample=Image.BICUBIC, expand=False)  
    
    #为了绘制箭头，不受旋转影响，再次获取图像上下文！
    draw = ImageDraw.Draw(img)  # 由于图像已经旋转，我们需要重新获取绘图上下文
    
    # 添加限速标志
    limit = 30  # 假设限速为50km/h
    speed_limit.draw_speed_limit(img, limit) #限速标识
    
    if arrow_visible:
        arrow_draw.arrow_up(draw, hud_display_width, hud_display_height) #生成箭头代码
        navigation_info.navigation_info_up(draw, hud_display_width, hud_display_height, "1.4km")


    # 将图像转换为RGB
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





while driver.step() != -1:
    current_time = driver.getTime()

    if arrow_visible:
        # 如果箭头是可见的，但已超过了on_duration，那么切换为不可见
        if current_time - last_toggle_time >= on_duration:
            arrow_visible = False
            last_toggle_time = current_time
    else:
        # 如果箭头是不可见的，但已超过了off_duration，那么切换为可见
        if current_time - last_toggle_time >= off_duration:
            arrow_visible = True
            last_toggle_time = current_time

    position = gps.getValues()
  #  print(position)
            
    draw_hud(current_time)  
        
  #  draw_hud(driver.getCurrentSpeed())  






