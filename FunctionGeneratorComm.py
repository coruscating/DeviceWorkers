'''
    Matt Tancik: 2015-01-06
    Communication class for Agilent 33250A, To control X88 equipments.

    Available set methods can be found in METHODSAVAILABLE, also callable from the server.

    units are in megahertz [MHz] and millivolts [mV]


'''


import time
import sys
import serial
import os
import numpy as np
import string
import traceback

#Define global variables
#DEVICELOC = '/dev/X88/FunGen'
DEVICELOC='/dev/ttyUSB0'
DEBUG = False

class Comm:
    def __init__(self):
        try:

            #Open Serial Connection with device
            serial_settings={"port":DEVICELOC,"baudrate":115200, "timeout":0.5, "rtscts":True}
            self.serial=serial.Serial(**serial_settings)
            self.serial.write('SYST:REM\n')
            self.serial.write('*CLS\n')
            self.serial.read()

            self.internal_state = {}

            time.sleep(0.1)
            self.GetState()

        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            sys.exit(1)


    def UPDATE(self):
        pass

    def GetState(self):
        '''
            Function gets the current device state, output frequency and amplitude
            It then updates the internal_state variable and returns.
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error
        '''
        try:
            meascommand = 'FUNCtion?\n'
            self.serial.write(meascommand)
            time.sleep(0.05)
            self.internal_state["Mode"] = self.serial.read(1000).rstrip()
            
            
            meascommand = 'FREQuency?\n'
            self.serial.write(meascommand)      #asks for frequency
            time.sleep(0.05) #time for device to load buffer
            self.internal_state["Frequency"] = float(self.serial.read(1000).rstrip())/1000000.0

            meascommand = 'VOLT?\n'
            self.serial.write(meascommand)      #asks for voltage amplitude
            time.sleep(0.05) #time for device to load buffer
            self.internal_state["Amplitude"] = float(self.serial.read(1000).rstrip())*1000.0
            
            
            meascommand = 'VOLTage:OFFset?\n'
            self.serial.write(meascommand)
            time.sleep(0.05)
            self.internal_state['Offset'] = float(self.serial.read(1000).rstrip())*1000.0

            meascommand = 'OUTPut?\n'
            self.serial.write(meascommand)
            time.sleep(0.05)
            self.internal_state['Output'] = int(self.serial.read(1000).rstrip())

            print self.internal_state
            
            if DEBUG: print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            print traceback.format_exc()
            return -1

    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial.close()

    def Output(self,input):
        try:
            self.serial.write("OUTPut " + input + "\n")
            if input=="ON":
                self.internal_state["Output"]=1
            else:
                self.internal_state["Output"]=0
        except Exception as e:
            print "Error: %s" %(str(e))

    def Mode(self,mode):
        '''
            Checks what mode the function generator is in. e.g. DC, Sine, Ramp, square etc.
        '''
        try:
            msg = 'FUNCtion %s\n'%(str(mode))
            if not mode == 'SIN' or mode == 'SQU' or mode == 'RAMP' or mode == 'DC':
                if DEBUG : print msg
            
                self.serial.write(msg)
                self.internal_state["Mode"] = mode
            else: raise
        except Exception as e:
            print 'Error in setting mode: ',e
        
        
    def Frequency(self,value):
        '''
            Sets the frequency to the value [value] in hertz.
            inputs: value [float]
            returns: 0
        '''
        if value < 0:
            print "Error, invalid frequency"
            return 0
        try:
            freq = int(float(value)*1000000.0)
            msg = 'FREQ '+'%d'%(freq)+'\n'
            if DEBUG : print msg

            self.serial.write(msg)
            time.sleep(0.01) #Time for command to be read in
            self.internal_state["Frequency"] = float(value)
        except Exception as e:
            print "Error setting current: ",e
        return 0

    def Amplitude(self,value):
        '''
            Sets the amplitude to the value [value] in volts.
            inputs: value [float]
            returns: 0
        '''
        value=float(value)
        if value < 0 or value > 1000:
            print "Error, invalid voltage %f" %(value)
            return 0
        try:
            amp = value/1000.0
            msg = 'VOLT '+'%.3f'%(amp)+'\n'
            if DEBUG: print msg

            self.serial.write(msg)
            time.sleep(0.01) #Time for command to be read in
            self.internal_state["Amplitude"] = value
        except Exception as e:
            print "Error in setting voltage: ",e

    def Offset(self,value):
        '''
            sets the offset to the value [value] in volts
            inputs: value [float]
            return: 0
        '''
	value=float(value)
        self.internal_state['Offset']=value
        #if abs(value) < 5
        self.serial.write('VOLTage:OFFset %.3f\n'%(value/1000.0))
        time.sleep(0.01)
        pass
    
    
    def METHODSAVAILABLE(self):
        return ['Mode','Frequency','Amplitude']
