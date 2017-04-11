'''
    Matt Tancik: 01/07/15
    Communication class for Agilent oscilloscope TDS2004B

    Type: USBTMC driver

    Available set methods can be found in METHODSAVAILABLE, also callable from the server.

    units are in Hertz [Hz] and Volts [V] and Volts peak-peak [Vpp]


'''


import socket
import time
import sys
import os
import numpy as np
import string

#Define global variables
DEBUG = False
DEVICELOC = "/dev/X88/RFOscilloscope"
PORT = 5825

class Comm:
    def __init__(self):
        try:

            #Connect to device
            self.dev = os.open(DEVICELOC, os.O_RDWR)

            #Setup internal state for MTserver

            self.internal_state = {}
            for i in range(1,5):
                self.internal_state["pk2pkChannel%d"%(i)] = 0.0
                self.internal_state["meanChannel%d"%(i)]  = 0.0

            time.sleep(5)
            self.UPDATE()

        except Exception as e:
            print "Could not initialize device",e
            sys.exit(1)
    def write_to_device(self,command):
        """
            Write command to device, command should be a non-terminated key word. e.g. "*IDN?"
        """
        os.write(self.dev, command)

    def read_from_device(self,length=9000):
        """
            Reads message
        """
        try:
            rv = os.read(self.dev, length)
            return rv
        except Exception as e:
            print "Could not read from device",e
            return -1

    def sendReset(self):
        self.write("*RST")


    def STOP(self):
        try:
            os.close(self.dev)
        except:
            print "could not close device"

    def measure_pkpk(self, channel):
        try:
            self.write_to_device('MEASUREMENT:IMMED:TYPE PK2PK')
            self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(channel)))
            self.write_to_device('*OPC?')
            Qready = self.read_from_device(100)
            if Qready.rstrip() == '1':
                self.write_to_device('MEASU:IMM:VAL?')
                rv = self.read_from_device(100)
            else:
                raise
            self.internal_state["pk2pkChannel" + channel] = rv
        except:
            print 'Trouble reading pk2pk'

    def measure_mean(self,channel):
        try:
            self.write_to_device('MEASUREMENT:IMMED:TYPE MEAN')
            self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(channel)))
            self.write_to_device('*OPC?')
            Qready = self.read_from_device(100)
            if Qready.rstrip() == '1':
                self.write_to_device('MEASUREMENT:IMMED:VALUE?')
                rv = self.read_from_device(100)
            else:
                raise
            self.internal_state["meanChannel" + channel] = rv
        except:
            print 'Could not measure mean'

    def UPDATE(self):
        try:
            for i in range(1,5):
                self.measure_pkpk(str(i))
                self.measure_mean(str(i))
        except:
            print ' Could not Update'
