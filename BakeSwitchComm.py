import serial
import time
import sys
import os

#Define global variables
DEBUG = False
DEVICELOC = '/dev/ttyACM2'

class Comm:
    def __init__(self):

        try:
            #Initialize arduino communication
            self.arduino = serial.Serial(DEVICELOC, 9600, timeout =2)
            time.sleep(2)
            self.internal_state = {}
            self.internal_state['Switch'] = 0
            self.Switch(1)
            print "switching to %d\n"%(self.internal_state['Switch'])
        except Exception as e:
            print 'Could not initialize',e
            sys.exit(1)
            
    def UPDATE(self):

        pass
    
        
    def Switch(self, switch):
        Byte = []
        switch = int(switch)
        self.internal_state['Switch'] = switch
        if switch == 0:
            Byte = ['0','0','0','0']
            
        elif switch != None and switch < 9 :
            Byte = list(bin(switch-1)[2:])
            while len(Byte) <3:
                Byte.insert(0,'0')
            Byte.append('1')

        else:
            pass
        serialnumber = ''.join(Byte) + '\n'
        self.arduino.write(serialnumber)

    def Status(self):
        try:
            self.arduino.write("A")
            print self.arduino.read(10)
        except Exception as e:
            print 'Failed in stats: ' ,e
            
    def STOP(self):
        '''
            Closes serial communication  
        '''  
        self.arduino.close()
