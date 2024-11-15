from vehicle import Driver

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

lanePositions = [10.6, 6.875, 3.2]
currentLane = 1
overtakingSide = None
maxSpeed = 70
safeOvertake = False
overtakeStartTime = None
overtakeEndTime = None
LANE_STAY_DURATION = 15  # 在新的车道上恒定速度行驶的时间
overtakingCompleted = False
originalLane = currentLane  # 初始设置为当前车道

def apply_PID(position, targetPosition):
    """Apply the PID controller and return the angle command."""
    P = 0.05
    I = 0.000015
    D = 25
    diff = position - targetPosition
    if apply_PID.previousDiff is None:
        apply_PID.previousDiff = diff
    # anti-windup mechanism
    if diff > 0 and apply_PID.previousDiff < 0:
        apply_PID.integral = 0
    if diff < 0 and apply_PID.previousDiff > 0:
        apply_PID.integral = 0
    apply_PID.integral += diff
    # compute angle
    angle = P * diff + I * apply_PID.integral + D * (diff - apply_PID.previousDiff)
    apply_PID.previousDiff = diff
    return angle


apply_PID.integral = 0
apply_PID.previousDiff = None


def get_ema_speed(current_speed):
    alpha = 0.1  # 调整此值以获得所需的平滑级别，范围是 0-1
    if get_ema_speed.previous is None:
        get_ema_speed.previous = current_speed
    ema_speed = alpha * current_speed + (1 - alpha) * get_ema_speed.previous
    get_ema_speed.previous = ema_speed
    return ema_speed

get_ema_speed.previous = None


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

driver = Driver()
for name in sensorsNames:
    sensors[name] = driver.getDevice("distance sensor " + name)
    sensors[name].enable(10)

gps = driver.getDevice("gps")
gps.enable(10)

while driver.step() != -1:
    # adjust speed according to front vehicle
    frontDistance = sensors["front"].getValue()
    frontRange = sensors["front"].getMaxValue()
    speed = maxSpeed * frontDistance / frontRange
    if sensors["front right 0"].getValue() < 8.0 or sensors["front left 0"].getValue() < 8.0:
        # another vehicle is currently changing lane in front of the vehicle => emergency braking
        speed = min(0.5 * maxSpeed, speed)
    if overtakingSide is not None:
        # check if overtaking should be aborted
        if overtakingSide == 'right' and sensors["left"].getValue() < 0.8 * sensors["left"].getMaxValue():
            overtakingSide = None
            currentLane -= 1
        elif overtakingSide == 'left' and sensors["right"].getValue() < 0.8 * sensors["right"].getMaxValue():
            overtakingSide = None
            currentLane += 1
        else:  # reduce the speed if the vehicle from previous lane is still in front
            speed2 = reduce_speed_if_vehicle_on_side(speed, overtakingSide)
            if speed2 < speed:
                speed = speed2
    speed = get_ema_speed(speed)
    driver.setCruisingSpeed(speed)
    # brake if needed
    speedDiff = driver.getCurrentSpeed() - speed
    if speedDiff > 0:
        driver.setBrakeIntensity(min(speedDiff / speed, 1))
    else:
        driver.setBrakeIntensity(0)
    # car in front, try to overtake
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
        if overtakingSide is not None:  # This means the vehicle is starting to overtake
            overtakeStartTime = driver.getTime()        
     # check if overtaking is over
    if overtakingSide is not None and overtakeStartTime is not None:
        if ((overtakingSide == 'right' and sensors["left"].getValue() > 0.8 * sensors["left"].getMaxValue()) or 
           (overtakingSide == 'left' and sensors["right"].getValue() > 0.8 * sensors["right"].getMaxValue())):
            # 确定返回到哪个车道
            if overtakingSide == 'right' and currentLane < len(lanePositions) - 1:
                currentLane += 1
            elif overtakingSide == 'left' and currentLane > 0:
                currentLane -= 1
            overtakingSide = None  # 设置为 None 以表示超车完成

            # 记录当前时间
            overtakeEndTime = driver.getTime()
     # 检查是否应返回原始车道
    if overtakingSide is None and overtakeEndTime is not None and driver.getTime() - overtakeEndTime > LANE_STAY_DURATION:
        if currentLane > originalLane and currentLane > 0:
            currentLane -= 1
        elif currentLane < originalLane and currentLane < len(lanePositions) - 1:
            currentLane += 1
        overtakeEndTime = None  # 重置，以免持续触发这个条件
    # adjust steering to stay in the middle of the current lane
    position = gps.getValues()[1]
    angle = max(min(apply_PID(position, lanePositions[currentLane]), 0.5), -0.5)
    driver.setSteeringAngle(-angle)
    # check if overtaking is over
    if abs(position - lanePositions[currentLane]) < 1.5:  # the car is just in the lane
        overtakingSide = None
        