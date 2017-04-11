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
DEVICELOC = '/dev/ULE/ULETact'

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
            self.internal_state["Volt"] = 3000
            self.internal_state["Celsius"] = 25
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
            meascommand = 'MEASure?\n'
            self.serial.write(meascommand)      #asks for frequency
            time.sleep(0.05) #time for device to load buffer
            self.internal_state["Volt"] =float(self.serial.read(24).rstrip())
            self.internal_state["Celsius"] = self.TempConversion(self.internal_state["Volt"])
            print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            return -1
    def TempConversion(self,V):
        '''
        Converts a voltage measurement to a temperature in celsius. 

        wavelength electronics controller uses 100uA to measure,
        conversion from
        resistance to voltage done through wavelength electronics function
        for 20k thermister
        '''
        Acoeff 	= 9.6542E-04
        Bcoeff 	= 2.3356E-04
        Ccoeff 	= 7.7781E-08
        Rmeas 	= V/(100E-06)
        return 1/( Acoeff + Bcoeff*np.log(Rmeas) 
                    + Ccoeff*(np.log(Rmeas))**3 )-272.15
    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial.close()


    def METHODSAVAILABLE(self):
        return []
