# MTserver for trap electrodes controlled by Agilent E3631A

import time
import sys
import serial
import os
import numpy as np
import string
import traceback
import iontrap
import zachmath

#Define global variables
DEBUG = True
DEV = '/dev/ttyUSB3'


class Comm:
    def __init__(self):
        try:

            #Open Serial Connection with device
            serial_settings={"port":DEV,"baudrate":115200, "timeout":1}
            self.serial=serial.Serial(**serial_settings)
            self.serial.write('SYST:REM\n')
            self.serial.write('*CLS\n')
            self.serial.read()

            self.internal_state = {}
            self.internal_state['IonPumpPressure']=0
            self.internal_state['IonPumpCurrent']=0
            self.UPDATE()
        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            sys.exit(1)


    def UPDATE(self):
        try:
            self.serial.write('Tt\r\n')
            time.sleep(0.1)
            self.internal_state['IonPumpPressure']=float(self.serial.read(1000).rstrip())
            self.serial.write('TI\r\n')
            time.sleep(0.1)
            current=self.serial.read(1000).rstrip()
            if current=="Pump off!":
                self.internal_state['IonPumpCurrent']="Off"
            else: 
                current=current.split(' ')
                if current[2]=="uA":
                    self.internal_state['IonPumpCurrent']=float(current[1])*1E-6
                elif current[2]=="mA":
                    self.internal_state['IonPumpCurrent']=float(current[1])*1E-3
                elif current[2]=="nA":
                    self.internal_state['IonPumpCurrent']=float(current[1])*1E-9
                elif current[2]=="A":
                    self.internal_state['IonPumpCurrent']=float(current[1])
            pass
        except Exception as e:
            print 'Error: %s' (str(e))
 
    
    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial.close()
