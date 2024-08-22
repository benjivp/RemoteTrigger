print('Importing necessary packages')

from ultralytics import YOLO
from cv2 import VideoCapture, imshow, waitKey, destroyAllWindows
from time import time, sleep
from rtmidi import MidiOut, MidiIn
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF
from waiting import wait
from pygrabber.dshow_graph import FilterGraph

print('Packages imported')

print('Generating camera device list')
#Retrieving all connected devices
devices = FilterGraph().get_input_devices()
#Initializing empty list
available_cameras = {}
#Creating list of available devices
for device_index, device_name in enumerate(devices):
    available_cameras[device_index] = device_name

#Prompting user to select the connected camera to use in movement identification
if available_cameras:
    print('Found device(s): ', available_cameras)
    user_input = input('Enter device number or \'q\' to quit: ')
    if user_input == 'q':
        print('ok bye bye!')
        quit()
    else:
        video = VideoCapture(int(user_input))
    print('Connection established')
else:
    print('No available devices. Please ensure that a camera is connected.')
    quit()

print('Preparing functions and variables')

#Loading pretrained YOLOv8n pose detection model
pose_det = YOLO('yolov8n-pose.pt')

#Buffer time (aka minimum time) allows for consistency in data points, regardless of performance
buffer_time = 0.18

#Setting up necessary utilities
prev_time = time() #For implementing buffer
curr_time = 0 #For implementing buffer
frame_time = 0 #For implementing buffer
i = 1 #For counting frames
cooldown_R = False #For right hand cooldown period
cooldown_L = False #For left hand cooldown period
r = 0 #For counting frames during right hand cooldown period
l = 0 #For counting frames during left hand cooldown period
tester = True #For latency test
resp_received = False #For latency test

#Functions for handling MIDI input from PD during latency test
def handle_input(event, data=None):
    global resp_received, rec_time
    rec_time = time()
    message, deltatime = event
    if message[1] == 10:
        resp_received = True

print('Functions and variables prepared')

print('Establishing connection with PD through MIDI')

#Retrieving list of MIDI ports for configuration
midiout = MidiOut()
midiin = MidiIn()
available_ports_out = midiout.get_ports()
available_ports_in = midiin.get_ports()

#Prompting user to select output MIDI port
if available_ports_out:
    print('OUTPUT - Found ports: ', available_ports_out)
    user_input = input('Enter port number or \'q\' to quit: ')
    if user_input == 'q':
        print('ok bye bye!')
        quit()
    else:
        midiout.open_port(int(user_input))
    print('Connection established')
else:
    print('No available ports. Please ensure that a virtual MIDI port is available')
    quit()

#Prompting user to select input MIDI port (for latency test)
if available_ports_in:
    print('INPUT - Found ports: ', available_ports_in)
    user_input = input('Enter port number or \'q\' to quit: ')
    if user_input == 'q':
        print('ok bye bye!')
        quit()
    else:
        midiin.open_port(int(user_input))
        midiin.set_callback(handle_input)
    print('Connection established')
else:
    print('No available ports. Please ensure that a virtual MIDI port is available')
    quit()

#Testing roundtrip latency of MIDI signal
print('Testing latency through MIDI')
lat_time = time()
midiout.send_message([NOTE_ON, 0, 127])
print('Waiting for MIDI response')
wait(lambda: resp_received, timeout_seconds=5, waiting_for='MIDI response')
rndtrip_time = rec_time - lat_time
print(f'Roundtrip latency for MIDI message: {rndtrip_time} s.')
sleep(3) #To allow user time to read latency test result
print('Closing MIDI input port')
#Closing input MIDI port, no longer necessary for general usage
midiin.close_port()
del midiin

print('Beginning movement identification. To terminate, press \'q\' on the live video window.')
sleep(3) #To allow user time to read how to quit the program
#Loop to run frame-by-frame analysis on video source
#If livecam use True, if video file use video.isOpened()
while (True): #Only end at break point when live camera is closed
    #Isolating video frame
    ret, frame = video.read()
    if ret:
        #Using counter i to skip frames to save on computation
        if (i % 3) == 0:
            #Displaying the current frame
            imshow('Webcam', frame)
            #Run inference on current frame
            #Parameter explanation:
                #Soure: What is being infered on, in this case it is the current frame defined above
                #Show: Toggle for displaying the outputted frames with keypoints displayed (False to reduce latency)
                #Conf: The minimum confidence score to consider the detected pose as valid
                #Max_det: The maximum number of people to detect (Keeping at 1 so as not to be triggered by other people)
                #Save: Toggle for saving the annoted frame to memory (Currenlty names each frame the same, so only the last frame is saved when live due to overwrites)
                #Stream: Changes the output format from a list to a generator
            results = pose_det(source=frame, show=False, conf=0.55, max_det=1, save=False, stream=False)
            curr_time = time()
            frame_time = curr_time - prev_time

            if i > 3:
                #Setting frame time to buffer time to allow for more consistent processing and analysis
                if frame_time < buffer_time:
                    sleep(buffer_time - frame_time)
                    frame_time = buffer_time

                keypoints = (results[0].keypoints).xy[0].numpy() #Retrieving keypoints from YOLOv8 pose detection output

                #Incrementing cooldown frames for each hand
                if cooldown_R:
                    if r < 5:
                        print('R cooldown...')
                        r = r + 1
                    else:
                        cooldown_R = False
                if cooldown_L:
                    if l < 5:
                        print('L cooldown...')
                        l = l + 1
                    else:
                        cooldown_L = False

                if keypoints.size != 0:
                    if (keypoints[3][1] != 0 or keypoints[4][1] != 0) and (keypoints[5][1] != 0 or keypoints[6][1] != 0) and (keypoints[9][1] != 0 or keypoints[10][1] != 0): #Ensuring at least one of each ear, shoulder and hand is visible 
                        if cooldown_R == False: #No analysis necessary if in cooldown
                            if keypoints[10][1] != 0:
                                if (max(keypoints[3][1], keypoints[4][1]) - keypoints[10][1]) >= (max(keypoints[5][1], keypoints[6][1]) - max(keypoints[3][1], keypoints[4][1])): #Trigger when distance between hand and ear > distance between ear and shoulder
                                    print('right hand up!')
                                    midiout.send_message([NOTE_ON, 60, 64]) #send MIDI note 60 on to PD
                                    midiout.send_message([NOTE_OFF, 60, 0]) #send MIDI note 60 off to PD
                                    cooldown_R = True #Trigger cooldown period
                                    r = 0 #Set cooldown frames to 0
                        if cooldown_L == False: #No analysis necessary if in cooldown
                            if keypoints[9][1] != 0:
                                if (max(keypoints[3][1], keypoints[4][1]) - keypoints[9][1]) >= (max(keypoints[5][1], keypoints[6][1]) - max(keypoints[3][1], keypoints[4][1])): #Trigger when distance between hand and ear > distance between ear and shoulder
                                    print('left hand up!')
                                    midiout.send_message([NOTE_ON, 61, 64]) #send MIDI note 61 on to PD
                                    midiout.send_message([NOTE_OFF, 61, 0]) #send MIDI note 61 off to PD
                                    cooldown_L = True #Trigger cooldown period
                                    l = 0 #Set cooldown frames to 0
                    else:
                        print('Cannot identify')
                else:
                    print('Cannot identify')
                print(f'Frame Time: {frame_time} s')
                i = i + 1 #Increment frame number
                prev_time = time()
            else:
                i = i + 1
        else:
            i = i + 1

        #Set hotkey to stop the video stream when "show" is set to True (q in this case)
        if waitKey(1) == ord('q'):
            break
    else:
        break

#Closing video connection and associated windows
print('Closing video feed')
video.release()
destroyAllWindows
print('Closing MIDI port connection')
midiout.close_port()
del midiout