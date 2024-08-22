print('Importing necessary packages')

from ultralytics import YOLO
from cv2 import VideoCapture, imshow, waitKey, destroyAllWindows
from time import time, sleep
from numba import jit
from rtmidi import MidiOut, MidiIn
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF
from waiting import wait
from pygrabber.dshow_graph import FilterGraph

print('Packages imported')

print('Generating camera device list')
devices = FilterGraph().get_input_devices()
available_cameras = {}
for device_index, device_name in enumerate(devices):
    available_cameras[device_index] = device_name

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

#Setting up necessary utilities (start time, iterator, empty array, video information, array to save to .csv)
prev_time = time()
curr_time = 0
frame_time = 0
i = 1
ret, frame = video.read()
height, width, channels = frame.shape
cooldown_R = False
cooldown_L = False
r = 0
l = 0
tester = True
condition = False

def handle_input(event, data=None):
    global condition, rec_time
    rec_time = time()
    message, deltatime = event
    if message[1] == 10:
        condition = True

print('Functions and variables prepared')
print('Establishing connection with PD through MIDI')

midiout = MidiOut()
midiin = MidiIn()
available_ports_out = midiout.get_ports()
available_ports_in = midiin.get_ports()

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

print('Testing latency through MIDI')
lat_time = time()
midiout.send_message([NOTE_ON, 0, 127])
print('Waiting for MIDI response')
wait(lambda: condition, timeout_seconds=5, waiting_for='MIDI response')
rndtrip_time = rec_time - lat_time
print(f'Roundtrip latency for MIDI message: {rndtrip_time} s.')
sleep(3)
print('Closing MIDI input port')
midiin.close_port()
del midiin

print('Beginning movement identification. To terminate, press \'q\' on the live video window.')
sleep(3)
#Loop to run frame-by-frame analysis on video source
#If livecam use True, if video file use video.isOpened()
while (True):
    #Isolating video frame
    ret, frame = video.read()
    if ret:
        #Using counter i to skip two frames to save on computation
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
                #Setting frame time to buffer time to allow for more consistent processing and analysis, especially for the neural network step
                if frame_time < buffer_time:
                    sleep(buffer_time - frame_time)
                    frame_time = buffer_time

                keypoints = (results[0].keypoints).xy[0].numpy()
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
                    if (keypoints[5][1] != 0 or keypoints[6][1] != 0) and (keypoints[9][1] != 0 or keypoints[10][1] != 0):
                        if cooldown_R == False:
                            if keypoints[10][1] != 0:
                                if (max(keypoints[3][1], keypoints[4][1]) - keypoints[10][1]) >= (max(keypoints[5][1], keypoints[6][1]) - max(keypoints[3][1], keypoints[4][1])):
                                    print('right hand up!')
                                    midiout.send_message([NOTE_ON, 60, 64])
                                    midiout.send_message([NOTE_OFF, 60, 0])
                                    print('sent midi 60')
                                    cooldown_R = True
                                    r = 0
                        if cooldown_L == False:
                            if keypoints[9][1] != 0:
                                if (max(keypoints[3][1], keypoints[4][1]) - keypoints[9][1]) >= (max(keypoints[5][1], keypoints[6][1]) - max(keypoints[3][1], keypoints[4][1])):
                                    print('left hand up!')
                                    midiout.send_message([NOTE_ON, 61, 64])
                                    midiout.send_message([NOTE_OFF, 61, 0])
                                    print('sent midi 61')
                                    cooldown_L = True
                                    l = 0
                    else:
                        print('Cannot identify')
                else:
                    print('Cannot identify')
                print('Frame Time: ' + str(frame_time))
                i = i + 1
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