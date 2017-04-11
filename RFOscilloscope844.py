'''
    MG: 2014-10-25
    Communication class for Agilent oscilloscope TDS2004B
    
    Channel 1: DC test: Q41
    Channel 2: RF Reflection
    Channel 3: Capacitive ladder 1:100 calibration
    Channel 4: DC test Q21
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
DEVICELOC = "/dev/X88/RFOscilloscope844"
#PORT = 5025
print "hellojkdfnkjsffsnjkfdsfnfkjdsnfkjsnfjsdfjknfsjfsjndkdjsfbafjkbakfb"
class Comm:
    def __init__(self):  
        try:
            
            #Connect to device
            self.dev = os.open(DEVICELOC, os.O_RDWR)
            
            #Setup internal state for MTserver
            self.channels={"RF-Ladd":3,"RF-Refl":2, "DC-Q41":1,"DC-Q21":4}
            self.channels={"RF-Ladd":3,"RF-Refl":2, "DC-Q41":1,"DC-Q21":4}
            
            self.internal_state = {}
            #self.internal_state["RF-Ladd"] = 0.0
            #self.internal_state["RF-Freq"] = 0.0
            #self.internal_state["RF-Refl"] = 0.0
            #self.internal_state["DC-Q41"] = 0.0
            #self.internal_state["DC-Q21"]  = 0.0
            
            #self.internal_state["CH2REF"] = 0.0
            self.internal_state["CH3MEAN"] = 0.0
            self.internal_state["CH3PP"] = 0.0
            self.internal_state["CH4MEAN"] = 0.0
            self.internal_state["CH4PP"] = 0.0
            
            time.sleep(0.1)
            self.measure_RF_freq()
            self.UPDATE()
            
            
            
        except Exception as e:
            print "Could not initilize device, is it connected?",e
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
            print "measuring pk-pk"
            self.write_to_device('MEASUREMENT:IMMED:TYPE PK2PK')
            #self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(self.channels[channel])))
            self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(channel)))
            self.write_to_device('*OPC?')
            print "reading now"
            Qready = self.read_from_device(10)
            print "finished reading"
            if Qready.rstrip() == '1':
                self.write_to_device('MEASU:IMM:VAL?')
                rv = self.read_from_device(100)
            else:
                raise
            self.internal_state["CH" + str(channel) + "PP"] = rv
        except:
            print 'Trouble reading pk2pk'
            
    def measure_mean(self,channel):
        try:
            self.write_to_device('MEASUREMENT:IMMED:TYPE MEAN')
            #self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(self.channels[channel])))
            self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(channel)))
            self.write_to_device('*OPC?')
            Qready = self.read_from_device(10)
            if Qready.rstrip() == '1':
                self.write_to_device('MEASUREMENT:IMMED:VALUE?')
                rv = self.read_from_device(100)
            else:
                raise
            self.internal_state["CH" + str(channel) + "MEAN"] = rv
        except Exception as e:
            print 'Could not measure mean: ' + str(e)
            
    def measure_RF_freq(self):
        try:
            self.write_to_device('MEASUREMENT:IMMED:TYPE FREQ')
            self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(self.channels["RF-Ladd"])))
            self.write_to_device('*OPC?')
            
            Qready = self.read_from_device(100)
            if Qready.rstrip() == '1':
                self.write_to_device('MEASUREMENT:IMMED:VALUE?')
                rv = self.read_from_device(100)
            else:
                raise
            self.internal_state["RF-Freq"] = rv
        except Exception as e:
            print ' Could not set freq: ' + str(e)
    '''def measure_reff(self,channel):
        try:
            self.write_to_device('MEASUREMENT:IMMED:TYPE REF')
            #self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(self.channels[channel])))
            self.write_to_device('MEASUREMENT:IMMED:SOURCE CH%d'%(int(channel)))
            self.write_to_device('*OPC?')
            Qready = self.read_from_device(10)
            if Qready.rstrip() == '1':
                self.write_to_device('MEASUREMENT:IMMED:VALUE?')
                rv = self.read_from_device(100)
            else:
                raise
            self.internal_state["CH" + str(channel) + "REF"] = rv
        except Exception as e:
            print 'Could not measure reflection: ' + str(e)
        '''    
    def UPDATE(self):
        try:
            #self.measure_pkpk("RF-Ladd")
            #self.measure_pkpk("RF-Refl")

            #self.measure_mean("DC-Q41")
            #self.measure_mean("DC-Q21")

            self.measure_pkpk('3')
            self.measure_pkpk('4')
            self.measure_mean('3')
            self.measure_mean('4')
	        #self.measure_reff('2')
            
        except:
            print ' Could not Update'
            

