# Copyright 1996-2022 Cyberbotics Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""vehicle_driver controller."""
#20240618

from controller import GPS,Motor
from vehicle import Driver
import math
import os
from datetime import datetime

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
    "left"]
sensors = {}

route_names = [
    "Songtao_1", "Songtao_2", 
    "Songtao_3_1","Songtao_3_2",
    "Songtao_3_3","Songtao_3_4",
    "Songtao_4"
]

worldinfo_node = driver.getRoot()
children_field = worldinfo_node.getField("children")
route_node = [None] * len(route_names)
cur_road_node = driver.getFromDef("ROAD_NODE_DEF")
# Get the vehicle node using its DEF name
vehicle_node = None
lanePositions = [233.419, 66.7578, 0.01]
currentLane = 1
overtakingSide = None
maxSpeed = 40
safeOvertake = False
j = 0 
# route_node_count = len(route_node) 
in_road = False

for i in range(children_field.getCount()):
    c_node = children_field.getMFNode(i)
    
    if c_node:
        child_field = c_node.getField("id")
        
        if child_field:
            road_id = child_field.getSFString()
            
            for j in range(len(route_names)):
                if route_names[j] == road_id:
                    # print(f"Matched Node ID is {road_id}")
                    route_node[j] = c_node
                    # print(j)

for i in range(children_field.getCount()):
    node = children_field.getMFNode(i)
    if node.getTypeName() == "BmwX5":  # Match the node type
        print("收到name")
        name_field = node.getField("name")
        if name_field and name_field.getSFString() == "vehicle":
            vehicle_node = node
            break

def get_node_info(node):
    translation_xy = None
    waypoints = []
    translated_waypoints = []
    angles = []

    if node:
        node_id = node.getField("id").getSFString()

        translation_field = node.getField("translation")
        if translation_field:
            translation = translation_field.getSFVec3f()
            translation_xy = (translation[0], translation[1])  # 提取 x 和 y 坐标

        waypoints_field = node.getField("wayPoints")
        if waypoints_field:
            waypoints_count = waypoints_field.getCount()
            for i in range(waypoints_count):
                waypoint = waypoints_field.getMFVec3f(i)
                waypoint_xy = (waypoint[0], waypoint[1])
                waypoints.append(waypoint_xy)
                
        # 计算每一个 waypoints 加上 translation_xy
        if translation_xy:
            for wp in waypoints:
                translated_waypoint = (wp[0] + translation_xy[0], wp[1] + translation_xy[1])
                translated_waypoints.append(translated_waypoint)
                
        # 计算每段道路的角度
        for i in range(len(translated_waypoints) - 1):
            angle = calculate_angle(translated_waypoints[i], translated_waypoints[i+1])
            angles.append(angle)

    return translated_waypoints, angles

def is_point_in_polygon(x, y, polygon):
    """判断点是否在多边形内的辅助函数"""
    n = len(polygon)
    inside = False
    px, py = x, y
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside

def get_perpendicular_vector(vx, vy, length):
    """计算给定向量的垂直向量并缩放到指定长度"""
    mag = math.sqrt(vx**2 + vy**2)
    ux = -vy / mag
    uy = vx / mag
    return (ux * length, uy * length)

def get_waypoint_polygon(p1, p2, road_width = 10.5):
    """根据两个路标生成四边形的顶点"""
    x1, y1 = p1
    x2, y2 = p2
    half_width = road_width / 2

    # 计算垂直向量
    perp_vx, perp_vy = get_perpendicular_vector(x2 - x1, y2 - y1, half_width)

    # 计算四个顶点
    polygon = [
        (x1 + perp_vx, y1 + perp_vy),
        (x1 - perp_vx, y1 - perp_vy),
        (x2 - perp_vx, y2 - perp_vy),
        (x2 + perp_vx, y2 + perp_vy)
    ]

    return polygon

def is_vehicle_in_road(vehicle_position, waypoints, road_width=10.5):
    """判断车辆是否在由 waypoints 组成的任何四边形区域内，并返回相应的 i"""
    vx, vy = vehicle_position
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i + 1]
        polygon = get_waypoint_polygon(p1, p2, road_width)
        if is_point_in_polygon(vx, vy, polygon):
            return True, i
    return False, None
  
    
def calculate_angle(p1, p2):
    """计算两点之间的角度，以弧度表示"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle = math.atan2(dy, dx)  
    return angle
    
    
def apply_PID(current_angle, target_angle):
    """Apply the PID controller and return the angle command."""
    P = 0.05
    I = 0.000015
    D = 25
    diff = current_angle - target_angle
    if apply_PID.previousDiff is None:
        apply_PID.previousDiff = diff
    # 防风机制
    if diff > 0 and apply_PID.previousDiff < 0:
        apply_PID.integral = 0
    if diff < 0 and apply_PID.previousDiff > 0:
        apply_PID.integral = 0
    apply_PID.integral += diff
    # 计算角度
    angle = P * diff + I * apply_PID.integral + D * (diff - apply_PID.previousDiff)
    apply_PID.previousDiff = diff
    return angle


apply_PID.integral = 0
apply_PID.previousDiff = None


def get_filtered_speed(speed):
    """Filter the speed command to avoid abrupt speed changes."""
    get_filtered_speed.previousSpeeds.append(speed)
    if len(get_filtered_speed.previousSpeeds) > 100:  # keep only 80 values
        get_filtered_speed.previousSpeeds.pop(0)
    return sum(get_filtered_speed.previousSpeeds) / float(len(get_filtered_speed.previousSpeeds))


def is_vehicle_on_side(side):
    """Check (using the 3 appropriated front distance sensors) if there is a car in front."""
    for i in range(3):
        name = "front " + side + " " + str(i)
        if sensors[name].getValue() > 0.8 * sensors[name].getMaxValue():
            return True
    return False


def reduce_speed_if_vehicle_on_side(speed, side):
    """Reduce the speed if there is some vehicle on the side given in argument."""
    minRatio = 1
    for i in range(3):
        name = "front " + overtakingSide + " " + str(i)
        ratio = sensors[name].getValue() / sensors[name].getMaxValue()
        if ratio < minRatio:
            minRatio = ratio
    return minRatio * speed


get_filtered_speed.previousSpeeds = []

for name in sensorsNames:
    sensors[name] = driver.getDevice("distance sensor " + name)
    sensors[name].enable(10)

gps = driver.getDevice("gps")
gps.enable(10)
# speed = gps.getSpeed()





def record():
    nowPosition = gps.getValues()    # 获取当前位置
    nowSpeed = driver.getCurrentSpeed()   # 获取当前速度
    nowFront = sensors["front"].getValue()  # 获取前车车距
    nowRear = sensors["rear"].getValue()    # 获取后车车距
    
    # 获取桌面路径
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    
    # 定义目标文件夹路径
    PID_folder = os.path.join(desktop_path, "PID", "Webots1")
    
    # 如果目标文件夹不存在，则创建它们
    os.makedirs(PID_folder, exist_ok=True)
    
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
        file_path = os.path.join(PID_folder, file_name)
        with open(file_path, 'a') as file:
            file.write(formatted_string)
        
        # 打印输出以验证（可选）
        #print(formatted_string)



while driver.step() != -1 and j < 7:

    record()


    veh_speed = gps.getSpeed()
    # print(veh_speed)
   
    # Get the translation field of the vehicle node
    veh_transField = vehicle_node.getField("translation")
    veh_xyz = veh_transField.getSFVec3f()
    veh_p = (veh_xyz[0], veh_xyz[1])
    # print(f"Vehicle position: x={veh_p}")
    
    veh_rotField = vehicle_node.getField("rotation")
    veh_rot = veh_rotField.getSFRotation()
    rotation_axis = veh_rot[2]
    maxSpeed = 60
    # print(f"当前车辆的角度为:{veh_rot[3]}")
    steer_angle = driver.getSteeringAngle()
    frontDistance = sensors["front"].getValue()
    frontRange = sensors["front"].getMaxValue()
    speed = maxSpeed * frontDistance / frontRange
    
    for j in range(len(route_names)):
        cur_rdwp, road_angles = get_node_info(route_node[j])
        in_road, index = is_vehicle_in_road(veh_p, cur_rdwp)
    
        if in_road:
            # print(f"-----------------------------")
            # print(f"Vehicle is on Road {j}, ID {route_names[j]}")
            if index is not None and index < len(cur_rdwp) - 1:
                # waypoint1 = cur_rdwp[index]
                # waypoint2 = cur_rdwp[index + 1]
                road_angle = road_angles[index]
                angle_diff = -road_angle - veh_rot[3]
                # print(f"车辆角度:{veh_rot[3]}")
                # print(f"道路角度:{road_angle}")
                # print(f"-----------------------------")
                driver.setSteeringAngle(angle_diff*3)   
                # print(f"输出的控制角度为:{angle_diff}")
                # print(f"车轮的角度为{steer_angle}") 
                # print(f"  Segment Angle: {road_angle}")
                if sensors["front right 0"].getValue() < 8.0 or sensors["front left 0"].getValue() < 8.0:
                    speed = min(0.5 * maxSpeed, speed)
                if overtakingSide is not None:
                    if overtakingSide == 'right' and sensors["left"].getValue() < 0.8 * sensors["left"].getMaxValue():
                        overtakingSide = None
                        currentLane -= 1
                    elif overtakingSide == 'left' and sensors["right"].getValue() < 0.8 * sensors["right"].getMaxValue():
                        overtakingSide = None
                        currentLane += 1
                    else:
                        speed2 = reduce_speed_if_vehicle_on_side(speed, overtakingSide)
                        if speed2 < speed:
                            speed = speed2
                speed = get_filtered_speed(speed)
                driver.setCruisingSpeed(speed)
                speedDiff = driver.getCurrentSpeed() - speed
                if speedDiff > 0:
                    driver.setBrakeIntensity(min(speedDiff / speed, 1))
                else:
                    driver.setBrakeIntensity(0)
                if frontDistance < 0.8 * frontRange and overtakingSide is None:
                    if (is_vehicle_on_side("left") and
                            (not safeOvertake or sensors["rear left"].getValue() > 0.8 * sensors["rear left"].getMaxValue()) and
                            sensors["left"].getValue() > 0.8 * sensors["left"].getMaxValue() and
                            currentLane < 2):
                        currentLane += 1
                        overtakingSide = 'right'
                    elif (is_vehicle_on_side("right") and
                            (not safeOvertake or sensors["rear right"].getValue() > 0.8 * sensors["rear right"].getMaxValue()) and
                            sensors["right"].getValue() > 0.8 * sensors["right"].getMaxValue() and
                            currentLane > 0):
                        currentLane -= 1
                        overtakingSide = 'left'
                
                position = gps.getValues()[1]
                #print(currentLane)
                if abs(position - lanePositions[currentLane]) < 1.5:
                    overtakingSide = None
            break


