from controller import Supervisor, Node
import os
from datetime import datetime

import traci

# 创建Supervisor实例
supervisor = Supervisor()

#traci.start(["sumo", "-c", "C:/Users/SimCCAD/Desktop/SURF2023/worlds/shcool_net/sumo.sumocfg"])

# 获取仿真时间步长
timestep = int(supervisor.getBasicTimeStep())

# 获取场景树根节点
root_node = supervisor.getRoot()
root_children_field = root_node.getField("children")

# 初始化SUMO车辆节点列表
sumo_vehicles = []


def write_to_file(id, value):
    # 获取桌面路径
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    
    
    
    # 创建一个叫SUMO的文件夹路径
    sumo_folder_path = os.path.join(desktop_path, "SUMO")
    
    # 如果文件夹不存在，则创建文件夹
    if not os.path.exists(sumo_folder_path):
        os.makedirs(sumo_folder_path)

    # 定义文件路径，存储在SUMO文件夹下，并命名为position.txt
    file_path = os.path.join(sumo_folder_path, "position.txt")

    current_time = datetime.now().strftime('%H:%M:%S:%f')[:-4]

    # 格式化字符串
    formatted_string = f"{current_time} {id} {value}\n"
    
    # 将数据写入文本文件
    with open(file_path, 'a') as file:
        file.write(formatted_string)



while supervisor.step(timestep) != -1:
    # 每个仿真时间步都重新填充sumo_vehicles列表
    sumo_vehicles.clear()

    
    # 遍历所有子节点，查找SUMO车辆节点
    for i in range(root_children_field.getCount()):
        node = root_children_field.getMFNode(i)

        # 检查是否是SUMO车
        if node.getType() == Node.SOLID and "SUMO_VEHICLE" in node.getDef():
            sumo_vehicles.append(node)

    # 打印所有SUMO车辆的translation数据
    for vehicle_node in sumo_vehicles:
        translation_field = vehicle_node.getField("translation")
        translation = translation_field.getSFVec3f()
        #print(f"Vehicle {vehicle_node.getDef()} translation: {translation}")
        write_to_file(vehicle_node.getDef(),translation)        
