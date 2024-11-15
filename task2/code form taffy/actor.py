import sys
from controller import Supervisor,Node
from multiprocessing.connection import Listener,Client
import numpy as np
import time
import os
import argparse
import struct

print('current path: '+os.getcwd())

def log(message):
	global print_log
	if print_log:
		global logger
		logger.send(message)

def tick():
	global tick_time
	tick_time = time.time()

def tock():
	global tick_time
	print(time.time()-tick_time)

def client_connect(address,key):
	conn = None
	while conn is None:
		try:
			conn = Client(address, authkey=key)
		except (ConnectionRefusedError,ConnectionResetError) as e:
			log(e)
			time.sleep(1)
			log('retry...')
	log('connect success')
	return conn

def listener_connect(address,key):
	listener = Listener(address, authkey=key)
	print('wait client ...')
	conn = listener.accept()
	return conn

def send_state(state):
	global address,key,conn
	log('send state')
	print('send state')
	try:
		conn.send(state)
		log(state)
		print(state)
	except ConnectionResetError as e: # catch connection error
		log(e)
		log('reset simulation')
		supervisor.simulationReset()

def recieve_command():
	global address,key,conn
	log('recieve command')
	print('recieve command')
	try:
		command = conn.recv()
	except (ConnectionResetError,EOFError) as e: # catch connection error
		log(e)
		log('reset simulation')
		supervisor.simulationReset()
	log(command)
	print(command)
	return command

def main(argv):
	### create logger connection
	global print_log
	if argv.log:
		print_log = True
		print('create logger')
		address_log = ('localhost',argv.logger_port)
		key_log = b'actor_log'
		global logger
		logger = listener_connect(address_log,key_log)
		print('logger connect')
		log('logger connect')
	else:
		print_log = False

	### create actor connection
	if not argv.empty:
		log('create actor connection')
		print('create actor connection')
		global address,key,conn
		address = ('localhost',argv.port)
		key = b'actor'
		conn = client_connect(address,key)
		log('actor connect')
		print('actor connect')
		
	### create the Robot instance.
	global supervisor
	supervisor = Supervisor()

	### get the time step of the current world.
	if argv.timerate is not None:
		timestep_rate = argv.timerate
	else:
		timestep_rate = 2
	timestep = int(supervisor.getBasicTimeStep())
	log('simulation step time is %d'%timestep)
	print('simulation step time is %d'%timestep)
	timestep *= timestep_rate
	log('controller step time is %d'%timestep)
	print('controller step time is %d'%timestep)

	### get depth camera info
	camera_node = supervisor.getFromDef('depth_camera')
	camera_position = camera_node.getPosition()
	camera_rotation = camera_node.getOrientation()

	if argv.vr:
	### enable cameras
		node_name = 'vr_camera_r'
		vr_camera_r = supervisor.getCamera(node_name)
		vr_camera_r.enable(timestep)
		log('enable camera: %s'%node_name)
		print('enable camera: %s'%node_name)

		node_name = 'vr_camera_l'
		vr_camera_l = supervisor.getCamera(node_name)
		vr_camera_l.enable(timestep)
		log('enable camera: %s'%node_name)
		print('enable camera: %s'%node_name)

	### get vr camera info
		vr_height = vr_camera_r.getHeight()
		vr_width = vr_camera_r.getWidth()
		vr_fov = vr_camera_r.getFov()

	### get or create shared image
		log('create numpy memmap')
		print('create numpy memmap')
		tmp_dir = './../../tmp/'
		if not os.path.exists(tmp_dir):            #生成了temp文件夹但是没有文件？
			os.mkdir(tmp_dir)
		filename_vr_r = tmp_dir+'vr_image_r_%d'%argv.port
		filename_vr_l = tmp_dir+'vr_image_l_%d'%argv.port
		try :
			shared_array_vr_r = np.memmap(filename_vr_r, dtype='uint8', mode='r+', shape=(vr_height,vr_width,3))
		except FileNotFoundError as e:
			log(e)
			shared_array_vr_r = np.memmap(filename_vr_r, dtype='uint8', mode='w+', shape=(vr_height,vr_width,3))
		try :
			shared_array_vr_l = np.memmap(filename_vr_l, dtype='uint8', mode='r+', shape=(vr_height,vr_width,3))
		except FileNotFoundError as e:
			log(e)
			shared_array_vr_l = np.memmap(filename_vr_l, dtype='uint8', mode='w+', shape=(vr_height,vr_width,3))

	### get devices
	motors = {}
	position_sensors = {}
	device_number = supervisor.getNumberOfDevices()
	for i in range(device_number):
		device = supervisor.getDeviceByIndex(i)
		node_name = device.getName()
		node_type = device.getNodeType()
		log('%s : %s'%(node_name,node_type))
		print('%s : %s'%(node_name,node_type))
		if node_type == Node.ROTATIONAL_MOTOR or node_type == Node.LINEAR_MOTOR: # mortors
			motors[node_name] = supervisor.getMotor(node_name)
		elif node_type == Node.POSITION_SENSOR:
			position_sensors[node_name] = supervisor.getPositionSensor(node_name)
			position_sensors[node_name].enable(timestep)

	### enable receiver
	if argv.recv:
		log('enable receiver')
		recv = supervisor.getReceiver('receiver')
		recv.enable(timestep)
	else:
		recv = None

	### get node
	log('get root and clone')
	root = supervisor.getRoot()
	root_children = root.getField('children')
	clone = supervisor.getFromDef('clone')
	if clone is not None:
		clone_children = clone.getField('children')
	else:
		clone_children = None

	# Main loop:
	# - perform simulation steps until Webots is stopping the controller
	objects = {}
	print('start loop')
	step_res = 0
	while step_res != -1:
		log('loop head')
		if argv.empty:
			step_res = supervisor.step(timestep)
			continue
		### get command	
		command = recieve_command()
		if command['type'] == 'step':
			log('step')
			step_res = supervisor.step(timestep)
			log('after step')
			### send state
			state = {}
			## save image
			if argv.vr:
				image_vr_array_r = np.frombuffer(vr_camera_r.getImage(), np.uint8).reshape((vr_height, vr_width, 4))
				shared_array_vr_r[:] = image_vr_array_r[:,:,:3]
				image_vr_array_l = np.frombuffer(vr_camera_l.getImage(), np.uint8).reshape((vr_height, vr_width, 4))
				shared_array_vr_l[:] = image_vr_array_l[:,:,:3]
				# state['images'] = {}
				# state['images']['image_vr_r'] = image_vr_array_r[:,:,:3]
				# state['images']['image_vr_l'] = image_vr_array_l[:,:,:3]
			## set touch
			touch_name = ['arm','table','Glass','Coke','Minute','LemonJuice','PineAppleJuice','Whisky','Vodka','Tequila']
			touch = {}
			for name in touch_name:
				touch[name] = False
			state['touch'] = touch
			if recv is not None:
				while recv.getQueueLength()>0:
					byte = recv.getData()
					log('receiver:')
					log(byte) 
					message = struct.unpack("10?",byte)
					log('receiver: %s , %s , %s'%(message,type(message),type(message[0])))
					recv.nextPacket()
					for i,name in enumerate(touch_name):
						if i<len(message) and message[i]:
							touch[name] = True
			## set object
			state['objects'] = {}
			for name,obj in objects.items():
				state['objects'][name] = {}
				state['objects'][name]['position'] = obj.getPosition()
				state['objects'][name]['orientation'] = obj.getOrientation()
			## set motor pos
			state['motors'] = {}
			for name,pos_sensor in position_sensors.items():
				state['motors'][name] = pos_sensor.getValue()
			state['time'] = supervisor.getTime()
			send_state(state)
		elif command['type'] == 'set motors':
			log('set motors')
			for name,pos in command['motors'].items():
				log('set mortor %s position: %s'%(name,pos))
				if name in motors:
					if pos is not None:
						motors[name].setPosition(pos)
					else:
						log('Motor %s pos is None'%name)
				else:
					log('Motor %s Not Found'%name)
		elif command['type'] == 'set objects':
			log('set objects')
			for name,pos in command['objects'].items():
				log('set object %s position: %s'%(name,pos))
				node = supervisor.getFromDef(name)
				if node is not None:
					objects[name] = node
					if pos is not None:
						if 'position' in pos:
							translation = node.getField('translation')
							translation.setSFVec3f(pos['position'])
						if 'orientation' in pos:
							rotation = node.getField('rotation')
							rotation.setSFRotation(pos['orientation'][:4])
				else:
					log('Node %s Not Found'%name)
		elif command['type'] == 'set index objects':
			log('set index objects')
			for index,pos in command['objects'].items():
				log('set %s position: %s'%(name,pos))
				node = clone_children.getMFNode(index)
				if node:
					translation = node.getField('translation')
					translation.setSFVec3f(pos)
				else:
					log('Node %s Not Found'%name)
		elif command['type'] == 'create objects':
			log('create objects')
			if clone_children is None:
				log('clone group node not found')
			else:
				for name in command['objects']:
					log('create %s '%(name))
					filename = './../../wbo/'+name+'.wbo'
					clone_children.importMFNode(-1,filename)
		elif command['type'] == 'get motor info':
			infos = {}
			for name,motor in motors.items():
				motor_info = {}
				motor_info['min position'] = motor.getMinPosition()
				motor_info['max position'] = motor.getMaxPosition()
				infos[name] = motor_info
			send_state(infos)
		elif command['type'] == 'get camera info':
			log('get camera info')
			camera_info = {}
			if args.vr:
				camera_info['vr'] = {'width':vr_width,
									'height':vr_height,
									'fov':vr_fov}
			camera_info['position'] = camera_position
			camera_info['rotation'] = camera_rotation
			send_state(camera_info)
		elif command['type'] == 'set textures':
			log('set textures')
			for name,url in command['textures'].items():
				log('set texture %s url: %s'%(name,url))
				node = supervisor.getFromDef(name)
				if node is not None:
					if url is not None:
						objects[name] = node
						field_url = node.getField('url')
						field_url.setMFString(0,url)
					else:
						log('url is None')
				else:
					log('Node %s Not Found'%name)
		elif command['type'] == 'save world':
			log('save world - %s'%command['name'])
			supervisor.worldSave(command['name'])
		elif command['type'] == 'load world':
			log('load world - %s'%command['name'])
			supervisor.worldLoad(command['name'])
		elif command['type'] == 'reload world':
			log('reload world')
			supervisor.worldReload()
		elif command['type'] == 'reset simulation':
			log('reset simulation')
			supervisor.simulationReset()
		elif command['type'] == 'reset physic':
			log('reset physic')
			supervisor.simulationResetPhysics()
		else:
			log('command type not found')
		log('loop tail')
	log('end loop')


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--log',action='store_true', help='print log')
	parser.add_argument('--empty',action='store_true', help='empty loop')
	parser.add_argument('--timerate',type=int, help='rate of simulation time')
	parser.add_argument('--host',type=str, help='host name of actor connection')
	parser.add_argument('--port',type=int, help='port of actor connection')
	parser.add_argument('--logger_host',type=str, help='host name of logger connection')
	parser.add_argument('--logger_port',type=int, help='port of logger connection')
	parser.add_argument('--recv',action='store_true', help='enable receiver')
	parser.add_argument('--vr',action='store_true', help='enable vr camera')
	args = parser.parse_args()
	print(args)
	main(args)

