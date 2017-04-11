'''
    Matt Tancik: 2015-1-27
    Communication class for Andor Camera Luca
    
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
import string
import traceback
import threading
from andor import *

#Define global variables
DEBUG = False
#The camera save a bmp to the path below. The webserver can pull this image locally to display.
#This is much faster than having the data streamed to the webserver.
IMAGESAVEPATH ='/media/twins_HDD/Dropbox (MIT)/Quanta/Twins/Control Software/Jarvis/www/images/camera/render.bmp'
PALETTEPATH = '/media/twins_HDD/Dropbox (MIT)/Quanta/Twins/Control Software/Jarvis/www/images/camera/colors.pal'

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
            
            self.internal_state["targetTemp"] = 5
            self.internal_state["EMCCDGain"] = 2
            self.internal_state["preAmpGain"] = 2
            self.internal_state["exposureTime"] = 200
            self.internal_state["bin"] = 1
            
            self.internal_state["CropParams"]=[1,1000,200,700]
            self.internal_state["ROI"] = self.internal_state["CropParams"]
            self.selection = set()
               


            print 'Connected to device...'
            time.sleep(0.1)
            
            t = threading.Thread(target = self.loopUpdate)
            t.start()
            
        except Exception as e:
            print 'Failed opening socket, Check device connection: ',e
            sys.exit(1)
            
    #All camera calls are made in this loop
    def loopUpdate(self):
        try:
            print 'Initializing camera...'
            self.cam = Andor()
            self.cam.SetEMGainMode(2) #Set EMgain in linear mode

            print 'Setting EMCCDGain = %f'%(self.internal_state["EMCCDGain"])
            self.cam.SetEMCCDGain(self.internal_state["EMCCDGain"])
            print 'Setting Exposure time = %.1fms'%(self.internal_state["exposureTime"])
            
            self.cam.SetExposureTime(self.internal_state["exposureTime"] / 1000.0)
            self.cam.SetImage(1,1,*self.internal_state["CropParams"])

        except Exception as e:
            print 'Failed initializing camera: ',e

        while self.running:
                try:
                    #render image unless camera command exists
                    if len(self.commandQueue) == 0:
                        self.cam.GetTemperature()
                        self.internal_state["currentTemp"] = self.cam.temperature
                        #Safety
                        if self.internal_state["currentTemp"] > -18:
                            print 'WARNING: Over Temp. Turning ON fan ...'
                            self.cam.SetFanMode(0)
                            self.internal_state["coolerStatus"] = 1;

                        self.cam.StartAcquisition()
                        

                        
                        #image proccessing by camera (faster, more reliable)
                        self.cam.SaveAsBmpOnCamera(IMAGESAVEPATH, PALETTEPATH)

                        
                        ##for image proccessing in python
                        #cam.SaveAsBmpNormalised(IMAGESAVEPATH)
                        
                        data = []
                        self.cam.GetAcquiredData(data)
                        x,x2,y,y2=self.internal_state["CropParams"]
                        data=np.array(data).reshape(x2-x+1,y2-y+1)
                        x,x2,y,y2 = self.internal_state["ROI"]
                        selectionData=data[x-1:x2,y-1:y2]
                            
                        self.internal_state["counts"] = sum(np.ravel(selectionData))
                        self.internal_state["maxCounts"] = max(np.ravel(selectionData))
                        
                        
                        
                    else:
                        cmd = self.commandQueue.pop(0)
                        print "cmd=" + cmd
                        if cmd == "exposure":
                            self.cam.SetExposureTime(self.internal_state["exposure"] / 1000.0)
                        elif cmd == "EMCCDGain":
                            self.cam.SetEMCCDGain(self.internal_state["EMCCDGain"])
                        elif cmd == "setImage":
                            curBin = self.internal_state["bin"];
                            x,y,x2,y2 = self.internal_state["CropParams"]
                            print ("bin:" + str(curBin) + " x:" +str(x) +  " x2:" + str(x2) + " y:" +str(y) +" y2:" +str(y2))
                            self.cam.SetImage(curBin,curBin,x,x2,y,y2)
                        elif cmd == "coolerOff":
                            print 'Turning OFF Fan...'
                            self.cam.SetFanMode(2)
                            self.internal_state["coolerStatus"] = 0;
                        elif cmd == "coolerOn":
                            print 'Turning ON Fan...'
                            self.cam.SetFanMode(0)
                            self.internal_state["coolerStatus"] = 1;                      
                            
                except Exception as e:
                    print 'Could not update state: ', e
                    print traceback.format_exc()
                    self.running = False
        if self.running ==False:
            self.cam.ShutDown()

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
            #self.internal_state["CropParams"] = (x, y, x2, y2)
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
            self.internal_state["ROI"] = [int(x), int(x)+int(w), int(y), int(y)+int(h)]
        except Exception as e:
            print 'Could not reset selection: ', e
            
    def resetSelection(self):
        '''
            Reset Selection
        '''
        try:
            print "Reset Selection"
            self.internal_state["ROI"] = self.internal_state["CropParams"]
        except Exception as e:
            print 'Could not reset selection: ', e

    def STOP(self):

        try:
            print 'Stopping camera'
            self.cam.ShutDown()
            self.running = False
        except Exception as e:
            print 'Could not stop', e
            

    def METHODSAVAILABLE():

        return ''
