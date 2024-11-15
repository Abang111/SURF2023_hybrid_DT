#没有HUD的版本


import os
import sys
from PyQt5.QtCore import QSettings
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import traci
import time

from vehicle import Driver
from controller import Display
from datetime import datetime


import arrow_draw
import car_info
import navigation_info
import car_arrow_draw
import speed_limit

# 全局变量定义
driver = Driver()    #优先初始化

NAXIS = 3
NAXISBOUNDS = 2
NBUTTONS = 13
NGAINS = 2
axesNames = ["Steering", "Throttle", "Brake"]
axesBoundNames = ["min", "max"]
buttonNames = ["RightWarning", "LeftWarning", "NextGear", "PreviousGear", "FirstGear",
               "SecondGear", "ThirdGear", "FourthGear", "FifthGear", "SixthGear",
               "ReverseGear", "NextWiperMode", "PreviousWiperMode"]
gainNames = ["AutoCentering", "Resistance"]

# Determine platform extension
print(os.name)
if os.name == "nt":
    platformExtension = "windows"
elif os.name == "posix":
    if os.uname().sysname == "Darwin":
        platformExtension = "mac"
    elif os.uname().sysname == "Linux":
        platformExtension = "linux"
    else:
        raise RuntimeError("Unsupported OS")
else:
    raise RuntimeError("Unsupported OS")


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
print(hud_display_height / 2)

gps = driver.getDevice("gps")
gps.enable(10)

# 在循环外部初始化状态变量
arrow_visible = True
last_toggle_time = 0




# 亮和暗状态的持续时间
on_duration = 0.75  # 亮状态持续时间
off_duration = 0.5  # 暗状态持续时间


desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")


# JoystickInterface 类定义
class JoystickInterface:
    def __init__(self, driver, configFile=None):
        self.driver = driver
        self.joystick = driver.getJoystick()
        print("Basic time step:", driver.getBasicTimeStep())

        self.joystick.enable(int(driver.getBasicTimeStep()))
        print("Basic time step:", driver.getBasicTimeStep())

        driver.step()

        # 如果没有连接手柄，则返回
        if not self.joystick.isConnected():
            print("No joystick connected啊.在__init__里面")
            return

        # 如果没有提供配置文件，根据手柄模型选择配置文件
        if configFile is None:
            model = self.joystick.getModel()
            if "G29" in model:
                configFile = "config_logitech_g29.ini"
            elif "G27" in model:
                configFile = "config_logitech_g27.ini"
            elif "FANATEC CSL Elite Wheel Base" in model:
                configFile = "config_fanatec_csl_elite_wheel_base.ini"
            else:
                self.fatal(f"'{model}' not supported. Please provide a custom configuration file.")
        else:
            # 如果提供了配置文件路径，但文件不存在，则抛出错误
            if not self.fileExists(configFile):
                self.fatal(f"File '{configFile}' does not exist.")

        # 选择平台特定的配置文件
        platformConfigFile = configFile.replace(".ini", f".{platformExtension}.ini")
        if self.fileExists(platformConfigFile):
            configFile = platformConfigFile

        self.init(configFile)

    def init(self, configFile):
        self.gear = 1
        self.wiperMode = Driver.DOWN  # This needs to be adjusted according to Python API
        self.driver.setGear(self.gear)
        self.driver.setWiperMode(self.wiperMode)

        if self.joystick.isConnected():
            print(f"'{self.joystick.getModel()}' detected (the following configuration file is used: '{configFile}').")

        settings = QSettings(configFile, QSettings.IniFormat)
        self.axesMap = {name: settings.value(f"Axis/{name}", -1, type=int) for name in axesNames}
        self.axesBoundsMap = {f"{bound}{axis}": settings.value(f"AxisBounds/{bound}{axis}", 0, type=int)
                              for axis in axesNames for bound in axesBoundNames}
        self.buttonsMap = {name: settings.value(f"Buttons/{name}", -1, type=int) for name in buttonNames}
        self.gainMap = {name: settings.value(f"Gains/{name}", 0.0, type=float) for name in gainNames}

        if self.joystick.isConnected():
            self.joystick.setForceAxis(self.axesMap["Steering"])

    def fatal(self, txt):
        print(txt, file=sys.stderr)
        sys.exit(-1)

    def fileExists(self, name):
        return Path(name).is_file()

    def convertFeedback(self, raw, minimum, maximum):
        if maximum == minimum:
            self.fatal("Prevent division by 0.")
        return max(0.0, min(1.0, (raw - minimum) / (maximum - minimum)))

    def step(self):
        if not self.joystick.isConnected():
            print("调用step")
            return False

        # Update steering, throttle, and brake based on axes value
        steeringFeedback = self.joystick.getAxisValue(self.axesMap["Steering"])
        throttleFeedback = self.joystick.getAxisValue(self.axesMap["Throttle"])
        brakeFeedback = self.joystick.getAxisValue(self.axesMap["Brake"])

        #print("准备steer")
        # Convert raw data to scaled data [0, 1]
        steeringAngle = self.convertFeedback(steeringFeedback, self.axesBoundsMap["minSteering"],
                                             self.axesBoundsMap["maxSteering"])
        #print("steeringAngle有了")
        throttle = self.convertFeedback(throttleFeedback, self.axesBoundsMap["minThrottle"],
                                        self.axesBoundsMap["maxThrottle"])
        #print("throttle有了")
        brake = self.convertFeedback(brakeFeedback, self.axesBoundsMap["minBrake"], self.axesBoundsMap["maxBrake"])
        #print("brake有了")
        # Apply the values to the automobile API
        self.driver.setSteeringAngle(steeringAngle - 0.5)  # Adjust range as needed for your model
        self.driver.setThrottle(throttle)
        self.driver.setBrakeIntensity(brake)

        # Update gear and indicator based on button states
        button = self.joystick.getPressedButton()
        gear = self.gear
        wiperMode = self.wiperMode

        # Initialize status flags for button presses
        isSwitchingToNextGear = False
        isSwitchingToPreviousGear = False
        isLeftBlinkerOn = False
        isRightBlinkerOn = False
        isSwitchingToNextWiperMode = False
        isSwitchingToPreviousWiperMode = False

        while button >= 0:
            if button == self.buttonsMap["NextGear"]:
                if not self.wasSwitchingToNextGear:
                    gear += 1
                isSwitchingToNextGear = True
            elif button == self.buttonsMap["PreviousGear"]:
                if not self.wasSwitchingToPreviousGear:
                    gear -= 1
                isSwitchingToPreviousGear = True
            elif button == self.buttonsMap["FirstGear"]:
                gear = 1
            elif button == self.buttonsMap["SecondGear"]:
                gear = 2
            elif button == self.buttonsMap["ThirdGear"]:
                gear = 3
            elif button == self.buttonsMap["FourthGear"]:
                gear = 4
            elif button == self.buttonsMap["FifthGear"]:
                gear = 5
            elif button == self.buttonsMap["SixthGear"]:
                gear = 6
            elif button == self.buttonsMap["ReverseGear"]:
                gear = -1
            elif button == self.buttonsMap["RightWarning"]:
                if not self.wasRightBlinkerOn:
                    self.driver.setIndicator(
                        self.driver.INDICATOR_RIGHT if self.driver.getIndicator() != self.driver.INDICATOR_RIGHT else self.driver.INDICATOR_OFF)
                isRightBlinkerOn = True
            elif button == self.buttonsMap["LeftWarning"]:
                if not self.wasLeftBlinkerOn:
                    self.driver.setIndicator(
                        self.driver.INDICATOR_LEFT if self.driver.getIndicator() != self.driver.INDICATOR_LEFT else self.driver.INDICATOR_OFF)
                isLeftBlinkerOn = True
            elif button == self.buttonsMap["NextWiperMode"]:
                if not self.wasSwitchingToNextWiperMode and self.wiperMode < self.driver.FAST:
                    wiperMode += 1
                isSwitchingToNextWiperMode = True
            elif button == self.buttonsMap["PreviousWiperMode"]:
                if not self.wasSwitchingToPreviousWiperMode and wiperMode > self.driver.DOWN:
                    wiperMode -= 1
                isSwitchingToPreviousWiperMode = True

            button = self.joystick.getPressedButton()  # Check for next button press

        # Update static status flags
        self.wasSwitchingToNextGear = isSwitchingToNextGear
        self.wasSwitchingToPreviousGear = isSwitchingToPreviousGear
        self.wasLeftBlinkerOn = isLeftBlinkerOn
        self.wasRightBlinkerOn = isRightBlinkerOn
        self.wasSwitchingToNextWiperMode = isSwitchingToNextWiperMode
        self.wasSwitchingToPreviousWiperMode = isSwitchingToPreviousWiperMode

        # Apply gear and wiper mode if changed
        gear = max(-1, min(self.driver.getGearNumber(), gear))

        if gear != self.gear:
            self.gear = gear
            self.driver.setGear(self.gear)
            print("gear:", self.gear)

        if wiperMode != self.wiperMode:
            self.wiperMode = wiperMode
            self.driver.setWiperMode(self.wiperMode)

        # Update resistance and auto-centering gain based on speed
        speed = self.driver.getCurrentSpeed()
        maxSpeed = 60.0  # speed from which the max gain is applied
        if self.gainMap["AutoCentering"] > 0.0:
            self.joystick.setAutoCenteringGain(
                min(self.gainMap["AutoCentering"], self.gainMap["AutoCentering"] * speed / maxSpeed))
        if self.gainMap["Resistance"] > 0.0:
            self.joystick.setResistanceGain(max(0.0, self.gainMap["Resistance"] * (1 - speed / maxSpeed)))

        return True

def draw_hud(recieve_speed):
    # 使用Pillow创建一个新的图像
    img = Image.new('RGBA', (hud_display_width, hud_display_height), color=(0, 0, 0, 0))
    # 为HUD的背景添加半透明的黑色图层
    alpha_layer = Image.new('RGBA', (hud_display_width, hud_display_height), (0, 0, 0, 128))  # 可以调整最后一个参数来控制透明度
    img = Image.alpha_composite(img, alpha_layer)

    # 设置文本颜色和大小
    font_size = 10
    font_path_for_HUD = os.path.join(desktop_path, "font", "Pixelarial11", "PIXEAB__.TTF")
    font = ImageFont.truetype(font_path_for_HUD, font_size)
    # 显示速度信息
    recieve_speed = max(0, recieve_speed)
    speed_text = "{:.0f}".format(recieve_speed)

    x_position = 67
    y_position = 220

    # 阴影的颜色和偏移
    shadow_color = (10, 10, 10)  # 阴影背景
    shadow_offset = (1, 1)

    # 创建只有阴影的图像
    shadow_img = Image.new('RGBA', (hud_display_width, hud_display_height), color=(0, 0, 0, 255))
    shadow_draw = ImageDraw.Draw(shadow_img)

    # 在此图像上绘制阴影文本
    draw = ImageDraw.Draw(img)

    draw.text((x_position, y_position), speed_text, font=font, fill=(0, 255, 0))
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
    for x_offset in range(-outline_width, outline_width + 1):
        for y_offset in range(-outline_width, outline_width + 1):
            draw.text((x_position + x_offset, y_position + y_offset), speed_text, font=font, fill=outline_color)

    # 最后绘制主文本
    draw.text((x_position, y_position), speed_text, font=font, fill=(0, 255, 0))

    # 添加旋转变换
    # angle = 5
    # img = img.rotate(-angle, resample=Image.BICUBIC, expand=False)

    # 为了绘制箭头，不受旋转影响，再次获取图像上下文！
    draw = ImageDraw.Draw(img)  # 由于图像已经旋转，我们需要重新获取绘图上下文

    # 添加限速标志
    #limit = traci.vehicle.getAllowedSpeed  # 假设限速为50km/h
    #speed_limit.draw_speed_limit(img, limit)  # 限速标识

    if arrow_visible:
        arrow_draw.arrow_right(draw, hud_display_width, hud_display_height)  # 生成箭头代码
        navigation_info.navigation_info_right(draw, hud_display_width, hud_display_height, "3.4km")

    #绘制车况示意图
   #本车
    rect_left = 122
    rect_top = 190
    rect_right = 132
    rect_bottom = 200
    draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
   #前车
    F_distance = int(sensors["front"].getValue())
    if F_distance < 10:
       rect_left = 119
       rect_top = 160
       rect_right = 135
       rect_bottom = 175
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(255, 0, 0))
   #后车
    R_distance = int(sensors["rear"].getValue())
    if R_distance < 10:
       rect_left = 119
       rect_top = 215
       rect_right = 135
       rect_bottom = 230
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(255, 0, 0))
    frontRange = sensors["front"].getMaxValue()
    frontDistance = sensors["front"].getValue()
    if sensors["front left 1"].getValue() < 8 :
    # 左前
       rect_left = 139
       rect_top = 160  # 根据 distance_left 调整正方形的 top
       rect_right = 150
       rect_bottom = 175  # 根据 distance_left 调整正方形的 bottom
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    if sensors["front right 1"].getValue() < 8 :
  #右前
       rect_left = 99
       rect_top = 160  # 根据 distance_left 调整正方形的 top
       rect_right = 110
       rect_bottom = 175  # 根据 distance_left 调整正方形的 bottom
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))

    if sensors["rear left"].getValue() < 8 :
    # 右后
       rect_left = 139
       rect_top = 215  # 根据 distance_left 调整正方形的 top
       rect_right = 150
       rect_bottom = 230  # 根据 distance_left 调整正方形的 bottom
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    if sensors["rear right"].getValue() < 8:
    # 左后
       rect_left = 99
       rect_top = 215  # 根据 distance_left 调整正方形的 top
       rect_right = 110
       rect_bottom = 230  # 根据 distance_left 调整正方形的 bottom
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))

    if sensors["right"].getValue() < 3:
    # 右车
       rect_left =  139
       rect_top = 190  # 根据 distance_left 调整正方形的 top
       rect_right = 150
       rect_bottom = 200  # 根据 distance_left 调整正方形的 bottom
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))
    if sensors["left"].getValue() < 3:
    # 左车
       rect_left = 99
       rect_top = 190  # 根据 distance_left 调整正方形的 top
       rect_right = 110
       rect_bottom = 200  # 根据 distance_left 调整正方形的 bottom
       draw.rectangle([rect_left, rect_top, rect_right, rect_bottom], fill=(0, 0, 255))


    R_distance = int(sensors["rear"].getValue())
    if R_distance < 10:
       car_info.draw_distance(img, R_distance)
    #print("目前成功")
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

def is_vehicle_on_side(side):
    """Check (using the 3 appropriated front distance sensors) if there is a car in front."""
    for i in range(3):
        name = "front " + side + " " + str(i)
        if sensors[name].getValue() > 0.8 * sensors[name].getMaxValue():
            return True
    return False



# 主循环
def main(config_file=None):
    joystick_interface = JoystickInterface(driver, config_file)
    # HUD显示、传感器数据处理、文件记录等初始化...

    while driver.step() != -1:

        # 读取GPS和传感器值，绘制HUD...
        #draw_hud(driver.getCurrentSpeed())



        nowPosition = gps.getValues()  # 获取当前位置
        nowSpeed = driver.getCurrentSpeed()  # 获取当前速度
        nowFront = sensors["front"].getValue()  # 获取前车车距
        nowRear = sensors["rear"].getValue()  # 获取后车车距

        # 获取桌面路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

        # 定义目标文件夹路径
        NO_HUD_folder = os.path.join(desktop_path, "Webots_NO_HUD")

        # 如果目标文件夹不存在，则创建它们
        os.makedirs(NO_HUD_folder, exist_ok=True)

        # 获取当前时间，精确到毫秒
        current_time = datetime.now().strftime('%H:%M:%S:%f')[:-4]

        # 定义文件路径和数据格式化字符串
        file_paths = {
            "position.txt": nowPosition,
            "speed.txt": nowSpeed,
            "nowFront.txt": nowFront,
            "nowRear.txt": nowRear
        }

    # 将数据分别写入不同的文本文件
        for file_name, data in file_paths.items():
            formatted_string = f"{current_time} {data}\n"
            file_path = os.path.join(NO_HUD_folder, file_name)
            with open(file_path, 'a') as file:
                file.write(formatted_string)
        
        if not joystick_interface.step():
            print("Please connect a joystick before starting the controller.main函数里的", file=sys.stderr)
            break



if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    main(config_file)
