# MTserver for trap electrodes controlled by Agilent E3631A
#controls 6 electrodes independently
import time
import sys
import serial
import os
import numpy as np
import string
import traceback
import usbtmc
import iontrap
import zachmath

#Define global variables
DEBUG = True
DACL = '/dev/X88/DACL'
DACR = '/dev/X88/DACR'

# maps zones to Agilent channelss
#        ___     ___      
#   E0  |   |   |   | E3
#       |___|   |___|
#   E1  |   |   |   | E4
#       |___|   |___|
#   E2  |   |   |   | E5
#       |___|   |___|

channels = {}
               #[left(0)/right(1),sign,volt] 
channels['E0']=[0,1,'P25V'] 
channels['E2']=[1,1,'P25V']
channels['E3']=[0,1,'N25V']
channels['E5']=[1,1,'N25V']


class Comm:
    def __init__(self):
        try:
            #Open Serial Connection with device
            serial_settings={"port":DACL,"baudrate":9600, "timeout":0.5}
            self.serial=[0,0]
            self.serial[0]=serial.Serial(**serial_settings)
            self.serial[0].write('SYST:REM\n')
            self.serial[0].write('*CLS\n')
            self.serial[0].read()

            serial_settings={"port":DACR,"baudrate":9600, "timeout":0.5}
            self.serial[1]=serial.Serial(**serial_settings)
            self.serial[1].write('SYST:REM\n')
            self.serial[1].write('*CLS\n')
            self.serial[1].read()
            
            #Connect to device
            self.soc=usbtmc.Instrument(0x0957,0x0907,'MY54000334')


            self.internal_state = {}
            self.internal_state['HorizComp']=0
            self.internal_state['VertComp']=0
            #electrode constraints
            self.filename = None
            self.internal_state['ElectrodeConst'] = None
            self.internal_state['SecularZ']=.6
            self.internal_state['SecularY']=0
            self.internal_state['SecularX']=0
            self.internal_state['FreqRF']= 30
            self.internal_state['VoltRF']= 175
            self.internal_state['TrapAZ']= [0,0,1]
            self.internal_state['TrapAY']= [0,1,0]
            self.internal_state['TrapAX']= [1,0,0]
            self.internal_state['E0']=0
            self.internal_state['E1']=0
            self.internal_state['E2']=0
            self.internal_state['E3']=0
            self.internal_state['E4']=0
            self.internal_state['E5']=0  
            self.internal_state['GND']=0
            time.sleep(0.1)
            self.GetValues()

        except Exception as e:
            print 'Failed to start serial communication, Check device connection: ',e
            print traceback.format_exc()
            sys.exit(1)

    def GetValues(self):
        try:
            msgs = "SOUR:VOLT? (@1,2,3)\n"
            recv = string.split(self.soc.ask(msgs),'\n')[0]
            recv1 = string.split(recv, ',')
            self.internal_state['E1'] = -float(recv1[0])
            self.internal_state['E4']= -float(recv1[1])
            self.internal_state['GND'] = -float(recv1[2])
            
            for key in channels:
                self.serial[channels[key][0]].write('MEAS:VOLT? ' + channels[key][2] + '\n')
                time.sleep(0.01)
                self.internal_state[key] = round(float(self.serial[channels[key][0]].read(1000).rstrip()),3)
                # flip sign if negative channels
                if channels[key][1]==-1:
                    self.internal_state[key]=-self.internal_state[key]
            print self.internal_state
            return self.internal_state
        except Exception as e:
            print 'Could not get device state: ',e
            print traceback.format_exc()
            return -1


    def UPDATE(self):
        pass
    def ElectrodeConst(self, const):
        self.internal_state['ElectrodeConst'] = const
        if self.internal_state['ElectrodeConst'] == 'sideground':
            self.filename = 'SandiaCavityTrapSideGround.tsv'
        elif self.internal_state['ElectrodeConst'] =='side':
            self.filename = 'SandiaCavityTrapSide.tsv'
        elif self.internal_state['ElectrodeConst'] == 'symground':
            self.filename = 'SandiaCavityTrapSymGround.tsv'
        elif self.internal_state['ElectrodeConst'] == 'sym':
            self.filename = 'SandiaCavityTrapSym.tsv'
        elif self.internal_state['ElectrodeConst'] == 'noconst':
            self.filename = 'SandiaCavityTrapNoConst.tsv'
        else:
            self.filename = 'SandiaCavityTrapNoConstGround.tsv'
    def GND(self, value):
        '''
            Sets the voltage on channel [channel] to the value [value] in volts.
            inputs: channel [int], value [float]
            returns: 0
        '''
        try:
            msg = "SOUR:VOLT:LEV %.5f,(@%i)\n"%(-float(value),3)
            self.internal_state['GND'] = float(value)
            if DEBUG: print msg
            self.soc.write(msg)
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()

    def E1(self, value):
        '''
            Sets the voltage on channel [channel] to the value [value] in volts.
            inputs: channel [int], value [float]
            returns: 0
        '''
        try:
            msg = "SOUR:VOLT:LEV %.5f,(@%i)\n"%(-float(value),1)
            self.internal_state['E1'] = float(value)
            if DEBUG: print msg
            self.soc.write(msg)
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()
            
    def E4(self, value):
        '''
            Sets the voltage on channel [channel] to the value [value] in volts.
            inputs: channel [int], value [float]
            returns: 0
        '''
        try:
            msg = "SOUR:VOLT:LEV %.5f,(@%i)\n"%(-float(value),2)
            self.internal_state['E4'] = float(value)
            if DEBUG: print msg
            self.soc.write(msg)
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0 
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()          

    def E3(self, value):
        try:
            value=float(value)
            self.internal_state['E3']=value
            print 'APPL ' + channels['E3'][2] + ', ' + str(value) + ', 0.001\n'
            self.serial[channels['E3'][0]].write('APPL ' + channels['E3'][2] + ', ' + str(float(value)) + ', 0.01\n')
            time.sleep(.01)
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()

    def E5(self, value):
        try:
            '''
            while 1:
                self.serial[channels['E2'][0]].write('*OPC?\n')
                status = self.serial[channels['E2'][0]].read().rstrip()
                print "status=" + status
                if status == '1':
                    break
                time.sleep(0.1)
            '''
            self.serial[channels['E5'][0]].write('*CLS\n')
            value=float(value)
            self.internal_state['E5']=value
            print 'APPL ' + channels['E5'][2] + ', ' + str(float(value)) + ', 0.001\n'
            self.serial[channels['E5'][0]].write('APPL ' + channels['E5'][2] + ', ' + str(float(value)) + ', 0.01\n')
            time.sleep(.01)
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()

    def E0(self, value):
        try:
            value=float(value)
            self.internal_state['E0']=value
            print 'APPL ' + channels['E0'][2] + ', ' + str(value) + ', 0.001\n'
            self.serial[channels['E0'][0]].write('APPL ' + channels['E0'][2] + ', ' + str(value) + ', 0.01\n')
            time.sleep(.01)
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()
            
    def E2(self, value):
        try:
            '''
            while 1:
                self.serial[channels['E2'][0]].write('*OPC?\n')
                status = self.serial[channels['E2'][0]].read().rstrip()
                print "status=" + status
                if status == '1':
                    break
                time.sleep(0.1)
            '''
            self.serial[channels['E2'][0]].write('*CLS\n')
            value=float(value)
            self.internal_state['E2']=value
            print 'APPL ' + channels['E2'][2] + ', ' + str(float(value)) + ', 0.001\n'
            self.serial[channels['E2'][0]].write('APPL ' + channels['E2'][2] + ', ' + str(float(value)) + ', 0.01\n')
            time.sleep(.01)
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()

    def SecularZ(self, value):
        self.internal_state['SecularZ']=float(value) #takes in value in MHz

    def FreqRF(self, value):
        self.internal_state['FreqRF']=float(value)

    def VoltRF(self,value):
        self.internal_state['VoltRF']=float(value)

    def VertComp(self,value):
        try:
            value=float(value)
            self.internal_state['VertComp']=value
            newE3=self.internal_state['E3']+value-self.internal_state['HorizComp']
            newE4=self.internal_state['E4']+value-self.internal_state['HorizComp']
            newE5=self.internal_state['E5']+value-self.internal_state['HorizComp']
            newE1=self.internal_state['E1']+value+self.internal_state['HorizComp']
            newE2=self.internal_state['E2']+value+self.internal_state['HorizComp']
            newE0=self.internal_state['E0']+value+self.internal_state['HorizComp']
            print 'APPL ' + channels['E3'][2] + ', ' + str(newE3) + ', 0.001\n'
            print 'APPL ' + channels['E5'][2] + ', ' + str(float(newE5)) + ', 0.001\n'
            print 'APPL ' + channels['E2'][2] + ', ' + str(float(newE2)) + ', 0.001\n'
            print 'APPL ' + channels['E0'][2] + ', ' + str(float(newE0)) + ', 0.001\n'
            print "SOUR:VOLT:LEV %.5f,(@%i)\n"%(float(newE1),1)
            print "SOUR:VOLT:LEV %.5f,(@%i)\n"%(float(newE4),2)
            self.serial[channels['E3'][0]].write('APPL ' + channels['E3'][2] + ', ' + str(float(newE3)) + ', 0.01\n')
            self.serial[channels['E5'][0]].write('APPL ' + channels['E5'][2] + ', ' + str(float(newE5)) + ', 0.01\n')
            self.serial[channels['E2'][0]].write('APPL ' + channels['E2'][2] + ', ' + str(float(newE2)) + ', 0.01\n')
            self.serial[channels['E0'][0]].write('APPL ' + channels['E0'][2] + ', ' + str(float(newE0)) + ', 0.01\n')
            self.soc.write("SOUR:VOLT:LEV %.5f,(@%i)\n"%(-float(newE1),1))
            self.soc.write("SOUR:VOLT:LEV %.5f,(@%i)\n"%(-float(newE4),2))
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()
    def HorizComp(self,value):
        try:
            value=float(value)
            self.internal_state['HorizComp']=value
            newE3=self.internal_state['E3']-value+self.internal_state['VertComp']
            newE4=self.internal_state['E4']-value+self.internal_state['VertComp']
            newE5=self.internal_state['E5']-value+self.internal_state['VertComp']
            newE1=self.internal_state['E1']+value+self.internal_state['VertComp']
            newE2=self.internal_state['E2']+value+self.internal_state['VertComp']
            newE0=self.internal_state['E0']+value+self.internal_state['VertComp']
            print 'APPL ' + channels['E3'][2] + ', ' + str(newE3) + ', 0.001\n'
            print 'APPL ' + channels['E5'][2] + ', ' + str(newE5) + ', 0.001\n'
            print 'APPL ' + channels['E2'][2] + ', ' + str(newE2) + ', 0.001\n'
            print 'APPL ' + channels['E0'][2] + ', ' + str(newE0) + ', 0.001\n'
            print "SOUR:VOLT:LEV %.5f,(@%i)\n"%(float(newE1),1)
            print "SOUR:VOLT:LEV %.5f,(@%i)\n"%(float(newE4),2)
            self.serial[channels['E3'][0]].write('APPL ' + channels['E3'][2] + ', ' + str(float(newE3)) + ', 0.01\n')
            self.serial[channels['E5'][0]].write('APPL ' + channels['E5'][2] + ', ' + str(float(newE5)) + ', 0.01\n')
            self.serial[channels['E2'][0]].write('APPL ' + channels['E2'][2] + ', ' + str(float(newE2)) + ', 0.01\n')
            self.serial[channels['E0'][0]].write('APPL ' + channels['E0'][2] + ', ' + str(float(newE0)) + ', 0.01\n')
            self.soc.write("SOUR:VOLT:LEV %.5f,(@%i)\n"%(-float(newE1),1))
            self.soc.write("SOUR:VOLT:LEV %.5f,(@%i)\n"%(-float(newE4),2))
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()     
  
    # takes the current electrode values and calculates secular frequencies
    def FindSecularFreqs(self):
        try:
            v_dict={}

            if self.internal_state ['ElectrodeConst'] == 'noconstground' or self.internal_state ['ElectrodeConst'] == 'sideground' or self.internal_state ['ElectrodeConst'] == 'symground':
                v_dict['vg']= self.internal_state['GND']
                if self.internal_state['ElectrodeConst'] == 'noconstground':
                    v_dict['v0']= self.internal_state['E0']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v1']= self.internal_state['E1']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v2']= self.internal_state['E2']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v3']= self.internal_state['E3']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                    v_dict['v4']= self.internal_state['E4']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                    v_dict['v5']= self.internal_state['E5']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                elif self.internal_state['ElectrodeConst'] == 'sideground':
                    v_dict['v0']= self.internal_state['E0']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v1']= self.internal_state['E1']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v2']= self.internal_state['E2']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['vside']= self.internal_state['E3']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                elif self.internal_state['ElectrodeConst'] == 'symground':
                    v_dict['vtop']= self.internal_state['E0']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['vmid']= self.internal_state['E1']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['vbottom']= self.internal_state['E2']+self.internal_state['VertComp']+self.internal_state['HorizComp']
            if self.internal_state ['ElectrodeConst'] == 'noconst' or self.internal_state ['ElectrodeConst'] == 'side' or self.internal_state ['ElectrodeConst'] == 'sym':
                if self.internal_state['ElectrodeConst'] == 'noconst':
                    v_dict['v0']= self.internal_state['E0']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v1']= self.internal_state['E1']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v2']= self.internal_state['E2']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v3']= self.internal_state['E3']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                    v_dict['v4']= self.internal_state['E4']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                    v_dict['v5']= self.internal_state['E5']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                elif self.internal_state['ElectrodeConst'] == 'side':
                    v_dict['v0']= self.internal_state['E0']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v1']= self.internal_state['E1']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['v2']= self.internal_state['E2']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['vside']= self.internal_state['E3']+self.internal_state['VertComp']-self.internal_state['HorizComp']
                elif self.internal_state['ElectrodeConst'] == 'sym':
                    v_dict['vtop']= self.internal_state['E0']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['vmid']= self.internal_state['E1']+self.internal_state['VertComp']+self.internal_state['HorizComp']
                    v_dict['vbottom']= self.internal_state['E2']+self.internal_state['VertComp']+self.internal_state['HorizComp']

            
            m = 1.46e-25                                    # [kg] - Strontium
            Ze = 1.602e-19                                  # [C] - singly ionized
            m_over_Ze = m/Ze                                # [kg/C]
            omega_rf = 2*np.pi*self.internal_state['FreqRF']*1000000        # [Hz] - rf frequency
            v_rf = self.internal_state['VoltRF']                            # [V]

            trap = iontrap.IonTrap(v_rf, m_over_Ze, omega_rf, v_dict, self.filename)
            secularfreqs, trapaxes = trap.find_omega_secular(v_dict, m_over_Ze, omega_rf)[0],trap.find_omega_secular(v_dict, m_over_Ze, omega_rf)[1]
            
            self.internal_state['SecularZ']= round(secularfreqs['omega_z']/(2*np.pi*1000000),3)
            self.internal_state['SecularY']= round(secularfreqs['omega_y']/(2*np.pi*1000000),3)
            self.internal_state['SecularX']= round(secularfreqs['omega_x']/(2*np.pi*1000000),3)

            r_z = []
            r_y = []
            r_x = []
            for i in trapaxes['z-axis']:
                r_z.append(round(i,3))
            for i in trapaxes['y-axis']:
                r_y.append(round(i,3))
            for i in trapaxes['x-axis']:
                r_x.append(round(i,3))
            self.internal_state['TrapAZ']= r_z
            self.internal_state['TrapAY']= r_y
            self.internal_state['TrapAX']= r_x
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()  



    # takes secular z-frequency and calculates electrode values
    def FindDCVoltages(self):
        try:       
            m = 1.46e-25                                                    # [kg] - Strontium
            Ze = 1.602e-19                                                  # [C] - singly ionized
            m_over_Ze = m/Ze                                                # [kg/C]
            omega_rf = 2*np.pi*self.internal_state['FreqRF']*1000000        # [Hz] - rf frequency
            v_rf = self.internal_state['VoltRF']                            # [V]

            
            Azz = 4*(2*np.pi*1000000*self.internal_state['SecularZ'])**2/omega_rf**2 #unitless curvature parameter
            trap = iontrap.IonTrap(v_rf, m_over_Ze, omega_rf, None, self.filename)
            curvature = m_over_Ze * omega_rf**2 * Azz/4 
            constraints = {trap.grad_potential_fn:[0,0,0], trap.hess_potential_fn_ij(2,2):curvature} 
            dcvoltages = trap.find_dc_voltages(constraints)

            for key in dcvoltages:
                dcvoltages[key]=round(dcvoltages[key],3)
                
            if self.internal_state ['ElectrodeConst'] == 'noconstground' or self.internal_state ['ElectrodeConst'] == 'sideground' or self.internal_state ['ElectrodeConst'] == 'symground':
                if self.internal_state['ElectrodeConst'] == 'noconstground':
                    self.internal_state['E0'] = dcvoltages['v0']
                    self.internal_state['E1'] = dcvoltages['v1']
                    self.internal_state['E2'] = dcvoltages['v2']
                    self.internal_state['E3'] = dcvoltages['v3']
                    self.internal_state['E4'] = dcvoltages['v4']
                    self.internal_state['E5'] = dcvoltages['v5']
                    self.internal_state['GND'] = dcvoltages['vg']
                elif self.internal_state['ElectrodeConst'] == 'sideground':
                    self.internal_state['E0'] = dcvoltages['v0']
                    self.internal_state['E1'] = dcvoltages['v1']
                    self.internal_state['E2'] = dcvoltages['v2']
                    self.internal_state['E3'] = dcvoltages['vside']
                    self.internal_state['E4'] = dcvoltages['vside']
                    self.internal_state['E5'] = dcvoltages['vside']
                    self.internal_state['GND'] = dcvoltages['vg']
                elif self.internal_state['ElectrodeConst'] == 'symground':
                    self.internal_state['E0'] = dcvoltages['vtop']
                    self.internal_state['E1'] = dcvoltages['vmid']
                    self.internal_state['E2'] = dcvoltages['vbottom']
                    self.internal_state['E3'] = dcvoltages['vtop']
                    self.internal_state['E4'] = dcvoltages['vmid']
                    self.internal_state['E5'] = dcvoltages['vbottom']
                    self.internal_state['GND'] = dcvoltages['vg']
            if self.internal_state ['ElectrodeConst'] == 'noconst' or self.internal_state ['ElectrodeConst'] == 'side' or self.internal_state ['ElectrodeConst'] == 'sym':
                if self.internal_state['ElectrodeConst'] == 'noconst':
                    self.internal_state['E0'] = dcvoltages['v0']
                    self.internal_state['E1'] = dcvoltages['v1']
                    self.internal_state['E2'] = dcvoltages['v2']
                    self.internal_state['E3'] = dcvoltages['v3']
                    self.internal_state['E4'] = dcvoltages['v4']
                    self.internal_state['E5'] = dcvoltages['v5']
                    self.internal_state['GND'] = 0
                elif self.internal_state['ElectrodeConst'] == 'side':
                    self.internal_state['E0'] = dcvoltages['v0']
                    self.internal_state['E1'] = dcvoltages['v1']
                    self.internal_state['E2'] = dcvoltages['v2']
                    self.internal_state['E3'] = dcvoltages['vside']
                    self.internal_state['E4'] = dcvoltages['vside']
                    self.internal_state['E5'] = dcvoltages['vside']
                    self.internal_state['GND'] = 0
                elif self.internal_state['ElectrodeConst'] == 'sym':
                    self.internal_state['E0'] = dcvoltages['vtop']
                    self.internal_state['E1'] = dcvoltages['vmid']
                    self.internal_state['E2'] = dcvoltages['vbottom']
                    self.internal_state['E3'] = dcvoltages['vtop']
                    self.internal_state['E4'] = dcvoltages['vmid']
                    self.internal_state['E5'] = dcvoltages['vbottom']
                    self.internal_state['GND'] = 0
            #updating secular x and y frequencies
            trap2 = iontrap.IonTrap(v_rf, m_over_Ze, omega_rf, dcvoltages, self.filename)
            secularfreqs2, trapaxes2 = trap2.find_omega_secular(dcvoltages, m_over_Ze, omega_rf)[0],trap2.find_omega_secular(dcvoltages, m_over_Ze, omega_rf)[1]

            self.internal_state['SecularY']= round(secularfreqs2['omega_y']/(2*np.pi*1000000),3)
            self.internal_state['SecularX']= round(secularfreqs2['omega_x']/(2*np.pi*1000000),3)

            r_z2 = []
            r_y2 = []
            r_x2 = []
            for i in trapaxes2['z-axis']:
                r_z2.append(round(i,3))
            for i in trapaxes2['y-axis']:
                r_y2.append(round(i,3))
            for i in trapaxes2['x-axis']:
                r_x2.append(round(i,3))
            self.internal_state['TrapAZ']= r_z2
            self.internal_state['TrapAY']= r_y2
            self.internal_state['TrapAX']= r_x2
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()  
    
    def STOP(self):
        '''
            closes serial communication
        '''
        self.serial[0].close()
        self.serial[1].close()
