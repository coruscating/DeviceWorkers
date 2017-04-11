'''
    MG: 2014-07-20
    Communication class for Agilent N6700B, To control X88 equipments.
    
   Channel 1: -15V for DAC
   Channel 2: +15V for DAC
   Channel 3: +5V for PhotonCounter

    Type: N6700B allows for direct TCP socket communication. See programmers manual for details.

    
    Available set methods can be found in METHODSAVAILABLE, also callable from the server.
    
    units are in Amps [A] and Volts [V]
    
    
'''


import socket
import time
import sys
import os
import numpy as np
import string

#Define global variables
DEBUG = False
DEVICELOC = "quanta-d-X88agilentEQ"
PORT = 5025

class Comm:
    def __init__(self):  
        try:
            
            #Connect to device
            self.hostname = socket.gethostbyname(DEVICELOC)
            self.host     = socket.gethostbyname(self.hostname) 
            self.soc      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.soc.settimeout(0.5)
            self.soc.connect((self.host, PORT))
            

            
            #Channel state, format [OUtput state,Current limit, Voltage limit, Current output, Voltage output]
            self.channels = ["PhotonCounter"]
            self.parameters = ["State", "CurrentLim","VoltageLim","CurrentOP", "VoltageOP"]
            self.internal_state = {}
            self.internal_state["PhotonCounterChannel"] = 4
            self.internal_state["PhotonCounterState"] = False
            self.internal_state["PhotonCounterCurrentLim"] = 0
            self.internal_state["PhotonCounterVoltageLim"] = 0
            self.internal_state["PhotonCounterCurrentOP"]  = 0
            self.internal_state["PhotonCounterVoltageOP"]  = 0
     
            
            print 'Connected to device: %s'%(self.get_name())
            time.sleep(0.1)
            self.UPDATE()
            
        except Exception as e:
            print 'Failed opening socket, Check device connection: ',e
            sys.exit(1)
    def get_name(self):
        '''
            Function for obtaining the device ID
            returns something like:Agilent Technologies,N6700B,MY54000348,D.02.01
            For debugging purposes only, not used in internal_state
        '''
        msg = "*IDN?\n"
        
        self.soc.sendall(msg)
        time.sleep(0.1)
        rv = self.soc.recv(1024)
        
        return rv
                    
    def UPDATE(self):
        '''
            Function gets the current device state, output on/off (True/False) of each channel,
            current limit, voltage limit, current output, and voltage output for each channel.
            It then updates the internal_state variable and returns.
            For further optimization one could consider breaking this update into sub-updates, but 
            as is this only takes ~50ms
            inputs: none
            returns: updated_internal state [dictionary] or -1 for an error 
        '''
        try:
            msgs = ["OUTP? (@1,2,3,4)\n",
                    "SOUR:CURR? (@1,2,3,4)\n",
                    "MEAS:CURR:DC? (@1,2,3,4)\n",
                    "SOUR:VOLT? (@1,2,3,4)\n",
                    "MEAS:VOLT:DC? (@1,2,3,4)\n"]
            
            recvmsg = []
            for i in msgs:
                self.soc.sendall(i)
                recv = string.split(self.soc.recv(1024),'\n')[0]
                if DEBUG: print recv
                recvmsg.append(string.split(recv,',') )
                
            for i in range(0,1):
                self.internal_state["%s%s"%(self.channels[i],self.parameters[0])] = bool(int(recvmsg[0][2]))
                self.internal_state["%s%s"%(self.channels[i],self.parameters[1])] = float(recvmsg[1][2])
                self.internal_state["%s%s"%(self.channels[i],self.parameters[2])] = float(recvmsg[3][2])
                self.internal_state["%s%s"%(self.channels[i],self.parameters[3])] = float(recvmsg[2][2])
                self.internal_state["%s%s"%(self.channels[i],self.parameters[4])] = float(recvmsg[4][2])

            if DEBUG: print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            return -1
            
    def STOP(self):
        '''
            closes socket
        '''
        self.soc.close()

    def CURRENT(self,channel,value):
        '''
            Sets the current on channel [channel] to the value [value] in amps.
            inputs: channel [int], value [float]
            returns: 0
        '''
        try:
            msg = "SOUR:CURR:LEV %.5f,(@%i)\n"%(float(value),int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error setting current: ",e
        return 0
    
    def VOLTAGE(self,channel,value):
        '''
            Sets the voltage on channel [channel] to the value [value] in volts.
            inputs: channel [int], value [float]
            returns: 0
        '''
        try:
            msg = "SOUR:VOLT:LEV %.5f,(@%i)\n"%(float(value),int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error in setting voltage: ",e
            
    def ON(self,channel):
        '''
            Turns on channel [channel]
            inputs: channel [int]
            returns: 0
        '''
        try:
            msg = "OUTP ON,(@%i)\n"%(int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error turning on channel: ",e
            
    def OFF(self,channel):
        '''
            Turns off channel [channel]
            inputs: channel [int]
            returns: 0
        '''
        try:
            msg = "OUTP OFF,(@%i)\n"%(int(channel))
            
            if DEBUG: print msg
            self.soc.sendall(msg)
            self.UPDATE()
        except Exception as e:
            print "Error turning on channel: ",e
        
    '''        
    Functions intended to be called from webDAQ
    '''           
    def PhotonCounterCurrentLim(self,value):
        self.CURRENT(3,value)
        
    def PhotonCounterVoltageLim(self,value):
        self.VOLTAGE(3,value)
        
    def PhotonCounterState(self, value):
        if value == 'ON' or value == True:
            self.ON(3)
        elif value == 'OFF' or value == False:
            self.OFF(3)
        else:
            print 'Error in received value'
                
        

       
    def METHODSAVAILABLE(self):
        availmeth = []
        for i in self.channels:
            availmeth += ['%sCurrentLim'%(i),'%sVoltageLim'%(i),'%sState'%(i)]
       
        return availmeth
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
