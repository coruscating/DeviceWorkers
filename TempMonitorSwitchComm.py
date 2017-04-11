DEVICE = '/dev/ttyUSB2'
DEBUG = False
DEVICELOC = '/dev/ttyACM0'
import time
import datetime
import sys
import serial
import os
import numpy as np
import string
import traceback
import usbtmc
import iontrap
import zachmath

class Comm:
    def __init__(self):
        try:
            serial_settings = {"port":DEVICE,"baudrate":9600, "timeout":0.5}
            self.serial=0
            self.serial=serial.Serial(**serial_settings)
            self.arduino = serial.Serial(DEVICELOC, 9600, timeout =2)
            time.sleep(2)
            self.internal_state = {}
            self.internal_state['SourceMeterVolt'] = 0
            self.internal_state['SourceMeterCurrent'] = 0
            self.internal_state['Switch'] = 0
            self.Meas()

            # self.SourceMeterVolt()
            # self.SourceMeterCurrent()
        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            print traceback.format_exc()
            sys.exit(1)
            
    def UPDATE(self):
        pass
    
    def SourceMeterVolt(self):
        self.serial.write(':MEAS:VOLT?\n')
        a = self.serial.read(100)
        b = string.split(a,',')
        self.internal_state['SourceMeterVolt'] = float(b[0])
        return self.internal_state['SourceMeterVolt']
        
    def SourceMeterCurrent(self):
        self.serial.write(':MEAS:CURR?\n')
        a = self.serial.read(100)
        b = string.split(a,',')
        self.internal_state['SourceMeterCurrent'] = float(b[0])
        return self.internal_state['SourceMeterCurrent']

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

    def Meas(self):
        loop = True
        acoeff = 1.0/.034
        bcoeff = 1.054*acoeff
        f = open('TempMonitorSwitch.txt', 'a')
        sleeptime = .1
        while loop:
            temperatures = []
            time.sleep(sleeptime)
            for i in range(8):
                self.Switch(i+1)
                temperature = (self.SourceMeterVolt()*1000)*acoeff + bcoeff
                time.sleep(sleeptime)
                switchtemp = 'Switch ' + str(i) + ' = ' + str(temperature)
                temperatures.append(switchtemp)
            f.write(str(datetime.datetime.now()) + ': ' + str(temperatures) + ' ')

    def STOP(self):
        self.serial.close()
        self.arduino.close()
