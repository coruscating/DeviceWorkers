'''
    Michael Gutierrez: 2015-03-22
    Communication class for Agilent 34401A, To read the ULE cavity temperature.

    units are in volts [V]


'''


import time
import sys
import serial
import os
import numpy as np
import string

#Define global variables
DEBUG = False
DEVICELOC = '/dev/ULE/REFTact'

class Comm:
    def __init__(self):
        try:

            #Open Serial Connection with device
            serial_settings={"port":DEVICELOC,"baudrate":9600, "timeout":.5,"rtscts":False,}
            self.serial=serial.Serial(**serial_settings)
            self.serial.write('SYST:REM\n')
            self.serial.write('*CLS\n')
            self.serial.read()

            self.internal_state = {}
            self.internal_state["Resistance"] = 3000
            self.internal_state["Temperature"] = 20.0
            time.sleep(0.1)
            self.UPDATE()

        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            sys.exit(1)

    def UPDATE(self):
        '''
            Function gets the current device state, output frequency and amplitude
            It then updates the internal_state variable and returns.
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error
        '''
        try:
            meascommand = 'MEASure:RESistance?\n'
            self.serial.write(meascommand)      #asks for frequency
            time.sleep(0.05) #time for device to load buffer
            self.internal_state["Resistance"] = float(self.serial.readline().rstrip())
            self.internal_state["Temperature"]= self.Temperature(self.internal_state["Resistance"])
            if DEBUG: print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            return -1
    def Temperature(self,R):
        A = 9.7142E-4
        B = 2.3268E-4
        C = 8.0591E-8
        try:
            T = (A + B * np.log(R) + C * (np.log(R))**3 )**-1 - 273.15
        except Exception as e:
            print 'Error in T conversion:',e
            T = 0.0
        return T
    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial.close()


    def METHODSAVAILABLE(self):
        return []
