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
#[left(0)/right(1)/channel,sign,volt/power supply] 
#E0,db7 / Q27, N6700 Ch1
#E1,db40 / Q28, N6700 Ch2
#E2,db8 / Q29, N6700 Ch3
#E3, db21 / Q63, DACL N25
#E4, db3 / Q64, N6700 Ch4
#E5, db38 / Q65,  DACL N25 (tied together with E3)
#Vgnd, db43 / Q73, DACR N25
channels['E0']=[1,-1,'6700'] 
channels['E1']=[2,-1,'6700']
channels['E2']=[3,-1,'6700']
channels['E3']=[0,1,'N25V']
channels['E4']=[4,-1,'6700']
channels['E5']=[0,1,'N25V']
channels['GND']=[1,1,'N25V']


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
            self.internal_state['ElectrodeConst'] = 'double'
            self.internal_state['SecularZ']=.6
            self.internal_state['SecularY']=0
            self.internal_state['SecularX']=0
            self.internal_state['FreqRF']= 30
            self.internal_state['VoltRF']= 175
            self.internal_state['TrapAZ']= [0,0,1]
            self.internal_state['XYTilt'] = 0
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
            #self.serial[0].write('SYST:REM\n')
            #self.serial[1].write('SYST:REM\n')
            msgs = "SOUR:VOLT? (@1,2,3,4)\n"
            recv = string.split(self.soc.ask(msgs),'\n')[0]
            recv1 = string.split(recv, ',')
            for key in channels:
                if channels[key][2]=='6700':
                    self.internal_state[key] = channels[key][1]*float(recv1[channels[key][0]-1])
            
            for key in channels:
                if(channels[key][2]!='6700'):
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
        elif self.internal_state['ElectrodeConst'] == 'double':
            self.filename = 'SandiaCavityTrapNoConstDoubleElectrodeSize.tsv'
        else:
            self.filename = 'SandiaCavityTrapNoConstGround.tsv'




    def Set6700Electrode(self,channel,value):
        try:
            msg = "SOUR:VOLT:LEV %.5f,(@%i)\n"%(channels[channel][1]*value,channels[channel][0])
            if DEBUG: print msg
            self.soc.write(msg)
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()       

    def SetDACElectrode(self,channel,value):
        try:
            if DEBUG: print 'APPL ' + channels[channel][2] + ', ' + str(value) + ', 0.001\n'
            self.serial[channels[channel][0]].write('APPL ' + channels[channel][2] + ', ' + str(value) + ', 0.01\n')
            time.sleep(.01)
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()       

    def GND(self, value):
        try:
            value=float(value)
            if(channels['GND'][2]=='6700'):
                self.Set6700Electrode('GND',value)
            else:
                self.SetDACElectrode('GND',value)
            self.internal_state['GND']=value
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()

    def E0(self, value):
        try:
            value=float(value)
            if(channels['E0'][2]=='6700'):
                self.Set6700Electrode('E0',value)
            else:
                self.SetDACElectrode('E0',value)
            self.internal_state['E0']=value
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()


    def E1(self, value):
        try:
            value=float(value)
            if(channels['E1'][2]=='6700'):
                self.Set6700Electrode('E1',value)
            else:
                self.SetDACElectrode('E1',value)
            self.internal_state['E1']=value
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()

    def E2(self, value):
        try:
            value=float(value)
            if(channels['E2'][2]=='6700'):
                self.Set6700Electrode('E2',value)
            else:
                self.SetDACElectrode('E2',value)
            self.internal_state['E2']=value
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()

    def E3(self, value):
        try:
            value=float(value)
            if(channels['E3'][2]=='6700'):
                self.Set6700Electrode('E3',value)
            else:
                self.SetDACElectrode('E3',value)
            self.internal_state['E3']=value
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()
  
    def E4(self, value):
        try:
            value=float(value)
            if(channels['E4'][2]=='6700'):
                self.Set6700Electrode('E4',value)
            else:
                self.SetDACElectrode('E4',value)
            self.internal_state['E4']=value
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()
    def E5(self, value):
        try:
            value=float(value)
            if(channels['E5'][2]=='6700'):
                self.Set6700Electrode('E5',value)
            else:
                self.SetDACElectrode('E5',value)
            self.internal_state['E5']=value
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()   
    def E6(self, value):
        try:
            value=float(value)
            if(channels['E6'][2]=='6700'):
                self.Set6700Electrode('E6',value)
            else:
                self.SetDACElectrode('E6',value)
            self.internal_state['E6']=value
            self.internal_state['VertComp']=0
            self.internal_state['HorizComp']=0
        except Exception as e:
            print "Error in setting voltage: ",e
            print traceback.format_exc()                     


    def SecularZ(self, value):
        self.internal_state['SecularZ']=float(value) #takes in value in MHz

    def FreqRF(self, value):
        self.internal_state['FreqRF']=float(value)

    def VoltRF(self,value):
        self.internal_state['VoltRF']=float(value)

    def XYTilt(self, value):
        self.internal_state['XYTilt'] = float(value)

    def VertComp(self,value):
        try:
            value=float(value)
            new={}
            self.internal_state['VertComp']=value
            new['E3']=self.internal_state['E3']+value-self.internal_state['HorizComp']
            new['E4']=self.internal_state['E4']+value-self.internal_state['HorizComp']
            new['E5']=self.internal_state['E5']+value-self.internal_state['HorizComp']
            new['E1']=self.internal_state['E1']+value+self.internal_state['HorizComp']
            new['E2']=self.internal_state['E2']+value+self.internal_state['HorizComp']
            new['E0']=self.internal_state['E0']+value+self.internal_state['HorizComp']
            for i in range(0,6):
                if(channels['E' + str(i)][2]=='6700'):
                    self.Set6700Electrode('E' + str(i),new['E' + str(i)])
                else:
                    self.SetDACElectrode('E' + str(i),new['E' + str(i)])
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()
    def HorizComp(self,value):
        try:
            value=float(value)
            self.internal_state['HorizComp']=value
            new={}
            new['E3']=self.internal_state['E3']-value+self.internal_state['VertComp']
            new['E4']=self.internal_state['E4']-value+self.internal_state['VertComp']
            new['E5']=self.internal_state['E5']-value+self.internal_state['VertComp']
            new['E1']=self.internal_state['E1']+value+self.internal_state['VertComp']
            new['E2']=self.internal_state['E2']+value+self.internal_state['VertComp']
            new['E0']=self.internal_state['E0']+value+self.internal_state['VertComp']
            for i in range(0,6):
                if(channels['E' + str(i)][2]=='6700'):
                    self.Set6700Electrode('E' + str(i),new['E' + str(i)])
                else:
                    self.SetDACElectrode('E' + str(i),new['E' + str(i)])
        except Exception as e:
            print "Error: %s" %(str(e))
            print traceback.format_exc()     
  
    # takes the current electrode values and calculates secular frequencies
    def FindSecularFreqs(self):
        try:
            v_dict={}

            if self.internal_state ['ElectrodeConst'] == 'noconstground' or self.internal_state ['ElectrodeConst'] == 'sideground' or self.internal_state ['ElectrodeConst'] == 'symground':
                v_dict['vg']= self.internal_state['GND']
                if self.internal_state['ElectrodeConst'] == 'noconstground' or self.internal_state['ElectrodeConst']=='double':
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

    def GotoVoltages(self):
        try:
            print "going to voltages"
            cur = {} # current voltages
            tar=self.internal_state #target voltages

            self.serial[0].write('SYST:REM\n')
            self.serial[1].write('SYST:REM\n')
            self.serial[0].write('*CLS\n')
            self.serial[1].write('*CLS\n')
            
            msgs = "SOUR:VOLT? (@1,2,3,4)\n"
            recv = string.split(self.soc.ask(msgs),'\n')[0]
            recv1 = string.split(recv, ',')
            for key in channels:
                if channels[key][2]=='6700':
                    cur[key] = channels[key][1]*float(recv1[channels[key][0]-1])
            
            for key in channels:
                if(channels[key][2]!='6700'):
                    self.serial[channels[key][0]].write('MEAS:VOLT? ' + channels[key][2] + '\n')
                    time.sleep(0.01)
                    cur[key] = round(float(self.serial[channels[key][0]].read(1000).rstrip()),3)
                    # flip sign if negative channels
                    if channels[key][1]==-1:
                        cur[key]=-cur[key]


            diff={}
            maxdiff=0
            for i in range(0,6): # find largest difference
                diff[i]=float(tar["E" + str(i)])-float(cur["E" + str(i)])
                if abs(diff[i]) > maxdiff:
                    maxdiff=abs(diff[i])
                print "diff=%f"%(diff[i])
            diff[7]=float(tar["GND"])-float(cur["GND"])
            steps=int(maxdiff/0.3) # move by 300 mV at a time at most
            print "steps=%d"%(steps)
            for i in range(1,steps+1):
                for j in range(0,6):
                    eval("self.E" + str(j) + '(cur["E'+ str(j) + '"]+diff[' + str(j) + ']/steps*' + str(i) + ")")
                    time.sleep(0.05)
                eval("self.GND(cur['GND']+diff[7]/steps*" + str(i) + ")")
                time.sleep(0.1)
            # set to final voltages in case there were rounding errors
            for j in range(0,6):
                eval("self.E" + str(j) + '(tar["E'+ str(j) + '"])')
                time.sleep(0.05)
            self.GND(tar["GND"])
            print "go to voltages done"
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

            if self.internal_state['XYTilt'] == 0:

                curvature = m_over_Ze * omega_rf**2 * Azz/4 
                constraints = {trap.grad_potential_fn:[0,0,0], trap.hess_potential_fn_ij(2,2):curvature}

            elif self.internal_state['XYTilt'] != 0:
                tilt_theta = np.radians(self.internal_state['XYTilt'])
                Axx = Azz*-1.5
                Ayy = -Axx - Azz
                C = m_over_Ze * omega_rf**2 / 4
                curvature_xx = C * ((Axx*np.cos(tilt_theta))**2 + (Ayy*np.sin(tilt_theta))**2)
                curvature_xy = C * (Axx - Ayy)*np.sin(2*tilt_theta) /2
                curvature_zz = C * Azz
                constraints = {trap.grad_potential_fn:[0,0,0], 
                trap.hess_potential_fn_ij(0,0):curvature_xx,
                trap.hess_potential_fn_ij(0,1):curvature_xy,
                trap.hess_potential_fn_ij(2,2):curvature_zz}
            dcvoltages = trap.find_dc_voltages(constraints)
            print dcvoltages

            for key in dcvoltages:
                dcvoltages[key]=round(dcvoltages[key],3)
                
            if self.internal_state ['ElectrodeConst'] == 'noconstground' or self.internal_state ['ElectrodeConst'] == 'sideground' or self.internal_state ['ElectrodeConst'] == 'symground' or self.internal_state['ElectrodeConst']=='double':
                if self.internal_state['ElectrodeConst'] == 'noconstground' or self.internal_state['ElectrodeConst']=='double':
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
            if self.internal_state ['ElectrodeConst'] == 'noconst' or self.internal_state ['ElectrodeConst'] == 'side' or self.internal_state['ElectrodeConst'] == 'sym':
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
