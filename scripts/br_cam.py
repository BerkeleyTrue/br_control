#!/usr/bin/env python
'''
This node deals with the rover's camera. It gets image data
and publishes is so that other nodes can use it.
'''

import roslib; roslib.load_manifest('br_swarm_rover')
import rospy
from sensor_msgs.msg import CompressedImage
from sensor_msgs.msg import Image

import numpy as np

import socket
import array

class RovCam(): 
    def __init__(self, data):
        self.host = '192.168.1.100'
        self.port = 80
        self.video_socket =\
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.max_tcp_buffer = 2048
        self.max_image_buffer = 231072
        self.image_ptr = 0
        self.tcp_ptr = 0
        self.image_start_position = 0
        self.image_length = 0
        #self.bridge = CvBridge()
        self.init_connection(data)     #image id is taken from data 

    def init_connection(self, data):
        """
        Starts connection to rovers camera
        """
        # Create new socket for video
        self.connect_video()
	
        print "data in video socket: " + data

        m_c = array.array('c')
        m_c.extend(['M', 'O', '_', 'V'])
        m_c.extend('\0')
        i = 0
        while i < 10:
            m_c.extend('\0')
            i = i + 1
        m_c.extend('\x04')
        i = 0
        while i < 3:
            m_c.extend('\0')
            i = i + 1
        m_c.extend('\x04')
        i = 0
        while i < 3:
            m_c.extend('\0')
            i = i + 1
        ldata = list(data)
        id_cp = ldata[25:29]
        m_c.extend(id_cp)
        msg = m_c.tostring()
        self.video_socket.send(msg)

    def connect_video(self):	
        """
        Initiates the video socket and sets it up to blocking
        """
        self.video_socket =\
                 socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#        self.video_socket.bind((self.nic, 0))       # bind to NIC
        self.video_socket.connect((self.host, self.port))
        self.video_socket.setblocking(1)

    def disconnect_video(self):
        """
        Stops communication with the rover's camera
        """
        self.video_socket.close()

    def write_cmd(self, extra_input):	
        """
        Sends the respective commands to the robot to initiate 
        camera connection
        """
        # Robot's Control Packets
        packet_len = 26                          # length of the video buffer
        cmd_buffer = array.array('c')
        cmd_buffer.extend(['M', 'O', '_', 'V'])
        for i in range(4, packet_len+1):	
            cmd_buffer.append('\0')
        cmd_buffer[15] = '\x04'
        cmd_buffer[19] = '\x04'
        for i in range(0, 3):
            if (len(extra_input) >= 4):
                cmd_buffer[i + 22] = extra_input[i]
            else:	
                cmd_buffer[i + 22] = '\0'     #extra_input[1]
        msg = cmd_buffer.tostring()
        self.video_socket.send(msg) 

    def get_image_length(self):            # int
        """
        Returns the length of the image data gathered
        Length vairies based on data corruption and resolution
        """
        return self.image_length
        
    def get_image_start_position(self):    #int
        """
        Returns the position in the rover's data packet where the
        image data starts
        """
        return self.image_start_position

    def set_image_start_position(self, start):   # int
        """
        Set the position where the image data should start
        """
        self.image_start_position = start
        
    def set_image_length(self, data):
        """
        Set the desired length of the image data
        """
        self.image_length = data

    def img_start(self, start):
        return (start[0] == 'M' and start[1] == 'O' and start[2] == '_' and start[3] == 'V')

    def receive_image(self):   
        """
        Retrives image data coming from the rover and then
        transforms it to numpy and string data for further
        manupulation with OpenCV and Kivy and returns the final
        data
        """
        data = ''
        ldata = array.array('c')
        image_buffer = CompressedImage()
        image_buffer.format = "jpeg"
#        start = ''
        found_start = False
        found_end = False
        start_pos = 0 #current position in ldata
        #position of the end of frame in the current array of data
        end_pos = 0
        while (not found_end):
            data = self.video_socket.recv(self.max_tcp_buffer)
            if(data == ''):
                continue
            #check for the message start token 'MO_V'
            for i in range(0, len(data)-2):
                if (data[i:(i+4)] == 'MO_V'):
                    if not found_start:
                        found_start = True
                        start_pos = i
                        #crop the data only include stuff after the
                        #start token.
                        data = data[start_pos:len(data)]
                        break
                    elif not found_end:
                        found_end = True
                        end_pos = i
                        break
            #if you have found the start but not the end (in the
            #middle of a image frame)
            if (found_start and not found_end):
                #add the recent data to ldata
                ldata.extend(list(data))
            if found_end:
               ldata.extend(list(data[0:end_pos]))
            data = ''
        l_len = len(ldata)
        #### Create CompressedIamge ####
        # convert to numpy to use with OpenCV, etc.
        image_buffer.header.stamp = rospy.Time.now()
        image_buffer.data = np.array(ldata[36:l_len]).tostring()

        return image_buffer
