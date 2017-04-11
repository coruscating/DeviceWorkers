'''
    MG: 2014-10-19
    Communication class for XDAC_V12, electrode controller for the X88 experiment.
    Type: Digilent nexys3 FPGA controls 6 Dense dac ad5360 chips, communication is 
    done through FPGAlink https://github.com/makestuff/libfpgalink/wiki/FPGALink
    The current version is for the Sandia Cavity trap. 

    returns a list of electrode values
    
    STATUS TIMESTAMP {'Q1': 1.2045, ......}

'''



import socket
import time
import sys
import os
import numpy as np
import string
import fpgalink2 as fpgalink
import math
import struct
import traceback



#Define global variables
DEBUG = False
REFVOLTAGE = 5.00
BITPRECISION = 16
ELECTRODEMAP = '/media/Wigner-1TB/Dropbox/Code/Python/XDAC_control/X88ControlWiringMap1.txt'
LOADFILE = "/media/Wigner-1TB/Dropbox/Code/FPGA/Verilog/QuantaCode/XDAC/XDAC_V1.2_MultiChip_MultiBoard/XDAC_V12.xsvf"






class Comm:
    def __init__(self,device='1443:0007', loadxsvf = False, filename = ''):
        """
            Initialises XDAC communication. 
                device: e.g. nexys3 = 1443:0007
                loadxsvf: load file to fpga?
                filename: where is the file you want to load.
            initialization will then create a handle to the device, 
            which will be used to write / read while the instance remains.
                WARNING: to be checked... not sure what would happen if a second 
                instance is created... UPDATE: second instance destroys first instance... 
                only 1 fpgalink device can run at a time.
            Then, a dictionary is created to map electrode name to a bit string... 
            See XDAC_channel_conversion.py for details
            
            initializes MTserver variables
        """
        #Create device handle
        if loadxsvf:
            print 'Current load file = %s'%(LOADFILE)
        else:
            try:
                self.device = device
                print 'Connecting to device %s...'%(self.device)
                self.handle = fpgalink.flOpen(self.device)
                print '...Device connected'
            except:
                print 'Could not connect to device %s, reload xsvf file'%(self.device)
                try:
                    print '...Attempting to load xsvf file'
                    os.system('flcli -v 1443:0007 -i 1443:0007 -s -x %s'%(LOADFILE))
                    print ' Load file successful'
                    print '...'
                    time.sleep(0.1)
                    print '...'
                    self.device = device
                    print 'Connecting to device %s...'%(self.device)
                    self.handle = fpgalink.flOpen(self.device)
                    print '...Device connected'
                except: 
                    print '...Could not connect to device, check port availability'
                    sys.exit(1)
                    
        #Create dictionary map
        try:
            f = open(ELECTRODEMAP,'r')
            filecontent = string.split(f.read(),'\n')
            self.XMAP = {}
            for line in filecontent:
                try:
                    lineval = string.split(line,', ')
                    self.XMAP[lineval[2]] = [lineval[-2],lineval[-3]]

                except: pass

        except Exception as e:
            print 'Could not load electrode map:',e
            sys.exit(1)
            
        #Initialize MTserver variables
        self.internal_state = {}
        for key in self.XMAP.keys():
            self.internal_state[key] = 0.0
        self.internal_state['GlobalCompensateVertical']=0
        self.internal_state['GlobalCompensateHorizontal']=0
        self.internal_state['ZoneCompensateHorizontal']=0
        self.internal_state['ZoneCompensateVertical']=0
        self.internal_state['Zone']=0
        self.internal_state['ZoneMids']=0
        self.internal_state['ZoneSide']=0
        self.internal_state['ZoneEnds']=0    
        
    def SETVOLTAGE(self, channel, value):
        """
            prepares and sends the set voltage command to the 
            fpga
            channel: electrode name e.g. 'Q02'
            value:  voltage value to be set, float e.g. 3.21
        """
        #Make bytearray to be sent
        try:
            #Convert voltage to bit string
            valuebitstring = self.convert_value(float(value))
            
            #convert channel to bit string
            if channel in self.XMAP.keys():
                DicConvert = self.XMAP[channel]
                channelbitstring = DicConvert[1]    
                if DicConvert[0] =='-':
                    print channel
                    raise
            else:
                print 'WARNING: Electrode name invalid'
                raise
            #make total bit string
            totalbitstring ='%s%s'%(channelbitstring,valuebitstring)

            #convert to bytes
            bytestring = ''
            for x in range(0,len(totalbitstring)/8):
                bytestring += struct.pack('c',chr(int(totalbitstring[8*x:8+8*x],2)) )
            #convert to byte array
            byarray = bytearray(bytestring)      
        except Exception as e:
            print 'WARNING: Failed to create bytearray:',e
            
            
        #Attempt to send bytearray on FPGA USB channel 1
        try:
            if DicConvert[0] =='-':
                raise
            else:
                #Update FPGA
                self.send_command(int(DicConvert[0]),byarray)
                #Update internal_state
                self.internal_state[channel] = float(value)
        except Exception as e:
            print 'WARNING: Could not send command:',e

    def GLOBALCOMPENSATEVERTICAL(self, value):
        '''
            Global vertical compensation, changes the value on the central ground electrode
        '''
        for i in range(1,37):
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]-self.internal_state['GlobalCompensateHorizontal']+float(value))
            time.sleep(0.01)
        for i in range(37,73):
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]-self.internal_state['GlobalCompensateHorizontal']+float(value))
            time.sleep(0.01)
        self.internal_state['GlobalCompensateVertical']=float(value)
        
    def GLOBALCOMPENSATEHORIZONTAL(self, value):
        '''
            Global horizontal compensation, adds value to Q1-Q36 and subtracts value from Q37-Q72
        '''
        for i in range(1,37):
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]-self.internal_state['GlobalCompensateHorizontal']+float(value))
            time.sleep(0.01)
        for i in range(37,73):
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]+self.internal_state['GlobalCompensateHorizontal']-float(value))
            time.sleep(0.01)
        self.internal_state['GlobalCompensateHorizontal']=float(value)


    def GLOBALSETMIDS(self,value):
        '''
            Sets global 'mids' value, sets alternating electrodes on one side to value
        '''
        for i in range(1,37):
            if i%2==1:
                if DEBUG: print "setting electrode %d to Vmid %f" %(i, float(value))
                self.SETVOLTAGE('Q' + str(i), float(value))
                time.sleep(0.01)
            
            
    def GLOBALSETENDS(self,value):
        '''
            Sets global 'ends' values, sets alternating electrodes on one side to value, these are interleaved with mids
        '''
        for i in range(1,37):
            if i%2==0:
                if DEBUG: print "setting electrode %d to Vend %f" %(i, float(value))
                self.SETVOLTAGE('Q' + str(i), float(value))
                time.sleep(0.01)

            
    def GLOBALSETSIDE(self,value):
        '''
            Sets electrode Q37-Q72 to value.
        '''                    
        for i in range(37,73):
            if DEBUG: print "setting electrode %d to Vside %f"%(i,float(value))
            self.SETVOLTAGE('Q'+str(i),float(value))


    def GND(self,value):
        '''
            sets the central ground electrode to value
        '''
        self.SETVOLTAGE('Q73',float(value))

    def ZoneCompensateVertical(self, value):
        zone=self.internal_state["Zone"]
        for i in [zone-1,zone,zone+1]:
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]-self.internal_state['ZoneCompensateVertical']+float(value))
            time.sleep(0.01)
        for i in [zone+35,zone+36,zone+37]:
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]-self.internal_state['ZoneCompensateVertical']+float(value))
            time.sleep(0.01)
        self.internal_state['ZoneCompensateVertical']=float(value)


    def ZoneCompensateHorizontal(self, value):
        zone=self.internal_state["Zone"]
        for i in [-1, 0, 1]:
            self.SETVOLTAGE('Q%i'%(zone+i),self.internal_state['Q%i'%(zone+i)]-self.internal_state['ZoneCompensateHorizontal']+float(value))
            self.SETVOLTAGE('Q%i'%(zone+i+36),self.internal_state['Q%i'%(zone+i+36)]+self.internal_state['ZoneCompensateHorizontal']-float(value))
        '''
        for i in [zone-1,zone,zone+1]:
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]-self.internal_state['ZoneCompensateHorizontal']+float(value))
            time.sleep(0.01)
        for i in [zone+35,zone+36,zone+37]:
            self.SETVOLTAGE('Q%i'%(i),self.internal_state['Q%i'%(i)]+self.internal_state['ZoneCompensateHorizontal']-float(value))
            time.sleep(0.01)
        '''
        self.internal_state['ZoneCompensateHorizontal']=float(value)

    def Zone(self, value):
        self.internal_state["Zone"]=int(value)
        self.internal_state['ZoneCompensateVertical']=0
        self.internal_state['ZoneCompensateHorizontal']=0

        
    def ZoneSide(self, value):
        zone=self.internal_state["Zone"]
        try:
        
            self.SETVOLTAGE('Q'+str(int(zone)+36),float(value))
            time.sleep(0.01)
            self.SETVOLTAGE('Q'+str(int(zone)+35),float(value))
            time.sleep(0.01)
            self.SETVOLTAGE('Q'+str(int(zone)+37),float(value))
            time.sleep(0.01)
            self.internal_state['ZoneSide']=float(value)
            self.internal_state['ZoneCompensateVertical']=0
            self.internal_state['ZoneCompensateHorizontal']=0
        except:
            print 'Could not set zone side values'
            
    def ZoneEnds(self, value):
        zone=self.internal_state["Zone"]
        
        try:
        
            self.SETVOLTAGE('Q'+str(int(zone)+1),float(value))
            time.sleep(0.01)
            self.SETVOLTAGE('Q'+str(int(zone)-1),float(value))
            self.internal_state['ZoneEnds']=float(value)
            self.internal_state['ZoneCompensateVertical']=0
            self.internal_state['ZoneCompensateHorizontal']=0
        except:
            print 'Could not set ends side values'
            
    def ZoneMids(self, value):
        
        zone=self.internal_state["Zone"]
        try:
        
            self.SETVOLTAGE('Q'+str(zone),float(value))
            time.sleep(0.01)
            self.internal_state['ZoneMids']=float(value)
            self.internal_state['ZoneCompensateVertical']=0
            self.internal_state['ZoneCompensateHorizontal']=0

        except:
            print 'Could not set mids side values'
                                
    def convert_value(self,value):
        """
            Helper to convert voltage float to bit string
            value: float, between -REFVOLTAGE, + REFVOLTAGE
            checks that the voltage is in range, converts to int in range, then returns binary value
        """
        try:
            if( np.abs(value) <= 2*REFVOLTAGE ): 
                val = int(np.floor( ((value+2*REFVOLTAGE) / (4*REFVOLTAGE) )*(2**BITPRECISION) ) )
                rv = string.split(bin(val),'b')[1]
            else:
                print 'WARNING: voltage not in allowed range.'
                raise ValueError
            if len(rv) < 16:
                rv = rv.zfill(16)
        except Exception as e:
            print 'WARNING: Could not convert value:',e
            raise
        

        return rv
    
    
    def send_command(self,channel,msg):
        """
            send bytearray msg to the fpga on specified channel
            see fpgalink2.py for details
            channel: int, 1-... see bellow
            msg: bytearray, see set_voltage for format 
        
        """
        try:
            if channel == 0:
                fpgalink.flWriteChannel(self.handle,1000,0x00,msg)
            elif channel == 1:
                fpgalink.flWriteChannel(self.handle,1000,0x01,msg)
            elif channel == 2:
                fpgalink.flWriteChannel(self.handle,1000,0x02,msg)
            elif channel == 3:
                fpgalink.flWriteChannel(self.handle,1000,0x03,msg)
            elif channel == 4:
                fpgalink.flWriteChannel(self.handle,1000,0x04,msg)
            elif channel == 5:
                fpgalink.flWriteChannel(self.handle,1000,0x05,msg)    
            else:
                print 'Update channels...'
        except Exception as e:
            print 'WARNING: Error sending command:',e
    
    def read_command(self,channel,numbytes):
        '''
            reads numbytes from FPGA USB channel, 
            See fpgalink2.py for details
            channel: int, 1...
            numbytes: int
            returns bytearray received
        '''
        if channel ==0:
            rv =fpgalink.flReadChannel(self.handle, 1000, 0x00, numbytes) 
        elif channel ==1:
            rv =fpgalink.flReadChannel(self.handle, 1000, 0x01, numbytes) 
        elif channel ==2:
            rv =fpgalink.flReadChannel(self.handle, 1000, 0x02, numbytes) 
        elif channel ==3:
            rv =fpgalink.flReadChannel(self.handle, 1000, 0x03, numbytes) 
        elif channel ==4:
            rv =fpgalink.flReadChannel(self.handle, 1000, 0x04, numbytes) 
        return rv

                 
    def STOP(self):
        """
            Closes device handle
            See fpgalink2.py for details
        """
        print '... Closing device %s handle...'%(self.device)
        try:   
            fpgalink.flClose(self.handle)
        except Exception as e:
            print 'Error closing device handle:',e
            
            
    def UPDATE(self):
        '''
            currently nothing to be updated... variables only stored on python side
        '''
        return self.internal_state

    def METHODSAVAILABLE(self):
        availmeth = ['SETVOLTAGE']
        return availmeth



if __name__ == "__main__":
    #test functionality
    test = COMM('1443:0007')

    #Vend=2.735/4.0
    #Vmid=-5.134/4.0
    #Vgnd=0.1
    
    # House values
    #Vend=4.018/6.0
    #Vmid=-8.0/6.0
    #Vgnd=-0.2/6.0

    # House asymmetric
    Vscale=1.0
    Vend=1.57535*Vscale
    Vmid=-2.27058*Vscale
    Vside=-0.2894*Vscale
    Vgnd=-0.5*Vscale
   
    # House asymmetric test 1
    #Vscale=2.0
    #Vend=1.57535*Vscale
    #Vmid=-2.15*Vscale
    #Vside=-0.2894*0.55*Vscale
    #Vgnd=-0.35*Vscale
   
    #Vend=-8
    #Vmid=5.5


    #symmmetric
    #Vend=-1.0
    #Vmid=0.55
    #Vgnd=-0.2/3.0
    
    #for i in range(1,73):
    for i in range(1,37):

        
        #if i%4==1 or i%4==2:
        if i%2==1:
            print "setting electrode %d to Vmid %f" %(i, Vmid)
            test.SETVOLTAGE('Q' + str(i), Vmid)
            time.sleep(0.01)
        else:
            print "setting electrode %d to Vend %f" %(i, Vend)
            test.SETVOLTAGE('Q' + str(i), Vend)
            time.sleep(0.01)

    print 'Setting 37 - 72 to Vside %f'%(Vside)
    for i in range(37, 73):
        
        test.SETVOLTAGE('Q' + str(i), Vside)
        time.sleep(0.01)       
    
    print 'Setting Center ground to Vgnd %f'%(Vgnd)
    test.SETVOLTAGE('Q73',Vgnd)
    
    test.global_compensateHor(0.125)
    test.global_compensateVert(-0.12)
    
    '''
    for i in range(10):
        time.sleep(0.1)
        test.set_voltage('Q41',1*np.sin(2*np.pi*i/100))
        test.set_voltage('Q19',1*np.sin(2*np.pi*i/100))
    '''
    
    #for i in range(1,70):
     #   time.sleep(0.1)
      #  electrode = 'Q'+str(i)
       # test.set_voltage(electrode,i/25.0)
        #print i
    
    test.STOP()


