import math
import sys
import time
import cv2                          
import glfw
import numpy as np
import openvr
from OpenGL.GL import *
from scipy.spatial.transform import Rotation as R
from manus import Manus_api as ma
import threading

def tick():
	global tick_time
	tick_time = time.time()

def tock():
	global tick_time
	dur = time.time()-tick_time
	return dur

def angle_inverse(value):
	return math.pi*2-value

def angle_convert(value):
	if value>math.pi:
		return value-math.pi*2
	elif value<math.pi*-1:
		return value+math.pi*2
	return value


class sample_buffer():
	def __init__(self):
		self.size = 0
		self.pos_x = []
		self.pos_y = []
		self.pos_z = []
		self.r_x = []
		self.r_y = []
		self.r_z = []
		self.r_w = []

	def append(self,pose_matrix):
		self.size += 1
		self.pos_x.append(pose_matrix[0][3])
		self.pos_y.append(pose_matrix[1][3])
		self.pos_z.append(pose_matrix[2][3])
		rotate_matrix = [pose_matrix[0][:3],pose_matrix[1][:3],pose_matrix[2][:3]]
		r = R.from_dcm(rotate_matrix)
		r_quat = r.as_quat()
		self.r_x.append(r_quat[0])
		self.r_y.append(r_quat[1])
		self.r_z.append(r_quat[2])
		self.r_w.append(r_quat[3])

class vive_device():
	def __init__(self,vive,index,device_class,serial,pose):
		self.vive = vive 
		self.index = index
		self.type = device_class
		self.serial = serial
		self.init_position = [0,0,0] #x,y,z
		self.init_rotation = R.from_quat([0,0,0,1])
		self.position = [0,0,0] #x,y,z
		self.rotation = R.from_quat([0,0,0,1])
		self.connected = True
		self.sample_number = 0
		self.pose = pose

	def __str__(self):
		return '%s-%s'%(self.type,self.serial)

	def init_pose_from_buffer(self):
		quat = [0,0,0,1]
		self.init_position[0] = sum(self.sample_buffer.pos_x) / float(self.sample_buffer.size)
		self.init_position[1] = sum(self.sample_buffer.pos_y) / float(self.sample_buffer.size)
		self.init_position[2] = sum(self.sample_buffer.pos_z) / float(self.sample_buffer.size)
		quat[0] = sum(self.sample_buffer.r_x) / float(self.sample_buffer.size)
		quat[1] = sum(self.sample_buffer.r_y) / float(self.sample_buffer.size)
		quat[2] = sum(self.sample_buffer.r_z) / float(self.sample_buffer.size)
		quat[3] = sum(self.sample_buffer.r_w) / float(self.sample_buffer.size)
		self.init_rotation = R.from_quat(quat)

	def sample(self,num):
		self.sample_buffer = sample_buffer()
		self.sample_number = num

	def update_pose(self):
		self.connected = self.pose.bDeviceIsConnected
		tracking = self.pose.mDeviceToAbsoluteTracking
		self.position[0] = tracking[0][3]
		self.position[1] = tracking[1][3]
		self.position[2] = tracking[2][3]
		rotate_matrix = [tracking[0][:3],tracking[1][:3],tracking[2][:3]]
		self.rotation = R.from_dcm(rotate_matrix)
		if self.sample_number>0:
			self.sample_number -= 1
			self.sample_buffer.append(tracking)


class vive_renderer():
	def __init__(self,vive,r_w,r_h,l_w,l_h):
		self.vive = vive
		self.r_width = r_w
		self.r_height = r_h
		self.l_width = l_w
		self.l_height = l_h
		print('render target size - right eye: %d %d'%(self.r_width,self.r_height))
		print('render target size - left eye: %d %d'%(self.l_width,self.l_height))
		self.lock_image = threading.Lock()
		self.right_image = np.zeros((self.r_height,self.r_width,3))
		self.left_image = np.zeros((self.l_height,self.l_width,3))
		
	def gl_init(self):
		if not glfw.init():
			raise Exception("GLFW Initialization error")
		# glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
		# glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 5)
		# glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
		self.window = glfw.create_window(10, 10, 'openvr renderer', None, None)
		if self.window is None:
			glfw.terminate()
			raise Exception("GLFW window creation error")
		glfw.set_key_callback(self.window, self.key_callback)
		glfw.make_context_current(self.window)
		
		self.texture_right = openvr.Texture_t(handle=glGenTextures(1),eType=openvr.TextureType_OpenGL,eColorSpace=openvr.ColorSpace_Gamma)
		glBindTexture(GL_TEXTURE_2D, self.texture_right.handle)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self.r_width, self.r_height, 0, GL_BGR, GL_UNSIGNED_BYTE, None)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)
		glBindTexture(GL_TEXTURE_2D, 0)

		self.texture_left = openvr.Texture_t(handle=glGenTextures(1),eType=openvr.TextureType_OpenGL,eColorSpace=openvr.ColorSpace_Gamma)
		glBindTexture(GL_TEXTURE_2D, self.texture_left.handle)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self.l_width, self.l_height, 0, GL_BGR, GL_UNSIGNED_BYTE, None)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)
		glBindTexture(GL_TEXTURE_2D, 0)

	def gl_destroy(self):
		glDeleteTextures(self.texture_right.handle)
		glDeleteTextures(self.texture_left.handle)
		if self.window:
			glfw.make_context_current(self.window)
		glfw.destroy_window(self.window)
		glfw.terminate()

	def key_callback(self, window, key, scancode, action, mods):
		"press ESCAPE to quit the application"
		if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
			glfw.set_window_should_close(self.window, True)

	# image->numpy array (value in 0~255)
	def render(self):
		# print('render to HMD')
		# print(self.right_image.shape)
		# print(self.left_image.shape)
		with self.lock_image:
			glBindTexture(GL_TEXTURE_2D, self.texture_right.handle)
			glTexSubImage2D (GL_TEXTURE_2D, 0, 0, 0, self.r_width, self.r_height, GL_BGR, GL_UNSIGNED_BYTE, self.right_image)
			glBindTexture(GL_TEXTURE_2D, self.texture_left.handle)
			glTexSubImage2D (GL_TEXTURE_2D, 0, 0, 0, self.l_width, self.l_height, GL_BGR, GL_UNSIGNED_BYTE, self.left_image)
			glBindTexture(GL_TEXTURE_2D, 0)
		try:
			self.vive.compositor.submit(openvr.Eye_Right, self.texture_right)
			self.vive.compositor.submit(openvr.Eye_Left, self.texture_left)
		except openvr.error_code.CompositorError_DoNotHaveFocus:
			pass # First frame fails because waitGetPoses has not been called yet
			# print(openvr.error_code.CompositorError_DoNotHaveFocus)
		self.vive.compositor.waitGetPoses(None, None)

	def run(self):
		def render_app():
			self.gl_init()
			print('start render')
			while threading.main_thread().is_alive():
				# tick()
				self.render()
				# print('render time: %f sec'%tock())
			print('end renderer')
			self.gl_destroy()
		self.render_thread = threading.Thread(target=render_app)
		self.render_thread.start()

	def update_image(self,right_image,left_image):
		r_h,r_w,r_c = right_image.shape
		l_h,l_w,l_c = left_image.shape
		with self.lock_image:
			self.right_image = right_image.copy()
			self.left_image = left_image.copy()
			if r_h!=self.r_height or r_w!=self.r_width:
				print('resize right image from %d*%d to %d*%d'%(r_w,r_h,self.r_width,self.r_height))
				self.right_image = cv2.resize(self.right_image, dsize=(self.r_width, self.r_height))
			if l_h!=self.l_height or l_w!=self.l_width:
				print('resize left image from %d*%d to %d*%d'%(l_w,l_h,self.l_width,self.l_height))
				self.left_image = cv2.resize(self.left_image, dsize=(self.l_width, self.l_height))
			
		

class vive_openvr():
	def __init__(self):
		self.vr = openvr.init(openvr.VRApplication_Scene)
		self.compositor = openvr.VRCompositor()
		self.devices_type = {"Tracking Reference":[],"HMD":[],"Controller":[],"Tracker":[]}
		self.devices_list = []
		self.poses = []
		self.update_devices()
		self.renderer = None
		print(self.vr.getEyeToHeadTransform(openvr.Eye_Right))
		print(self.vr.getEyeToHeadTransform(openvr.Eye_Left))
		print(self.vr.getProjectionMatrix(openvr.Eye_Right,0.01,10))
		print(self.vr.getProjectionMatrix(openvr.Eye_Left,0.01,10))

	def __del__(self): 
		openvr.shutdown()

	def calculate_camera_info(self):
		self.transform_right = self.vr.getEyeToHeadTransform(openvr.Eye_Right)
		self.transform_left = self.vr.getEyeToHeadTransform(openvr.Eye_Left)
		self.projection_right = self.vr.getProjectionMatrix(openvr.Eye_Right,0.01,10)
		self.projection_left = self.vr.getProjectionMatrix(openvr.Eye_Left,0.01,10)
		print(self.transform_right)
		print(self.transform_left)
		print(self.projection_right)
		print(self.projection_left)
		self.fov_horizon_right = math.atan(1/self.projection_right[0][0])
		self.fov_horizon_left = math.atan(1/self.projection_left[0][0])
		self.offset_horizon_right = abs(self.projection_right[0][2])
		self.offset_horizon_left = abs(self.projection_left[0][2])
		self.full_fov_horizon_right = math.atan((1+self.offset_horizon_right)/self.projection_right[0][0])
		self.full_fov_horizon_left = math.atan((1+self.offset_horizon_left)/self.projection_right[0][0])
		print('right eye camera fov should be %f'%(self.full_fov_horizon_right*2))
		print('left eye camera fov should be %f'%(self.full_fov_horizon_left*2))
		self.fov_vertical_right = math.atan(1/self.projection_right[1][1])
		self.fov_vertical_left = math.atan(1/self.projection_left[1][1])
		self.offset_vertical_right = abs(self.projection_right[1][2])
		self.offset_vertical_left = abs(self.projection_left[1][2])
		self.full_fov_vertical_right = math.atan((1+self.offset_vertical_right)/self.projection_right[1][1])
		self.full_fov_vertical_left = math.atan((1+self.offset_vertical_left)/self.projection_right[1][1])
		print('right eye view aspect should be %f'%(self.full_fov_horizon_right/self.full_fov_vertical_right))
		print('left eye view aspect should be %f'%(self.full_fov_horizon_left/self.full_fov_vertical_left))

	def update_renderer(self,right_image,left_image):
		if self.renderer is not None:
			self.renderer.update_image(right_image[:self.right_vertical_range,-1*self.right_horizon_range:,:],left_image[:self.left_vertical_range,:self.left_horizon_range,:])

	def create_renderer(self,right_image,left_image,w=None,h=None):
		self.calculate_camera_info()
		r_h,r_w,r_c = right_image.shape
		l_h,l_w,l_c = left_image.shape
		self.right_horizon_range = int(r_w/(1+self.offset_horizon_right))
		self.left_horizon_range = int(l_w/(1+self.offset_horizon_left))
		self.right_vertical_range = int(r_h/(1+self.offset_vertical_right))
		self.left_vertical_range = int(l_h/(1+self.offset_vertical_left))
		if self.right_horizon_range%2==1:
			self.right_horizon_range += 1
		if self.left_horizon_range%2==1:
			self.left_horizon_range += 1
		if self.right_vertical_range%2==1:
			self.right_vertical_range += 1
		if self.left_vertical_range%2==1:
			self.left_vertical_range += 1
		print('right clip shape: %d * %d'%(self.right_horizon_range,self.right_vertical_range))
		print('left clip shape: %d * %d'%(self.left_horizon_range,self.left_vertical_range))
		width,height = self.vr.getRecommendedRenderTargetSize()
		print('RecommendedRenderTargetSize : %d,%d'%(width,height))
		if w==None or h==None:
			print('use RecommendedRenderTargetSize')
			self.renderer = vive_renderer(self,width,height,width,height)
		elif w==0 or h==0:
			print('use clipped size')
			self.renderer = vive_renderer(self,self.right_horizon_range,self.right_vertical_range,self.left_horizon_range,self.left_vertical_range)
		else:
			print('use specific target size')
			self.renderer = vive_renderer(self,w,h,w,h)
		self.renderer.run()
		# self.update_renderer(right_image,left_image)
			
	def update_devices(self):
		# Iterate through the pose list to find the active devices and determine their type
		self.poses = self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, self.poses)
		for i,pose in enumerate(self.poses):
			if pose.bPoseIsValid:
				device_class = self.vr.getTrackedDeviceClass(i)
				device_class_name = self.get_device_class_name(device_class)
				device_serial = self.vr.getStringTrackedDeviceProperty(i,openvr.Prop_SerialNumber_String)
				device = self.get_device(device_serial,device_class_name)
				if device == None:
					print('add new device , %s , %s'%(device_class_name,device_serial))
					device = vive_device(self,i,device_class_name,device_serial,pose)
					self.devices_type[device_class_name].append(device)
					self.devices_list.append(device)
				
	def get_device_class_name(self,device_class):
		if (device_class == openvr.TrackedDeviceClass_Controller):
			device_class_name = 'Contoller'
		elif (device_class == openvr.TrackedDeviceClass_HMD):
			device_class_name = 'HMD'
		elif (device_class == openvr.TrackedDeviceClass_GenericTracker):
			device_class_name = 'Tracker'
		elif (device_class == openvr.TrackedDeviceClass_TrackingReference):
			device_class_name = 'Tracking Reference'
		else:
			device_class_name = 'Unknown'
		return device_class_name

	def update_poses(self):
		self.vr.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, self.poses)
		for device in self.devices_list:
			device.update_pose()

	def get_device(self,device_serial,device_class=None):
		if device_class==None:
			for device in self.devices_list:
				if device.serial == device_serial:
					return device
		else:
			for device in self.devices_type[device_class]:
				if device.serial == device_serial:
					return device
		print('device serial [%s] not found '%device_serial)
		return None

	def sample(self,num):
		for device in self.devices_list:
			device.sample(num)
		
	def init_poses(self,num):
		self.sample(num)
		for i in range(num):
			self.update_poses()
		for device in self.devices_list:
			device.init_pose_from_buffer()

class vive_glove():
	def __init__(self,dongle_id,side):
		self.dongle_id = dongle_id
		self.side = side
		self.wrist = None
		self.fingers = None
		self.rotation = None
		self.init_rotation = None

	@property
	def is_connected(self):
		return ma.IsConnected_id(self.dongle_id,self.side)

	@property
	def hand(self):
		hand_t = ma.manus_hand_t()
		ma.GetHand_id(self.dongle_id, self.side, hand_t)
		return hand_t
	
	@property
	def battery_level(self):
		out = ma.uint8_arr(1)
		ma.GetBatteryLevel_id(self.dongle_id, self.side, out)
		return out[0]
	
	@property
	def battery_voltage(self):
		out = ma.uint16_arr(1)
		ma.GetBatteryVoltage_id(self.dongle_id, self.side, out)
		return out[0]

	@property
	def signal_strength(self):
		out = ma.int16_arr(1)
		ma.GetBatteryVoltage_id(self.dongle_id, self.side, out)
		return out[0]

	def set_vibration(self,power,ms):
		p = min(1.0,max(0.0,power))
		ma.SetVibration_id(self.dongle_id,self.side,p,ms)

	def update_pose(self):
		if self.is_connected:
			hand_t = self.hand
			wrist_quat = hand_t.wrist
			self.wrist = wrist_quat
			try:
				self.rotation = R.from_quat([wrist_quat.x,wrist_quat.y,wrist_quat.z,wrist_quat.w])
			except ValueError:
				print('zero norm quaternions')
			self.fingers = hand_t.raw.finger_sensor

	def init_pose(self,success_times,max_times):
		success = 0
		hand_sum_quat = ma.quat_t()
		for i in range(max_times):
			if self.is_connected:
				success += 1
				self.update_pose()
				wrist_quat = self.wrist
				hand_sum_quat.x += wrist_quat.x
				hand_sum_quat.y += wrist_quat.y
				hand_sum_quat.z += wrist_quat.z
				hand_sum_quat.w += wrist_quat.w
				if success>=success_times:
					self.init_rotation = R.from_quat([hand_sum_quat.x,hand_sum_quat.y,hand_sum_quat.z,hand_sum_quat.w])
					break
		

class vive_manus():
	def __init__(self):
		# init 
		print('init Manus ...')
		ma.Init()
		time.sleep(3)
		# get dongle id

		p = ma.uint32_arr(10)
		num = ma.GetDongleIDs(p,10)
		print("number of dongle is %d"%num)
		if num!=0:
			ret = ma.GetDongleIDs(p,num)
			print("ret=%d"%ret)
		else:
			num = 10
		self.gloves_id = {}
		self.gloves_list = []
		for i in range(num):
			print('add dongle id %d'%p[i])
			right_glove = vive_glove(p[i],ma.GLOVE_RIGHT)
			left_glove = vive_glove(p[i],ma.GLOVE_LEFT)
			self.gloves_id[p[i]] = (right_glove,left_glove)
			self.gloves_list.append(right_glove)
			self.gloves_list.append(left_glove)

		# set coordinate system
		ma.SetCoordinateSystem(ma.COOR_Y_UP, ma.COOR_RIGHT_HANDED)

	def __del__(self):
		ma.Exit()

	def get_glove(self,dongle_id,side):
		if dongle_id in self.gloves_id:
			pair = self.gloves_id[dongle_id]
		if side == 'r':
			return pair[0]
		elif side == 'l':
			return pair[1]
		else:
			print('side is not r or l ')
			raise Exception

	def update_poses(self):
		for glove in self.gloves_list:
			glove.update_pose()

	def init_poses(self,success_times,max_times):
		for glove in self.gloves_list:
			glove.init_pose(success_times,max_times)


class vive_robot():
	def __init__(self,vive,manus,id_reference1,id_reference2,id_headset,id_tracker_elbow_r=None,id_tracker_wrist_r=None,id_tracker_elbow_l=None,id_tracker_wrist_l=None):
		### Vive OpenVR
		self.vive = vive
		self.reference1 = self.refresh_vive_device(id_reference1,"Tracking Reference",3,0.5)
		self.reference2 = self.refresh_vive_device(id_reference2,"Tracking Reference",3,0.5)
		self.headset = self.refresh_vive_device(id_headset,"HMD",3,0.5)
		self.tracker_elbow_r = self.refresh_vive_device(id_tracker_elbow_r,"Tracker",3,0.5)
		self.tracker_wrist_r = self.refresh_vive_device(id_tracker_wrist_r,"Tracker",3,0.5)
		self.tracker_elbow_l = self.refresh_vive_device(id_tracker_elbow_l,"Tracker",3,0.5)
		self.tracker_wrist_l = self.refresh_vive_device(id_tracker_wrist_l,"Tracker",3,0.5)
		### Manus
		self.manus = manus
		self.glove_r = self.manus.gloves_list[0]
		self.glove_l = self.manus.gloves_list[1]
		### joints
		self.neck_euler = [0,0,0]
		self.arm_joints = [0,0,0,0,0,0,0]
		self.finger_joints = {}
		self.finger_joints['little'] = [0,0] 
		self.finger_joints['ring'] = [0,0] 
		self.finger_joints['middle'] = [0,0] 
		self.finger_joints['index'] = [0,0] 
		self.finger_joints['thumb'] = [0,0] 

	def refresh_vive_device(self,device_id,device_type,times,cycle):
		for i in range(times):
			device = self.vive.get_device(device_id,device_type)
			if device is not None:
				return device
			else:
				print('wait %f seconds ,try to update devices ...'%cycle)
				time.sleep(cycle)
				self.vive.update_devices()
		return None
	
	def init_pose(self):
		print('init pose...')
		self.vive.init_poses(10)
		self.manus.init_poses(10,100)

	def update_head(self):
		r_head_relative = R.from_quat([0,0,0,1])
		if self.headset is not None and self.headset.connected:
			r_head_relative = self.headset.init_rotation.inv()*self.headset.rotation
			head_relative_euler = r_head_relative.as_euler('zyx')
			# print('head_relative_euler')
			# print(head_relative_euler)
			self.neck_euler[0] = angle_convert(head_relative_euler[0]) #z
			self.neck_euler[1] = angle_convert(head_relative_euler[1]) #y
			self.neck_euler[2] = angle_convert(head_relative_euler[2]) #x

	def update_right_arm(self):
		### elbow
		if self.tracker_elbow_r is not None and  self.tracker_elbow_r.connected:
			r_elbow_relative = self.tracker_elbow_r.init_rotation.inv()*self.tracker_elbow_r.rotation
			euler_elbow_relative = r_elbow_relative.as_euler('ZXY') # Z:button-up Y;button-light X:button-side
			# print('euler_elbow_relative')
			# print(euler_elbow_relative)
			self.arm_joints[0] = angle_convert(euler_elbow_relative[0])
			self.arm_joints[1] = angle_convert(euler_elbow_relative[1])
			self.arm_joints[2] = angle_convert(euler_elbow_relative[2])
		### wrist
		if self.tracker_wrist_r is not None and self.tracker_wrist_r.connected:
			r_wrist_relative = self.tracker_wrist_r.init_rotation.inv()*self.tracker_wrist.rotation
			r_wrist_relative2elbow = r_elbow_relative.inv()*r_wrist_relative
			euler_wrist = self.tracker_wrist_r.rotation.as_euler('ZXY')
			euler_wrist_relative = r_wrist_relative.as_euler('ZXY')
			euler_wrist_relative2elbow = r_wrist_relative2elbow.as_euler('ZXY') # X not use
			# print('euler_wrist')
			# print(euler_wrist)
			# print('euler_wrist_relative')
			# print(euler_wrist_relative)
			# print('euler_wrist_relative2elbow')
			# print(euler_wrist_relative2elbow)
			self.arm_joints[3] = angle_convert(euler_wrist_relative2elbow[0])
			self.arm_joints[4] = angle_convert(euler_wrist_relative2elbow[2])
		if self.glove_r.is_connected:
			try:
				base_matrix = R.from_dcm([
							[-1,0,0],
							[0,0,-1],
							[0,-1,0]
						])
				r_hand = self.glove_r.rotation*base_matrix.inv()
				r_hand_init = self.glove_r.init_rotation*base_matrix.inv()
				r_hand_relative = r_hand_init.inv()*r_hand
				r_hand_relative2wrist = r_wrist_relative.inv()*r_hand_relative
				euler_hand = r_hand.as_euler('ZXY') # X:left-right Y:front-back Z:arm-rotate 
				euler_hand_relative = r_hand_relative.as_euler('ZXY')
				euler_hand_relative2wrist = r_hand_relative2wrist.as_euler('XZY')
				# print('euler_hand')
				# print(euler_hand)
				# print('euler_hand_relative')
				# print(euler_hand_relative)
				# print('hand_euler_relative2wrist')
				# print(euler_hand_relative2wrist)
				self.arm_joints[5] = angle_convert(euler_hand_relative2wrist[0])
				self.arm_joints[6] = angle_convert(euler_hand_relative2wrist[1])
			except Exception as e:
				print(e)
			self.finger_joints['little'][0] = self.glove_r.fingers[0]
			self.finger_joints['little'][1] = self.glove_r.fingers[1]
			self.finger_joints['ring'][0] = self.glove_r.fingers[2]
			self.finger_joints['ring'][1] = self.glove_r.fingers[3]
			self.finger_joints['middle'][0] = self.glove_r.fingers[4]
			self.finger_joints['middle'][1] = self.glove_r.fingers[5]
			self.finger_joints['index'][0] = self.glove_r.fingers[6]
			self.finger_joints['index'][1] = self.glove_r.fingers[7]
			self.finger_joints['thumb'][0] = self.glove_r.fingers[8]
			self.finger_joints['thumb'][1] = self.glove_r.fingers[9]

	def update_left_arm(self):
		pass

	def update_poses(self):
		self.vive.update_poses()
		self.manus.update_poses()
		self.update_head()
		self.update_right_arm()
		self.update_left_arm()

	# def update_poses(self):
	# 	r_head_relative = R.from_quat([0,0,0,1])
	# 	r_elbow_relative = R.from_quat([0,0,0,1])
	# 	r_wrist_relative = R.from_quat([0,0,0,1])
	# 	self.vive.update_poses()
	# 	### head
	# 	if self.headset is not None and self.headset.connected:
	# 		r_head_relative = self.headset.init_rotation.inv()*self.headset.rotation
	# 		head_relative_euler = r_head_relative.as_euler('zyx')
	# 		# print('head_relative_euler')
	# 		# print(head_relative_euler)
	# 		self.neck_euler[0] = angle_convert(head_relative_euler[0]) #z
	# 		self.neck_euler[1] = angle_convert(head_relative_euler[1]) #y
	# 		self.neck_euler[2] = angle_convert(head_relative_euler[2]) #x
	# 	### elbow
	# 	if self.tracker_elbow is not None and  self.tracker_elbow.connected:
	# 		r_elbow_relative = self.tracker_elbow.init_rotation.inv()*self.tracker_elbow.rotation
	# 		euler_elbow_relative = r_elbow_relative.as_euler('ZXY') # Z:button-up Y;button-light X:button-side
	# 		# print('euler_elbow_relative')
	# 		# print(euler_elbow_relative)
	# 		self.arm_joints[0] = angle_convert(euler_elbow_relative[0])
	# 		self.arm_joints[1] = angle_convert(euler_elbow_relative[1])
	# 		self.arm_joints[2] = angle_convert(euler_elbow_relative[2])
	# 	### wrist
	# 	if self.tracker_wrist is not None and self.tracker_wrist.connected:
	# 		r_wrist_relative = self.tracker_wrist.init_rotation.inv()*self.tracker_wrist.rotation
	# 		r_wrist_relative2elbow = r_elbow_relative.inv()*r_wrist_relative
	# 		euler_wrist = self.tracker_wrist.rotation.as_euler('ZXY')
	# 		euler_wrist_relative = r_wrist_relative.as_euler('ZXY')
	# 		euler_wrist_relative2elbow = r_wrist_relative2elbow.as_euler('ZXY') # X not use
	# 		# print('euler_wrist')
	# 		# print(euler_wrist)
	# 		# print('euler_wrist_relative')
	# 		# print(euler_wrist_relative)
	# 		# print('euler_wrist_relative2elbow')
	# 		# print(euler_wrist_relative2elbow)
	# 		self.arm_joints[3] = angle_convert(euler_wrist_relative2elbow[0])
	# 		self.arm_joints[4] = angle_convert(euler_wrist_relative2elbow[2])
		
	# 	# self.glove.update_pose()
	# 	self.manus.update_poses()
	# 	### hand
	# 	if self.glove.is_connected:
	# 		try:
	# 			base_matrix = R.from_dcm([
	# 						[-1,0,0],
	# 						[0,0,-1],
	# 						[0,-1,0]
	# 					])
	# 			r_hand = self.glove.rotation*base_matrix.inv()
	# 			r_hand_init = self.glove.init_rotation*base_matrix.inv()
	# 			r_hand_relative = r_hand_init.inv()*r_hand
	# 			r_hand_relative2wrist = r_wrist_relative.inv()*r_hand_relative
	# 			euler_hand = r_hand.as_euler('ZXY') # X:left-right Y:front-back Z:arm-rotate 
	# 			euler_hand_relative = r_hand_relative.as_euler('ZXY')
	# 			euler_hand_relative2wrist = r_hand_relative2wrist.as_euler('XZY')
	# 			# print('euler_hand')
	# 			# print(euler_hand)
	# 			# print('euler_hand_relative')
	# 			# print(euler_hand_relative)
	# 			# print('hand_euler_relative2wrist')
	# 			# print(euler_hand_relative2wrist)
	# 			self.arm_joints[5] = angle_convert(euler_hand_relative2wrist[0])
	# 			self.arm_joints[6] = angle_convert(euler_hand_relative2wrist[1])
	# 		except Exception as e:
	# 			print(e)
	# 		self.finger_joints['little'][0] = self.glove.fingers[0]
	# 		self.finger_joints['little'][1] = self.glove.fingers[1]
	# 		self.finger_joints['ring'][0] = self.glove.fingers[2]
	# 		self.finger_joints['ring'][1] = self.glove.fingers[3]
	# 		self.finger_joints['middle'][0] = self.glove.fingers[4]
	# 		self.finger_joints['middle'][1] = self.glove.fingers[5]
	# 		self.finger_joints['index'][0] = self.glove.fingers[6]
	# 		self.finger_joints['index'][1] = self.glove.fingers[7]
	# 		self.finger_joints['thumb'][0] = self.glove.fingers[8]
	# 		self.finger_joints['thumb'][1] = self.glove.fingers[9]

def show_device_information():
	vi_manus = vive_manus()
	vi_openvr = vive_openvr()
	vi_openvr.update_devices()
	for device in vi_openvr.devices_list:
		print(device)

def main(argv):
	vi_manus = vive_manus()
	vi_openvr = vive_openvr() 
	vi_robot = vive_robot(vi_openvr,vi_manus,"LHB-9E32C602","LHB-C6A58E4E","LHR-D440A806","LHR-4987D824","LHR-D85E2F6F")
	input()
	while 1:
		vi_robot.update_poses()
		for device in vi_robot.vive.devices_list:
			print(device.index)
			print(device.type)
			print(device.serial)
			print(device.position)
			print(device.rotation.as_quat())

if __name__ == '__main__':
	show_device_information()
	# main(sys.argv)
