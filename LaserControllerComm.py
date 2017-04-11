'''
    Helena Zhang: 2014-10-09
    Communication class for Pichu boards based on old LaserController code.

 '''


import socket, sys, time
from MCxem import *

DEBUG = False

DEVICESERIAL = 'BRapurWDjz'

class Comm:
    def __init__(self):    
        try: 
            self.mcxem = MCxem(0)        
        except Exception as e:
            print "initialization error" + str(e)
            sys.exit(1)
        
        self.internal_state={}
        for i in range(0,4):
            channel = str(i)
            self.internal_state["ADC" + channel + "val"] = "0"
            self.internal_state["DAC" + channel + "wave"] = "0"
            self.internal_state["DAC" + channel + "offset"] = self.mcxem.get_state('DAC%swave'%(channel))[0]
            self.internal_state["DAC" + channel + "amp"] = self.mcxem.get_state('DAC%swave'%(channel))[1]
            self.internal_state["DAC" + channel + "period"] = self.mcxem.get_state('DAC%swave'%(channel))[2]
        
    def update_mcxem(self, channel):
        channel=str(channel)    
        if self.internal_state["DAC" + channel + "wave"]=="0":
            amp=0.0
        else:
            amp=self.internal_state["DAC" + channel + "amp"]
        self.mcxem.set_state('DAC' + channel + 'wave', [self.internal_state["DAC" + channel + "offset"],amp, self.internal_state["DAC" + channel + "period"]]) 



    def DAC0offset(self, value):
        self.internal_state["DAC0offset"] = float(value)
        self.update_mcxem(0)

    def DAC0wave(self, value):
        self.internal_state["DAC0wave"] = value
        self.update_mcxem(0)
        
    def DAC0amp(self, value):
        self.internal_state["DAC0amp"] = float(value)
        self.update_mcxem(0)
        
    def DAC0period(self, value):
        self.internal_state["DAC0period"] = float(value)
        self.update_mcxem(0)   

    def DAC1offset(self, value):
        IO="DAC1offset"
        setvalue=float(value)
        # need to walk the piezo slowly if taking large step
        if setvalue > self.internal_state[IO]:
            flag=1
        else:
            flag=-1
        while abs(self.internal_state[IO]-setvalue) > 0.005:
            self.internal_state[IO] += flag*0.005
            self.update_mcxem(1)
            time.sleep(0.02)
        self.internal_state[IO] = setvalue
        self.update_mcxem(1)

    def DAC1wave(self, value):
        self.internal_state["DAC1wave"] = value
        self.update_mcxem(1)
        
    def DAC1amp(self, value):
        self.internal_state["DAC1amp"] = float(value)
        self.update_mcxem(1)
        
    def DAC1period(self, value):
        self.internal_state["DAC1period"] = float(value)
        self.update_mcxem(1)   

    def DAC2offset(self, value):
        IO="DAC2offset"
        setvalue=float(value)
        # need to walk the piezo slowly if taking large step
        if setvalue > self.internal_state[IO]:
            flag=1
        else:
            flag=-1
        while abs(self.internal_state[IO]-setvalue) > 0.005:
            self.internal_state[IO] += flag*0.005
            self.update_mcxem(2)
            time.sleep(0.02)
        self.internal_state[IO] = setvalue
        self.update_mcxem(2)

    def DAC2wave(self, value):
        self.internal_state["DAC2wave"] = value
        self.update_mcxem(2)
        
    def DAC2amp(self, value):
        self.internal_state["DAC2amp"] = float(value)
        self.update_mcxem(2)
        
    def DAC2period(self, value):
        self.internal_state["DAC2period"] = float(value)
        self.update_mcxem(2)   
        
    def DAC3offset(self, value):
        IO="DAC3offset"
        setvalue=float(value)
        # need to walk the piezo slowly if taking large step
        if setvalue > self.internal_state[IO]:
            flag=1
        else:
            flag=-1
        while abs(self.internal_state[IO]-setvalue) > 0.005:
            self.internal_state[IO] += flag*0.005
            self.update_mcxem(3)
            time.sleep(0.02)
        self.internal_state[IO] = setvalue
        self.update_mcxem(3)

    def DAC3wave(self, value):
	print "changing DAC3wave to " + str(value)
        self.internal_state["DAC3wave"] = value
        self.update_mcxem(3)
        
    def DAC3amp(self, value):
        self.internal_state["DAC3amp"] = float(value)
        self.update_mcxem(3)
        
    def DAC3period(self, value):
        self.internal_state["DAC3period"] = float(value)
        self.update_mcxem(3)        
                   
    def UPDATE(self):
        # update ADCs: SLOW before FAST is allegedly more correct?
        self.internal_state["ADC1val"] = self.mcxem.get_adc_value(1, 'SLOW', 7)
        self.internal_state["ADC3val"] = self.mcxem.get_adc_value(3, 'SLOW', 7)
        self.internal_state["ADC0val"] = self.mcxem.get_adc_value(0, 'FAST', 0)
        self.internal_state["ADC2val"] = self.mcxem.get_adc_value(2, 'FAST', 0)
        return self.internal_state

    def STOP(self):
        self.mcxem.save_config()
        

