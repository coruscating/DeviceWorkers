'''
    Matt Tancik: 2015-01-29
    Communication class for Oasis 160

    Available set methods can be found in METHODSAVAILABLE, also callable from the server.

    units are in megahertz [MHz] and millivolts [mV]


'''


import time
import sys
import serial
import os
import numpy as np
import string
import struct

#Define global variables
DEBUG = False
DEVICELOC = '/dev/ttyUSB0'

# Oasis get commands
GETSWVERSION = 0xD7
GETCOOLANTTEMP = 0xC9
GETSETPOINT = 0xC1
GETCOOLHEAT = 0xDE
GETFAULTBYTE = 0xC8

# Oasis set commands
SETPOINT = 0xE1
SETFAULTRESET = 0xFF


class Comm:
    def __init__(self):
        try:

            #Open Serial Connection with device
            serial_settings={"port":DEVICELOC,"baudrate":9600, "timeout":.5,"rtscts":False,"bytesize": serial.EIGHTBITS,"stopbits": serial.STOPBITS_ONE}
            self.serial=serial.Serial(**serial_settings)
            
            self.internal_state = {}
            self.internal_state['CoolantTemp'] = 0
            self.internal_state['CoolantSetPoint'] = 0

            self.getsetpoint()
            #self.UPDATE()

        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            sys.exit(1)

    # takes Oasis output format and returns float
    def datatonumber(self, input1, input2):
        lb=struct.unpack('B', input1)[0]
        hb=struct.unpack('B', input2)[0]
        return (hb*256+lb)/10.
        
    # get actual coolant temperature    
    def getcoolanttemp(self):
        try:
            self.serial.write(struct.pack('B', GETCOOLANTTEMP))
            output=self.serial.read(3)
            if (struct.unpack('B', output[0])[0]==GETCOOLANTTEMP):
                self.internal_state['coolantTemp'] = self.datatonumber(output[1],output[2])
                print self.datatonumber(output[1],output[2])
            else:
                print "Error getting coolant temp"
        except Exception as e:
            print 'Failed to get coolant temperature: ', e

    def getsetpoint(self):
        try:
            self.serial.write(struct.pack('B', GETSETPOINT))
            output=self.serial.read(3)
            if (struct.unpack('B', output[0])[0]==GETSETPOINT):
                self.internal_state['coolantSetPoint'] = self.datatonumber(output[1],output[2])
                print self.datatonumber(output[1],output[2])
            else:
                print "Error getting setpoint"
        except Exception as e:
            print 'Failed to get setpoint: ', e
            
    def setpoint(self, value):
        try:
            value
            self.serial.write(Struct.pack('B', SETPOINT))
            self.serial.write(Struct.pack('B', ))
            self.serial.write(Struct.pack('B', ))
            output = self.serial.read()
        except Exception as e:
            print 'failed to set setpoint: ', e

    def UPDATE(self):
        '''
            Function gets the current device state, output coolant temp and coolant setpoint
            It then updates the internal_state variable and returns.
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error
        '''
        try:
            self.getcoolanttemp()
            self.getsetpoint()
        except Exception as e:
            print 'Could not get device state: ',e
            return -1

    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial.close()

