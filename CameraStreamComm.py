'''
    Matt Tancik: 2015-1-27
    Communication class for Andor Camera

    Adding ability to stream directly via ffmpeg
    
    Commands to camera are added to self.commandQueue and are called after the current image acquisition
    is complete. The update function does not do anything. All of the camera calls are done in a seperate
    looping thread. This allows for faster image updates.

    Available set methods can be found in METHODSAVAILABLE, also callable from the server.

'''


import socket
import time
import sys
import os
import numpy as np
import subprocess as sp
import string
import traceback
import threading
import matplotlib.pyplot as plt
from pyandor.andor import *

#Define global variables
DEBUG = False
#The camera save a bmp to the path below. The webserver can pull this image locally to display.
#This is much faster than having the data streamed to the webserver.
IMAGESAVEPATH = '/Dropbox/Quanta/Software/GitHub/Jarvis/www/images/camera/render.bmp'
PALETTEPATH = '/Dropbox/Quanta/Software/GitHub/Jarvis/www/images/camera/colors.pal'
FFMPEG_BIN = "ffmpeg"

class Comm:
    def __init__(self):
        try:
            self.commandQueue = []
        
            self.running = True
            self.internal_state = {}
            self.internal_state["currentTemp"] = 25
            self.internal_state["coolerStatus"] = 1
            self.internal_state["image"] = []
            self.internal_state["counts"] = 0
            self.internal_state["maxCounts"] = 0
            
            self.internal_state["targetTemp"] = 20
            self.internal_state["EMCCDGain"] = 0
            self.internal_state["preAmpGain"] = 0
            self.internal_state["exposureTime"] = 200
            self.internal_state["bin"] = 1
            
            self.cropParams = (1,1,512,512)
            self.selection = set()

            self.cam = Andor()
            self.cam.SetSingleScan()
            self.cam.SetAcquisitionMode(1)
            self.cam.SetShutter(1,1,0,0)
            self.cam.SetPreAmpGain(self.internal_state["preAmpGain"])
            self.cam.SetEMCCDGain(self.internal_state["EMCCDGain"])
            self.cam.SetExposureTime(self.internal_state["exposureTime"] / 1000.0)
            self.cam.SetCoolerMode(0)
            self.cam.CoolerOFF()
            #self.cam.SetTemperature(self.internal_state["targetTemp"])

            print 'Connected to device...'
            time.sleep(0.1)
            


            '''
            #working code that outputs to mp4 file
            command = [ FFMPEG_BIN,
                    '-y', # (optional) overwrite output file if it exists
                    '-f', 'rawvideo',
                    '-vcodec', 'rawvideo',
                    '-s', '512x512', # size of one frame
                    '-pix_fmt', 'rgb24',
                    '-r', '24', # frames per second
                    '-i', '-', # The imput comes from a pipe
                    '-an', # Tells FFMPEG not to expect any audio
                    '-vcodec', 'mpeg4',
                    'my_output_videofile.mp4' ]
            '''

            command = [ FFMPEG_BIN,
                    '-f', 'rawvideo',
                    '-vcodec', 'rawvideo',
                    '-s', '512x512', # size of one frame
                    '-pix_fmt', 'rgb24',
                    '-i', '-', # The imput comes from a pipe
                    '-b', '800k',
                    '-r', '30', # frames per second
                    '-an', # Tells FFMPEG not to expect any audio
                    '-f', 'mpeg2video',
                    '-video_size', '512x512',
                    'http://127.0.0.1:8082/yourpassword/512/512/' ]


            '''
            command = [ "ffmpeg", "-y", 
            "-loglevel", "warning", "-i", "-",
            "-vcodec", "rawvideo", "-f", "mpeg1video",
            "-pix_fmt", "rgb24",
            "-ar", "44100", 
            "http://127.0.0.1:8082/yourpassword/512/512/"]
            '''
            self.pipe = sp.Popen( command, stdin=sp.PIPE, stderr=sp.PIPE)
            #a = np.ones((512, 512, 3), dtype=np.uint8)*255
            #self.pipe.stdin.write(a.tostring())
            t = threading.Thread(target = self.loopUpdate)
            t.start()
            
        except Exception as e:
            print 'Failed opening socket, Check device connection: ',e
            sys.exit(1)
            
    #All camera calls are made in this loop
    def loopUpdate(self):
        while self.running:
                try:
                    #render image unless camera command exists
                    if len(self.commandQueue) == 0:
                        self.cam.GetTemperature()
                        self.internal_state["currentTemp"] = self.cam.temperature
                        self.internal_state["coolerStatus"] = self.cam.IsCoolerOn()
                        
                        print "loop starting acquisition"
                        self.cam.StartAcquisition()

                        
                        #image proccessing by camera (faster, more reliable)
                        #
                        #self.cam.SaveAsBmpOnCamera(IMAGESAVEPATH, PALETTEPATH)

                        #print np.array(pic.getdata()).reshape(pic.size[0], pic.size[1], 3)
                        ##for image proccessing in python
                        #self.cam.SaveAsBmpNormalised(IMAGESAVEPATH)
                        
                        #selectionData = []
                        #print "loop get data"
                        data = []
                        #self.cam.GetAcquiredData(data)

                        #print len(data)
                        #npdata=np.array(data).reshape((512,512,3))
                        #print npdata
                        
                        #self.cam.SaveAsBmp(IMAGESAVEPATH)

                        #if self.selection:
                        #    for i in self.selection:
                        #        selectionData.append(data[i])
                        #else:
                        #    selectionData = data
                            
                        #self.internal_state["counts"] = sum(selectionData)
                        #self.internal_state["maxCounts"] = max(selectionData)
                        #time.sleep(1)
                        #print "loop done"
                        data=self.cam.AcquireImage()
                        self.pipe.stdin.write( data.tostring() )

                        #self.cam.SaveAsBmpOnCamera(IMAGESAVEPATH, PALETTEPATH)
                        
                    else:
                        cmd = self.commandQueue.pop(0)
                        print "cmd=" + cmd
                        if cmd == "temp":
                            self.cam.SetTemperature(self.internal_state["targetTemp"])
                        elif cmd == "coolerOn":
                            self.cam.CoolerON()
                        elif cmd == "coolerOff":
                            self.cam.CoolerOFF()
                        elif cmd == "exposure":
                            self.cam.SetExposureTime(self.internal_state["exposure"] / 1000.0)
                        elif cmd == "preAmpGain":
                            self.cam.SetPreAmpGain(self.internal_state["preAmpGain"])
                        elif cmd == "EMCCDGain":
                            self.cam.SetEMCCDGain(self.internal_state["EMCCDGain"])
                        elif cmd == "setImage":
                            curBin = self.internal_state["bin"];
                            x,y,x2,y2 = self.cropParams
                            print ("bin:" + str(curBin) + " x:" +str(x) +  " x2:" + str(x2) + " y" +str(y) +" y2" +str(y2))
                            self.cam.SetImage(curBin,curBin,x,x2,y,y2)                            
                            
                except Exception as e:
                    print 'Could not update state: ', e
                    print traceback.format_exc()
                    self.running = False

    def UPDATE(self):
        '''
            Updates all internal state variables
        '''

    def targetTemp(self, value):
        '''
            Set temperature of Camera
        '''
        try:
            print "setting temperature to " + value
            self.commandQueue.append("temp")
            self.internal_state["targetTemp"] = int(value)
        except Exception as e:
            print 'Could not update state: ', e

    def setCooler(self, value):
        '''
            Turn camera cooler on or off
        '''
        try:
            if int(value) == 1:
                print "Turning cooler on"
                self.commandQueue.append("coolerOn")
            else:
                print "Turning cooler off"
                self.commandQueue.append("coolerOff")
        except Exception as e:
            print 'Could not update state: ', e

    def exposure(self, value):
        '''
            Set camera exposure time in ms
        '''
        try:
            print "setting exposure to " + value
            self.internal_state["exposure"] = int(value)
            self.commandQueue.append("exposure")
        except Exception as e:
            print 'Could not update state: ', e

    def preAmpGain(self, value):
        '''
            Set preAmp Gain
        '''
        try:
            print "setting preAmp Gain to " + value
            self.internal_state["preAmpGain"] = int(value)
            self.commandQueue.append("preAmpGain")
        except Exception as e:
            print 'Could not update state: ', e

    def EMCCDGain(self, value):
        '''
            Set EMCCD Gain
        '''
        try:
            print "setting EMCC Gain to " + value
            self.internal_state["EMCCDGain"] = int(value)
            self.commandQueue.append("EMCCDGain")
        except Exception as e:
            print 'Could not update state: ', e
            
    def setBin(self, value):
        '''
            Set bin level
        '''
        try:
            print "setting bin level to " + value
            self.internal_state["bin"] = int(value)
            x, y, x2, y2 = self.cropParams
            self.setCrop(x, y, x2, y2)
        except Exception as e:
            print 'Could not update state: ', e
            
    def setCrop(self, x, y, x2, y2):
        '''
            Set crop
        '''
        try:
            print "cropping"
            x, y, x2, y2 = int(x), int(y), int(x2), int(y2)
            curBin = self.internal_state["bin"]
            print x
            print x2
            #Some really wierd stuff going on here. Onle certian crop dimensions allowed. 
            #With some trial and error the following seems to work.
            if (x2-x) % curBin != curBin - 1:
                x = x+((x2-x) % curBin)+1
            if (y2-y) % curBin != curBin - 1:
                y = y+((y2-y) % curBin)+1
            self.cropParams = (x, y, x2, y2)
            self.commandQueue.append("setImage")
        except Exception as e:
            print 'Could not update state: ', e
            
    def addSelection(self, x, y, w, h):
        '''
            Add to the selection
        '''
        try:
            #each selection array indiced are calculated and added to the self.selection set
            print "Adding to selection"
            W = (self.cropParams[2] - self.cropParams[0]) / self.internal_state["bin"]
            H = (self.cropParams[3] - self.cropParams[1]) / self.internal_state["bin"]
            x = int(int(x)/512.0 * W)
            y = int(int(y)/512.0 * H)
            h = int(int(h)/512.0 * H)
            w = int(int(w)/512.0 * W)
            for j in range(h):
                for i in range(w):
                    self.selection.add(W * (j + y) + x + i)
        except Exception as e:
            print 'Could not reset selection: ', e
            
    def resetSelection(self):
        '''
            Reset Selection
        '''
        try:
            print "Reset Selection"
            self.selection = set()
        except Exception as e:
            print 'Could not reset selection: ', e

    def STOP(self):

        try:
            self.pipe.stdin.flush()
            self.pipe.terminate()
            self.cam.ShutDown()
            self.running = False
        except Exception as e:
            print 'Could not stop', e
            

    def METHODSAVAILABLE():

        return ''
