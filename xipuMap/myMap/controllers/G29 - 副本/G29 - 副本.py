import os
import sys
from PyQt5.QtCore import QSettings
from vehicle import Driver
from pathlib import Path

NAXIS = 3
NAXISBOUNDS = 2
NBUTTONS = 13
NGAINS = 2




desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
# 使用桌面路径来创建文件路径
speed_file_path = os.path.join(desktop_path, "FYP.txt")
rear_distance_file_path = os.path.join(desktop_path, "rear_distance.txt")
front_distance_file_path = os.path.join(desktop_path, "front_distance.txt")
current_position_file_path = os.path.join(desktop_path, "current_position.txt")


# 全局变量定义处
speed_file = open(speed_file_path, "w")
rear_distance_file = open(rear_distance_file_path, "w")
front_distance_file = open(front_distance_file_path, "w")
current_position_file = open(current_position_file_path, "w")




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

        # Convert raw data to scaled data [0, 1]
        steeringAngle = self.convertFeedback(steeringFeedback, self.axesBoundsMap["minSteering"],
                                             self.axesBoundsMap["maxSteering"])
        throttle = self.convertFeedback(throttleFeedback, self.axesBoundsMap["minThrottle"],
                                        self.axesBoundsMap["maxThrottle"])
        brake = self.convertFeedback(brakeFeedback, self.axesBoundsMap["minBrake"], self.axesBoundsMap["maxBrake"])

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


def main(config_file=None):
    driver = Driver()
    joystick_interface = JoystickInterface(driver, config_file)

    # 主循环
    while driver.step() != -1:
        # Write current speed to file every second
        speed_file.write(f"{current_time},{current_speed}\n")
        speed_file.flush()  # Ensure the data is written immediately

        rear_distance_file.write(f"{current_time},{rear_distance}\n")
        rear_distance_file.flush()

        front_distance_file.write(f"{current_time},{front_distance}\n")
        front_distance_file.flush()

        current_position_file.write(f"{current_time},{position}\n")
        current_position_file.flush()

        if not joystick_interface.step():
            print("Please connect a joystick before starting the controller.main函数里的", file=sys.stderr)
            break


if __name__ == "__main__":
    import sys

    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    print("config_file为")
    print(sys.argv)
    main(config_file)