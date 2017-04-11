'''
    MG: 2014-07-20
    Communication class for Shutter device.
    Type: Arduino, controlling multiple servo's
    
'''


import serial
import time
import sys
import os

#Define global variables
DEBUG = False
#DEVICELOC = '/dev/X88/ShutterBox'
DEVICELOC = '/dev/ttyACM0'

class Comm:
    def __init__(self):
        
        try:
            #Initialize arduino communication
            self.arduino = serial.Serial(DEVICELOC, 9600, timeout =None)
            
            #Arduino Shutter specific commands
            self.freqs = ["Shutter405","Shutter461"]
            self.read_cmd = ['1', '2', '3','4','5','6']
            self.close_cmd = ['a', 'b', 'c','d','e','f']
            self.open_cmd = ['A', 'B', 'C','D','E','F']
            
            #Variable to monitor/store shutter states
            self.internal_state = dict((f, 'OPEN') for f in self.freqs)
            self.UPDATE()

        except Exception as e:
            print 'Could not initialize shutters',e
            sys.exit(1)
        
    def Shutter405(self, state):
        '''
            Function sets the passed frequency to the closed state [1]
            inputs: frequency [int in self.freqs]
            returns: none
            
        '''
        try:
            if state=="OPEN":
                write_cmd = self.open_cmd[self.freqs.index("Shutter405")]
            elif state=="CLOSE":
                write_cmd = self.close_cmd[self.freqs.index("Shutter405")] 
            self.arduino.write(write_cmd)
            self.internal_state["Shutter405"]=state
            
        except Exception as e:
            print 'Failed in Close: ',e
            pass
            
    def Shutter461(self, state):
        '''
            Function sets the passed frequency to the open state [0]
            inputs: frequency [int in self.freqs]
            returns: none
            
        '''
        try:  

            if state=="OPEN":
                write_cmd = self.open_cmd[self.freqs.index("Shutter461")]
            elif state=="CLOSE":
                write_cmd = self.close_cmd[self.freqs.index("Shutter461")]   
            self.arduino.write(write_cmd)
            self.internal_state["Shutter461"]=state
            
        except Exception as e:
            print 'Failed in open: ',e
            pass
    
    def update_internal_state(self, write_cmd, delay= 0.05):
        '''
            Updates the internal state of the shutters.
            Note the formatting of the arduino output is not
            well controlled, so a loop over returned 
            values is necessary 
            inputs: write_cmd [string in self.read_cmd]
            returns: none
        '''
        
        try:
            self.arduino.write(write_cmd)
            time.sleep(delay)
            response = self.arduino.read(self.arduino.inWaiting())
            if DEBUG: print 'response is: ', response
            for received in response:
                if received in self.close_cmd:
                    freq = self.freqs[self.close_cmd.index(received)]
                    self.internal_state[freq] = 'CLOSE'
                elif received in self.open_cmd:
                    freq = self.freqs[self.open_cmd.index(received)]
                    self.internal_state[freq] = 'OPEN'
        except Exception as e:
            print 'Failed in update_internal_state: ',e
            pass
    
    def STATUS(self, frequency):
        '''
            Updates the internal state of frequency
            and returns that state
            input: frequency [int in self.freqs]
            return: bool , current state of the 'frequency' shutter
        '''
        try:
            
            self.update_internal_state(self.read_cmd[ self.freqs.index(frequency) ])
            if self.internal_state[frequency]:
                return 1
            else:
                return 0
        except Exception as e:
            print 'Failed in STATUS: ',e
            return -1
            pass
            
            
    def UPDATE(self):
        '''
            Updates all internal state values 
            and returns them in a string array [".",".",...]
            
        '''
        try:
            if DEBUG: print 'Updating internal_state...'
            for freqs in self.freqs:
                self.STATUS(freqs)
            return str(self.internal_state)
        except Exception as e:
            print 'Failed in Update: ',e
            pass

    def STOP(self):
        '''
            Closes serial communication  
        '''  
        self.arduino.close()

