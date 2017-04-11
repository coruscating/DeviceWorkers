'''
Jules (3/11) - I'll be configuring the source meter to work only as a current source
 while we're working on the B-field measurements.
'''

DEVICE = '/dev/ttyUSB4'
import time, sys, serial, os, string
import numpy as np

class Comm:
    def __init__(self):
        try:
            serial_settings = {"port":DEVICE,"baudrate":9600, "timeout":0.5}
            self.serial=0
            self.serial=serial.Serial(**serial_settings)
            self.internal_state = {}
            #self.internal_state['SourceMeterVolt'] = 0
            self.internal_state['SourceMeterCurrent'] = 0.0
            self.internal_state['SourceMeterStatus'] = "Off"


            self.serial.write('*RST\n')
            #Configure to source current with the maximum available range
            self.serial.write(':SOUR:FUNC CURR\n')
            self.serial.write(':SOUR:CURR:MODE FIX\n')
            self.serial.write(':SOUR:CURR:RANG MAX\n')
            #self.serial.write(':SOUR:CURR:LEV -0.2\n')
            #Configure to measure voltage with an output compliance of 10 volts
            self.serial.write(':SENS:FUNC \"VOLT\"\n')
            self.serial.write(':SENS:VOLT:PROT 10\n')
            self.serial.write(':SENS:VOLT:RANG 10\n')
            self.serial.write(':SENS:VOLT:RANG:AUTO OFF\n')
            #self.serial.write(':OUTP ON\n')
            self.serial.flushInput()

            
            self.serial.write(':SYST:BEEP 660, 0.1\n')
            time.sleep(0.25)
            self.serial.write(':SYST:BEEP 660, 0.1\n')
            time.sleep(0.4)
            self.serial.write(':SYST:BEEP 660, 0.1\n')
            time.sleep(0.4)
            self.serial.write(':SYST:BEEP 510, 0.1\n')
            time.sleep(0.2)
            self.serial.write(':SYST:BEEP 660, 0.1\n')
            time.sleep(0.4)
            self.serial.write(':SYST:BEEP 770, 0.1\n')
            time.sleep(0.65)
            self.serial.write(':SYST:BEEP 380, 0.1\n')
            time.sleep(0.675)

            self.serial.write(':SYST:BEEP 510, 0.1\n')
            time.sleep(0.550)
            self.serial.write(':SYST:BEEP 380, 0.1\n')
            time.sleep(0.500)
            self.serial.write(':SYST:BEEP 320, 0.1\n')
            time.sleep(0.600)
            self.serial.write(':SYST:BEEP 440, 0.1\n')
            time.sleep(0.400)
            self.serial.write(':SYST:BEEP 480, 0.08\n')
            time.sleep(0.510)
            self.serial.write(':SYST:BEEP 450, 0.1\n')
            time.sleep(0.250)
            self.serial.write(':SYST:BEEP 430, 0.1\n')
            time.sleep(0.400)
            self.serial.write(':SYST:BEEP 380, 0.1\n')
            time.sleep(0.300)
            self.serial.write(':SYST:BEEP 660, 0.08\n')
            time.sleep(0.280)
            self.serial.write(':SYST:BEEP 760, 0.05\n')
            time.sleep(0.200)
            self.serial.write(':SYST:BEEP 860, 0.1\n')
            time.sleep(0.400)
            self.serial.write(':SYST:BEEP 700, 0.08\n')
            time.sleep(0.230)
            self.serial.write(':SYST:BEEP 760, 0.05\n')
            time.sleep(0.400)
            self.serial.write(':SYST:BEEP 660, 0.08\n')
            time.sleep(0.380)
            self.serial.write(':SYST:BEEP 520, 0.08\n')
            time.sleep(0.380)
            self.serial.write(':SYST:BEEP 580, 0.08\n')
            time.sleep(0.230)
            self.serial.write(':SYST:BEEP 480, 0.08\n')
            time.sleep(0.580)



        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            print traceback.format_exc()
            sys.exit(1)
    
    def SetCurrent(self, current):
        self.internal_state['SourceMeterCurrent'] = float(current)
        self.serial.write(':SOUR:CURR:LEV ' + str(current) + '\n')

    def OutputStatus(self, status):
        self.internal_state['SourceMeterStatus'] = status
        if (self.internal_state['SourceMeterStatus'] == "On"):
            self.serial.write(':OUTP ON\n')
        else:
            self.serial.write(':OUTP OFF\n')

    def UPDATE(self):
        #self.SourceMeterVolt()
        #self.SourceMeterCurrent()
        #print self.internal_state
        pass

    def STOP(self):
        self.serial.write(':OUTP OFF\n')
        self.serial.close()

'''    
    def SourceMeterVolt(self):
        #self.serial.write(':SENS:FUNC "VOLT"\n')
        #self.serial.write(':SENS:CURR:PROT 0.001\n')
        self.serial.write('*RST\n')
        self.serial.write(':SOUR:FUNC CURR\n')
        self.serial.write(':SOUR:CURR:MODE FIXED\n')
        self.serial.write(':SENS:FUNC "VOLT"\n')
        self.serial.write(':SOUR:CURR:RANG MIN\n')
        self.serial.write(':SOUR:CURR:LEV 0\n')
        self.serial.write(':SENS:VOLT:PROT 25\n')
        self.serial.write(':SENS:VOLT:RANG 20\n')
        self.serial.write(':FORM:ELEM VOLT\n')
        #self.serial.write(':OUTP ON\n')
        self.serial.write(':MEAS:VOLT?\n')
        #self.serial.write(':OUTP OFF\n')
        #self.serial.write(':READ?\n')
        time.sleep(0.1)
        a = self.serial.read(100)
        b = string.split(a,',')
        self.internal_state['SourceMeterVolt'] = float(b[0])

    def SourceMeterCurrent(self, current):
        self.serial.write(':MEAS:CURR?\n')
        a = self.serial.read(100)
        b = string.split(a,',')
        self.internal_state['SourceMeterCurrent'] = float(b[0])
'''