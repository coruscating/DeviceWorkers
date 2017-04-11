import serial
import time
import sys
import os
import traceback

#Define global variables
DEBUG = False
DEVICELOC = '/dev/X88/CavityTemp1092'

class Comm:
    def __init__(self):
        try:
            #Initialize arduino communication
            self.arduino = serial.Serial(DEVICELOC, 115200, timeout=0.5)
            time.sleep(2)
            self.internal_state = {}
            self.internal_state['CavTemp1092_Cur'] = 0
            self.internal_state['CavTemp1092_Set'] = 0
            self.Status()
        except Exception as e:
            print 'Could not initialize',e
            print traceback.format_exc()
            sys.exit(1)
            
    def Status(self):
        self.arduino.write("A\n")
        result=self.arduino.read(10)
        result=result.split("\n")
        if len(result[0])>1:
            self.internal_state['CavTemp1092_Cur'] = float(result[0])
        time.sleep(0.15)
        self.arduino.write("B\n")
        result=self.arduino.read(10)
        result=result.split("\n")
        if len(result[0])>1:
            self.internal_state['CavTemp1092_Set'] = float(result[0])


    def CavTemp1092_Set(self, value):
        print "setting setpoint to %f" %(float(value))
        self.arduino.write(str(float(value)) + "\n")

    def UPDATE(self):
        self.Status()
        
            
    def STOP(self):
        '''
            Closes serial communication  
        '''  
        self.arduino.close()
