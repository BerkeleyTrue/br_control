#!/usr/bin/env python
import roslib; roslib.load_manifest('br_swarm_rover')
import rospy
from std_msgs.msg import String

import cv2

import socket
import array
import time

class RovCam(): 
    def __init__(self, data):
        self.host = '192.168.1.100'
        self.port = 80
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.max_tcp_buffer = 2048
        self.max_image_buffer = 231072
        self.image_ptr = 0
        self.tcp_ptr = 0
        self.image_start_position = 0
        self.image_length = 0
        #self.image_buffer = array.array('c')
        self.init_connection(data)     #image id is taken from data 

    def init_connection(self, data):
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
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.video_socket.connect((self.host, self.port))
        self.video_socket.setblocking(1)

    def disconnect_video(self):
        self.video_socket.close()

    def write_cmd(self, extra_input):	
#	    Robot's Control Packets
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

    def display_image(self):
 	# For now just get one frame, we have to make this a loop of course
        print 'Get video frame!'
        data = 0 
        ldata = array.array('c')
       # ldata = []
        start = ''
        while data == 0:
            data = self.video_socket.recv(self.max_tcp_buffer)
            list_data = list(data)
            m_c = array.array('c')
            m_c.extend (list_data[0:4])

            if (start == ''):
                start = 'first'
            else:
                start = m_c.tostring()
            if (start == 'MO_V'):
                break
            else:
                ldata.extend(list_data)

            data = 0 

        # Write image to "test.jpg"
        img = ldata[36:]
        #img = ''.join(img)
        print type(img)
        print len(img)
        jpgfile = open('test.jpg', 'wb')
        for i in img:
            jpgfile.write(i)
           # print i 
        jpgfile.close()
 
        image = cv2.imread('test.jpg', 1)
        print type(image)
        #image = image[:,-1::-1,:]
        #image = image * 1
        #cv2.imshow(u'Image', image)
        #time.sleep(1) 
        #cv2.waitKey()
        #cv2.destroyWindow('test.jpg')

#     def get_raw_image_buffer(self):        # byte, returns image data
#         return self.image_buffer

    def get_image_length(self):            # int
        return self.image_length
        
    def get_image_start_position(self):    #int
        return self.image_start_position

    def set_image_start_position(self, start):   # int
        self.image_start_position = start
        
    def set_image_length(self, data):
        self.image_length = data

    def img_start(self, start):
        return (start[0] == 'M' and start[1] == 'O' and start[2] == '_' and start[3] == 'V')
       
    def receive_image(self):   
        data = ''
        ldata = array.array('c')
        start = ''
        found_start = False
        found_end = False
        start_pos = 0 #current position in ldata
        end_pos = 0 #position of the end of frame in the current array of data
        while (not found_end):
            data = self.video_socket.recv(self.max_tcp_buffer)
            if(data == ''):
                continue
                #check for the message start token 'MO_V'
            for i in range(0, len(data)-2):
                #try
                if (data[i:(i+3)] == 'MO_V'):
                    if not found_start:
                        found_start = True
                        print "start of picture found"
                        start_pos = i
                        #crop the data only include stuff after the
                        #start token.
                        data = data[start_pos:len(data)]
                        break
                    elif not found_end:
                        found_end = True
                        print "end of picture found"
                        end_pos = i
                        break
#                 catch e
#                    disp(e);
#                    disp(['length of data: ' num2str(length(data))]);
#                    disp(['try to access: ' num2str(i) ' thru ' num2str(i+3) ]);
            #if you have found the start but not the end (in the
            #middle of a image frame)
            if (found_start and not found_end):
                #add the recent data to ldata
                ldata.extend(list(data))
                print "adding recent data"
            if found_end:
               ldata.extend(list(data[0:end_pos]))
               print "adding data from 0 to end"
            data = ''
            time.sleep(1)
        l_len = len(ldata)
        image_buffer = ldata[36:l_len]
