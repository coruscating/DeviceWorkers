'''
    Matt Tancik: 2015-01-29
    Communication class Temperature and Humidity sensor.
    Type: Arduino
    
'''


import serial
import time
import sys
import os
import threading
import datetime
import traceback

#Define global variables
DEBUG = False
DEVICELOC = '/dev/X88/TempAndHumi'
LOGFILE = '/media/Wigner-1TB/Dropbox (MIT)/Quanta/Data/Logs/temp_humi.log'

class Comm:
    def __init__(self):
        
        try:
            #Initialize arduino communication
            self.arduino = serial.Serial(DEVICELOC, 9600, timeout =1)
            print "connected"
            self.running = True
            
            #Variable to monitor/store shutter states
            self.internal_state = {}
            self.internal_state["temperature"] = 0
            self.internal_state["humidity"] = 0
            self.internal_state["dewPoint"] = 0
            
            t = threading.Thread(target = self.update_internal_state)
            t.start()

        except Exception as e:
            print 'Could not initialize',e
            sys.exit(1)
        
    def update_internal_state(self):
        '''
            Updates the internal state (Temp, Humidity, and Dew Point)
            returns: none
        '''
        while self.running:
            try:
                response = self.arduino.readline()
                if len(response) > 10:
                    response = response.strip().split(';')
                    self.internal_state["temperature"] = float(response[0])
                    self.internal_state["humidity"] = float(response[1])
                    self.internal_state["dewPoint"] = float(response[2])
                #if self.internal_state["temperature"] != 0:
                #    f=open(LOGFILE, 'a')
                #    f.write("%s;%s\n" %(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'), self.internal_state))
                #    f.close()
            except Exception as e:
                print 'Failed in update_internal_state: ',e
                print traceback.format_exc()
                self.running = False
                pass
    
            
    def UPDATE(self):
        '''
            Do Nothing
        '''
        pass

    def STOP(self):
        '''
            Closes serial communication  
        '''  
        self.running = False
        self.arduino.close()
