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
import traceback

#Define global variables
DEBUG = False
DEVICELOC = '/dev/ttyUSB0'

class Comm:
    def __init__(self):
        try:

            #Open Serial Connection with device
            serial_settings={"port":DEVICELOC,"baudrate":9600, "timeout":5}
            self.serial=serial.Serial(**serial_settings)
            #self.serial.write('SYST:REM\n')
            #self.serial.write('*CLS\n')
            #self.serial.read()

            self.internal_state = {}
            self.internal_state["SentorrPressure"] = 0

            time.sleep(5)
            self.UPDATE()

        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            print traceback.format_exc()
            sys.exit(1)

    def UPDATE(self):
        '''
            Function gets the current device state, output frequency and amplitude
            It then updates the internal_state variable and returns.
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error
        '''
        try:

            meascommand = '#000F\r\n'
            self.serial.write(meascommand)      #asks for frequency
            time.sleep(0.05) #time for device to load buffer
            self.internal_state["SentorrPressure"] = float(self.serial.read(24).rstrip()[1:])
            print self.internal_state

            if DEBUG: print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            return -1

    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial.close()


    def METHODSAVAILABLE(self):
        return []
