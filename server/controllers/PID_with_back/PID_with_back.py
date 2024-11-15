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

from controller import GPS
from vehicle import Driver
import math
import os
from datetime import datetime


#20240628晚

driver = Driver()

sensorsNames = [
    "front PID1","front PID2","front","front right PID","front left PID"
]

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
        name_field = node.getField("name")
        if name_field and name_field.getSFString() == "PID2":
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
                
        # calculate waypoints with translation_xy
        if translation_xy:
            for wp in waypoints:
                translated_waypoint = (wp[0] + translation_xy[0], wp[1] + translation_xy[1])
                translated_waypoints.append(translated_waypoint)
                
        # calculate each road angle
        for i in range(len(translated_waypoints) - 1):
            angle = calculate_angle(translated_waypoints[i], translated_waypoints[i+1])
            angles.append(angle)

    return translated_waypoints, angles

def is_point_in_polygon(x, y, polygon):
    """ determining whether a point is within a polygon"""
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
    """vertical vector and shrink it to a specified length"""
    mag = math.sqrt(vx**2 + vy**2)
    ux = -vy / mag
    uy = vx / mag
    return (ux * length, uy * length)

def get_waypoint_polygon(p1, p2, road_width = 10.5):
    """Generate vertices of a quadrilateral based on two landmarks"""
    x1, y1 = p1
    x2, y2 = p2
    half_width = road_width / 2

    # Calculate vertical vectors
    perp_vx, perp_vy = get_perpendicular_vector(x2 - x1, y2 - y1, half_width)

    # Calculate four vertices
    polygon = [
        (x1 + perp_vx, y1 + perp_vy),
        (x1 - perp_vx, y1 - perp_vy),
        (x2 - perp_vx, y2 - perp_vy),
        (x2 + perp_vx, y2 + perp_vy)
    ]

    return polygon

def is_vehicle_in_road(vehicle_position, waypoints, road_width=10.5):
    """Determine if the vehicle is within any quadrilateral 
    area composed of waypoints and return the corresponding i"""
    vx, vy = vehicle_position
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i + 1]
        polygon = get_waypoint_polygon(p1, p2, road_width)
        if is_point_in_polygon(vx, vy, polygon):
            return True, i
    return False, None
  
    
def calculate_angle(p1, p2):
    """Calculate the angle between two points, expressed in radians"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle = math.atan2(dy, dx)  
    return angle

def calculate_side_of_road(x1, y1, x2, y2, x, y):
    # Calculate road direction vector
    road_vector_x = x2 - x1
    road_vector_y = y2 - y1
    
    # Calculate vehicle position vector
    vehicle_vector_x = x - x1
    vehicle_vector_y = y - y1
    
    # Calculate vector cross product
    cross_product = road_vector_x * vehicle_vector_y - road_vector_y * vehicle_vector_x
    
    if cross_product > 0:
        return "left"
    elif cross_product < 0:
        return "right"
    else:
        return "center"

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

def smooth_speed_transition(current_speed, target_speed, rate=0.02):
    """Smoothly transition to the target speed."""
    if abs(target_speed - current_speed) < rate:
        return target_speed
    elif target_speed > current_speed:
        return current_speed + rate
    else:
        return current_speed - rate
        
def adjust_speed_for_obstacle(current_speed, target_speed, max_speed, rate=0.1):
    """Adjust the speed based on obstacle detection and smooth transition."""
    front_distance = min(sensors["front"].getValue(),
                   sensors["front PID1"].getValue(),
                   sensors["front PID2"].getValue())
    front_range = sensors["front"].getMaxValue()
    
    if front_distance < front_range:  # Obstacle detected
        obstacle_speed = max_speed * front_distance / front_range
        return obstacle_speed
    else:
        return smooth_speed_transition(current_speed, target_speed, rate)                

get_filtered_speed.previousSpeeds = []

for name in sensorsNames:
    sensors[name] = driver.getDevice("distance sensor " + name)
    sensors[name].enable(10)

gps = driver.getDevice("gps")
gps.enable(10)
# speed = gps.getSpeed()
current_speed = 0


def record():
    nowPosition = gps.getValues()  # 获取当前位置
    nowSpeed = driver.getCurrentSpeed()  # 获取当前速度
    nowFront = min(sensors["front"].getValue(),
                   sensors["front PID1"].getValue(),
                   sensors["front PID2"].getValue())  # 获取前车车距
    #nowRear = sensors["rear"].getValue()  # 获取后车车距

    # 获取桌面路径
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    # 定义目标文件夹路径
    PID_folder = os.path.join(desktop_path, "PID")

    # 如果目标文件夹不存在，则创建它们
    os.makedirs(PID_folder, exist_ok=True)

    # 获取当前时间，精确到毫秒
    current_time = datetime.now().strftime('%H:%M:%S:%f')[:-4]

    # 定义文件路径和数据格式化字符串
    file_paths = {
        "position.txt": nowPosition,
        "speed.txt": nowSpeed,
        "nowFront.txt": nowFront,
        #"nowRear.txt": nowRear
    }

    # 将数据分别写入不同的文本文件
    for file_name, data in file_paths.items():
        formatted_string = f"{current_time} {data}\n"
        file_path = os.path.join(PID_folder, file_name)
        with open(file_path, 'a') as file:
            file.write(formatted_string)

        # 打印输出以验证（可选）
        # print(formatted_string)



while driver.step() != -1 and j < 7:
    veh_speed = gps.getSpeed()
    # print(veh_speed)

    record()


    # Get the translation field of the vehicle node
    veh_transField = vehicle_node.getField("translation")
    veh_xyz = veh_transField.getSFVec3f()
    veh_p = (veh_xyz[0], veh_xyz[1])
    # print(f"Vehicle position: x={veh_p}")
    
    veh_rotField = vehicle_node.getField("rotation")
    veh_rot = veh_rotField.getSFRotation()
    rotation_axis = veh_rot[2]
    maxSpeed = 60
    # print(f"current vehicle angle:{veh_rot[3]}")
    steer_angle = driver.getSteeringAngle()



    # print(frontDistance)
    # print(frontRange)

    frontRange = sensors["front"].getMaxValue()
    frontDistance1 = sensors["front PID1"].getValue()
    frontDistance2 = sensors["front PID2"].getValue()

    frontLeftDistance= sensors["front left PID"].getValue()
    frontRightDistance= sensors["front right PID"].getValue()

    minDistance =min(frontDistance1,frontDistance2, frontLeftDistance,frontRightDistance)
    #print(f"最小的传感器距离为{minDistance}")

    target_speed = maxSpeed * minDistance / frontRange
    # speed = maxSpeed * frontDistance / frontRange
    
    # if obstacles ahead
    if minDistance < frontRange:
        target_speed = maxSpeed * minDistance / frontRange
        current_speed = adjust_speed_for_obstacle(current_speed, target_speed, maxSpeed, rate=0.5)
    else:  # if no obstacles
        target_speed = maxSpeed
        target_speed = get_filtered_speed(target_speed)
        current_speed = smooth_speed_transition(current_speed, target_speed, rate=0.1)
    
    for j in range(len(route_names)):
        cur_rdwp, road_angles = get_node_info(route_node[j])
        in_road, index = is_vehicle_in_road(veh_p, cur_rdwp)
    
        if in_road:
            # print(f"Vehicle is on Road {j}, ID {route_names[j]}")
            if index is not None and index < len(cur_rdwp) - 1:
                # waypoint1 = cur_rdwp[index]
                road_angle = road_angles[index]
                angle_diff = -road_angle - veh_rot[3]

                x1, y1 = cur_rdwp[index]
                x2, y2 = cur_rdwp[index + 1]
                vehicle_side = calculate_side_of_road(x1, y1, x2, y2, veh_p[0], veh_p[1])
                # print(f"Vehicle is on the {vehicle_side} side of the road.")
                
                # Adjust the steering angle based on the vehicle position
                if vehicle_side == "left":
                    driver.setSteeringAngle(angle_diff*3+0.009)   
                elif vehicle_side == "right":
                    driver.setSteeringAngle(angle_diff*3-0.009) 
                # print(vehicle_side)
                
                # target_speed = get_filtered_speed(target_speed)
                # current_speed = smooth_speed_transition(current_speed, target_speed)
                driver.setCruisingSpeed(current_speed)
                speedDiff = driver.getCurrentSpeed() - current_speed
                
                # speed = get_filtered_speed(speed)
                # driver.setCruisingSpeed(speed)
                # speedDiff = driver.getCurrentSpeed() - speed
                if speedDiff > 0:
                    # driver.setBrakeIntensity(min(speedDiff / speed, 1))
                    driver.setBrakeIntensity(min(speedDiff / current_speed, 1))

                else:
                    driver.setBrakeIntensity(0)
            break