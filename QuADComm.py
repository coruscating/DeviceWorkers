'''
        Jules Stuart: 2015-10-13
        Communication class for the QuAD boards using the OK library; giving credit where it is due - 
         I copied most of the form of the code below from Helena's PhotonCounterComm.py
        
        Update on 2015-3-4
        I'm going to be switching over to the newer version of the bitfile which has
        firmware for performing ramps and output offsets.


        Available methods:
        setRegister - use the Register Assignment Module to set one of the internal registers
        configureDaughter - update the status of an individual daughter
        
        register map
        0x00            : Address 
        0x01            : value to be loaded into Address
        0x20-21         : ADC single read register

        Address map
        0x0000          : Type register, 8 bit true/false register for ADC/DAC daughter module
        0x0002          : OutputMode register, 8 bit true/false register for Feedback/SingleCMD daughter module
        0x0004          : Range mode register, 8 bit true/false for dual/positive-only mode
        0x0010-0x001F   : DAC single write registers
        0x0080-0x0087   : Source for feedback to daughters 0-7
        0x0090-0x009F   : positive / negative rail registers,e.g. 0x0090-DA0 positive rail, 0x0091-DA0 negative rail

        trigger map
        0x40,0x0-7      : daughter specific registers ready cmd for module 0-7
        0x40,0x9        : general register ready
        0x40,0x010      : get single adc value prompt register
 '''

import ok, struct, time, sys, math
import numpy as np
import matplotlib.pyplot as plt
DEBUG = True
# Local variables
SYSTEMCLOCK = 160.0    #MHz
DEVICESERIAL = "13450006RO"
#DEVICESERIAL = "13450006WW"
# NOTE - with this change it should be able to load the bitfile from any directory
BITFILE = "./QuADController.bit"
SOURCE_LIST = {'ADC0':0x00, 'ADC1':0x01, 'ADC2':0x02, 'ADC3':0x03, 'ADC4':0x04, 'ADC5':0x05, \
                             'ADC6':0x06, 'ADC7':0x07, 'IIR0':0x10, 'IIR1':0x11, 'IIR2':0x12, 'IIR3':0x13, \
                             'IIR4':0x14, 'IIR5':0x15, 'SWP':0x16}

INIT_CONFIG={}
INIT_CONFIG["CHType"]         =["ADC"     , "DAC"     , "DAC"     , "DAC"     , "DAC"     , "DAC"     , "DAC"     , "DAC"]
INIT_CONFIG["CHOutputMode"]   =["Single"  , "Single"  , "Single"  , "Single"  , "Single"  , "Single"  , "Single"  , "Single"]
INIT_CONFIG["CHRangeMode"]    =["Positive", "Positive", "Positive", "Positive", "Positive", "Positive", "Positive", "Positive"]
INIT_CONFIG["CHSource"]       =["ADC0"    , "ADC0"    , "ADC0"    , "ADC0"    , "ADC0"    , "ADC0"    , "ADC0"    , "ADC0"]
INIT_CONFIG["CHPositiveRail"] =[5.0       , 5.0       , 5.0       , 5.0       , 5.0       , 5.0       , 5.0       , 5.0]
INIT_CONFIG["CHNegativeRail"] =[-5.0      , -5.0      , -5.0      , -5.0      , -5.0      , -5.0      , -5.0      , -5.0]
INIT_CONFIG["CHVoltage"]      =[0.0       , 0.0       , 0.0       , 0.0       , 0.0       , 0.0       , 0.0       , 0.0]
INIT_CONFIG["FilterType"]     =["P"       , "P"       , "P"       , "P"       , "P"       , "P"]
INIT_CONFIG["FilterSource"]   =["ADC0"    , "ADC0"    , "ADC0"    , "ADC0"    , "ADC0"    , "ADC0"]
INIT_CONFIG["FilterGain"]     =[1.0       , 1.0       , 1.0       , 1.0       , 1.0       , 1.0       , 1.0       , 1.0]
INIT_CONFIG["InputOffset"]    =[0.0       , 0.0       , 0.0       , 0.0       , 0.0       , 0.0       , 0.0       , 0.0]

class Comm:
    def __init__(self):        
        try: 
            maxLoadAttempts = 10 #Allow for repeated loading to fix a bug I saw once
            loadedBitfile = 1 #Bitfile not yet loaded
            
            self.xem = ok.FrontPanel()
            devices = self.xem.GetDeviceCount()
            print "Found %d attached FPGAs"%(devices)
            
            if (devices >0):
                if (self.xem.OpenBySerial(DEVICESERIAL)==0):
                    print "Opened an FPGA known as %s"%(self.xem.GetDeviceID())
                    
                    print "Now loading PLL configuration..."
                    pll = ok.PLL22150()
                    self.xem.GetEepromPLL22150Configuration(pll)
                    pll.SetVCOParameters(int(SYSTEMCLOCK), 24)    # NOTE - make sure this gives the right frequency
                    pll.SetDiv1(pll.DivSrc_VCO,4)
                    pll.SetOutputSource(0, pll.ClkSrc_Div1By2)
                    pll.SetOutputSource(1, pll.ClkSrc_Div1By2)
                    pll.SetOutputEnable(1, True)
                    print "System clock to be set @ %gMHz"%(pll.GetOutputFrequency(0))
                    print "SPI clock to be set @ %gMHz"%(pll.GetOutputFrequency(1))
                    self.xem.SetPLL22150Configuration(pll)
                    
                    print "Loading the bitfile..."
                    attempts = 0
                    while (attempts <= maxLoadAttempts):
                        loadedBitfile = self.xem.ConfigureFPGA(BITFILE)
                        if (loadedBitfile == 0):
                            print "Bitfile loaded!"
                            break
                        attempts += 1
        
        except Exception as e:
            print "Initialization error" + str(e)
            sys.exit(1)
        try:
            self.internal_state = {}

            for i in range(8):
                self.internal_state["QuADDaughterType_%i"%i]          = "DAC"
                self.internal_state["QuADDaughterOutputMode_%i"%i]    = "Single"
                self.internal_state["QuADDaughterRangeMode_%i"%i]     = "Positive"
                self.internal_state["QuADDaughterSource_%i"%i]        = "ADC0"
                self.internal_state["QuADDaughterPositiveRail_%i"%i]  = 5.0
                self.internal_state["QuADDaughterNegativeRail_%i"%i]  = 0.0
                self.internal_state["QuADDaughterVoltage_%i"%i]       = 0

            for i in range(5):
                self.internal_state["QuADFilterType_%i"%i]    = "P"
                self.internal_state["QuADFilterSource_%i"%i]  = "ADC0"
                self.internal_state["QuADFilterCutoff_%i"%i]  = 20000.0
                self.internal_state["QuADFilterGain_%i"%i]    = 1.0
                self.internal_state["QuADFilterOffset_%i"%i]  = 0.0

            self.internal_state["QuADRampAmplitude"] = 1.0
            self.internal_state["QuADRampFrequency"] = 100.0
            self.internal_state["QuADRampStatus"]    = "Off"

        
            #Populate functions
            try:
                for i,key in enumerate(self.internal_state):
                    if 'QuADDaughter' in key:
                        FuncID,ind = (key.split('QuADDaughter')[1]).split('_')
                        FuncID = 'self.'+FuncID
                        setattr(self,key,lambda x, self=self,ind=ind,FuncID=FuncID:eval(FuncID)(ind,x))
                    elif 'QuADFilter' in key:
                        FuncID,ind = (key.split('QuAD')[1]).split('_')
                        FuncID = 'self.'+FuncID
                        setattr(self,key,lambda x, self=self,ind=ind,FuncID=FuncID:eval(FuncID)(ind,x))
                    if DEBUG: print FuncID,ind

            except Exception as e:
                print 'ERROR in populating functions: \n\n',e
            
            # Now run initialization methods to reach a common start state
            print "Engaging default state..."
            # All daughters initialize as DACs
            self.setRegister(0x0000, 0x00)
            # All daughters initialize into non_feedback mode
            self.setRegister(0x0002, 0x00)
            # Set all DACs into positive mode and write 0 V to each
            for i in range(8):
                self.setRegister(0x0080 + i, SOURCE_LIST["ADC0"])
                self.setRegister(0x0010 + 2*i, 0x0002)
                self.setRegister(0x0011 + 2*i, 0x0020)
                self.xem.ActivateTriggerIn(0x40, i)
                # In positive mode, the code to set zero volts is 0x180000
                self.setRegister(0x0010 + 2*i, 0x0000)
                self.setRegister(0x0011 + 2*i, 0x0018)
                self.xem.ActivateTriggerIn(0x40, i)
                print "Writing 0.0 to DAC at position " + str(i)
            # Set all of the feedback modes to positive only
            self.setRegister(0x0004, 0x00)
            #Set the rail voltages for each DAC
            for i in range(8):
                self.PositiveRail(i, self.internal_state["QuADDaughterPositiveRail_%i"%i])
                self.NegativeRail(i, self.internal_state["QuADDaughterNegativeRail_%i"%i])
            # Update each of the filters to the internal state configuration
            # NOTE - need to replace configureFilter() here to get rid of the extra function
            for i in range(5):
                self.configureFilter(i, self.internal_state["QuADFilterType_%i"%i], \
                    self.internal_state["QuADFilterSource_%i"%i], self.internal_state["QuADFilterCutoff_%i"%i], \
                    self.internal_state["QuADFilterGain_%i"%i], self.internal_state["QuADFilterOffset_%i"%i])
            #Add initialization for the ramp
            self.QuADRampFrequency(self.internal_state["QuADRampFrequency"])
            self.QuADRampAmplitude(self.internal_state["QuADRampAmplitude"])
            self.QuADRampStatus(self.internal_state["QuADRampStatus"])
            print "Default state set.    Welcome to the QuADCon!"

            #sanity checking...
            #self.setRegister(0x0000, 0x01)
            #self.setRegister(0x0084, 0x0010)
        except Exception as e:
            print 'Could not run intialize: \n\n',e
    
    def UPDATE(self):
        for i in range(8):
            if (self.internal_state['QuADDaughterType_%i'%i] == 'ADC'):
                self.Voltage(i)
    
    def STOP(self):
        pass 
    
    # Function to translate ADC code to a voltage
    # NOTE - should be able to adjust/test these parameters
    def codeToVoltage(self,count):
        # Parameters from the fit
        m = 25609.9
        b = 130923.0
        return (float(count)-b)/m
    
    # Function for converting to int from two's complement; copied from stack exchange
    def twos_comp(self, val, bits):
        # val - binary representation of an unsigned number
        # bits - number of bits in the representation
        if (val & (1 << (bits - 1))) != 0:
            val = val - (1 << bits)
        return val
    
    def setRegister(self, address, value):
        # Set the register address and value
        self.xem.SetWireInValue(0x00, address)
        self.xem.SetWireInValue(0x01, value)
        self.xem.UpdateWireIns()
        # Trigger the register addressing module
        self.xem.ActivateTriggerIn(0x40, 9)
    
    def VtoDACCode(self,index,voltage):
        """
            Description
            -----------
            Converts voltage to DAC codeword
        """
        try:
            # Convert the voltage to a DAC code with write prefix
            if (self.internal_state['QuADDaughterRangeMode_%i'%index] == "Positive"):
                if (voltage < 0.0):
                    voltage = 0.0
                    print "Negative voltages not allowed in this mode!"
                code = int((voltage-5.0)/10.0 * 2**20)
                if (voltage < 5):
                    code = (1<<20) + code
            else:
                code = int(voltage/20.0 * 2**20)    
                if (voltage < 0):
                    code = (1<<20) + code
            
            code = code | 0x100000
            return code
        except Exception as e:
            print 'ERROR in V2code: \n\n',e
            raise 
     
    def ADCCodetoV(self,BitString):
        """
            Description
            -----------
            Converts ADC bitstring to voltage
        """

        volts = (float(self.twos_comp(BitString, 20))/(2**19))*10.0  
        return volts

    def Type(self,index, typ=None):
        """
            Description
            -----------
            Changes daughter[index] module between 'ADC' and 'DAC'
        """

        try:
            index     = int(index)
            typ = str(typ)
            self.internal_state["QuADDaughterType_%i"%index] = typ
            # Calculate the range statuses to be written based on the status of all DACs
            DaughterType = sum(map(
                lambda x: int(self.internal_state['QuADDaughterType_%i'%x]=='ADC')<<x, range(8)
                                ))
            

            print '\n\n',DaughterType,'\n\n'
            self.setRegister(0x0000, DaughterType)
            self.xem.ActivateTriggerIn(0x40, index)

        except Exception as e:
            print 'Error in Type: \n\n',e

    def OutputMode(self,index, output_mode=None):
        """
            Description
            -----------
            Changes DAC[index] between feedback and single cmd mode
        """

        try:
            if DEBUG:print 'OutputMode ',index,output_mode
            index = int(index)
            output_mode = str(output_mode)
            self.internal_state["QuADDaughterOutputMode_%i"%index] = output_mode
            # Calculate the range statuses to be written based on the status of all DACs
          
            OutputModeCode =  sum(map(
                lambda x: int(self.internal_state['QuADDaughterOutputMode_%i'%x]=='Feedback')<<x, range(8)
                                ))

            self.xem.ActivateTriggerIn(0x40, index)
            self.setRegister(0x0002, OutputModeCode)
            self.xem.ActivateTriggerIn(0x40, index)


        except Exception as e:
            print 'Error in OutputMode: \n\n',e

    def RangeMode(self,index, rangemode=None):
        """
            Description
            -----------
            Changes DAC[index] between dual-rail and positive-only mode
        """
      
        try:
            if DEBUG: print 'Range mode ',index, rangemode
            index     = int(index)
            rangemode = str(rangemode)
            self.internal_state["QuADDaughterRangeMode_%i"%index] = rangemode
            # Calculate the range statuses to be written based on the status of all DACs
            rangemodecode = sum(map(
                lambda x: int(self.internal_state['QuADDaughterRangeMode_%i'%x]=='Dual')<<x, range(8)
                                ))
            if DEBUG: print rangemodecode
            # Update the range status register
            self.setRegister(0x0004, rangemodecode)

            if (self.internal_state["QuADDaughterRangeMode_%i"%index] == "Positive"):
                self.setRegister(0x0010 + 2*index, 0x0002)
                self.setRegister(0x0011 + 2*index, 0x0020)
            else:
                self.setRegister(0x0010 + 2*index, 0x0000)
                self.setRegister(0x0011 + 2*index, 0x0020)
            self.xem.ActivateTriggerIn(0x40, index)

        except Exception as e:
            print 'Error in RangeMode: \n\n',e

    def Source(self,index, source=None):
        """
            Description
            -----------
            Changes DAC[index] feedback path to source
        """

        try:
            if DEBUG: print index,source
            index = int(index)
            source = str(source)
            self.internal_state["QuADDaughterSource_%i"%index] = source
            # Calculate the range statuses to be written based on the status of all DACs
            self.setRegister(0x0080 + index, SOURCE_LIST[source])
            self.xem.ActivateTriggerIn(0x40, index)

        except Exception as e:
            print 'Error in Source: \n\n',e

    def PositiveRail(self,index, positive_rail=None):
        """
            Description
            -----------
            Changes the positive voltage limit of dac[index]
        """

        try:
            if DEBUG: print 'Positive Rail ',index,positive_rail
            index=int(index)
            positive_rail = float(positive_rail)
            self.internal_state['QuADDaughterPositiveRail_%i'%index] = positive_rail
            positive_code = int((self.internal_state['QuADDaughterPositiveRail_%i'%index])/20.0 * 2**21)
            positive_code = self.twos_comp(positive_code, 21)
            bottomBits = positive_code & 0x00FFFF
            topBits = (positive_code & 0xFF0000) >> 16
            self.setRegister(0x0090 + 2*index, bottomBits)
            self.setRegister(0x0091 + 2*index, topBits)

        except Exception as e:
            print 'Error in Positive Rail: \n\n',e

    def NegativeRail(self,index, negative_rail=None):
        """
            Description
            -----------
            Changes the negative voltage limit of dac[index]
        """

        try:
            if DEBUG: print 'NegativeRail ',index,negative_rail
            index = int(index)
            negative_rail =float(negative_rail)
            self.internal_state['QuADDaughterNegativeRail_%i'%index] = negative_rail
            negative_code = int((self.internal_state['QuADDaughterNegativeRail_%i'%index])/20.0 * 2**21)
            negative_code = self.twos_comp(negative_code, 21)
            bottomBits = negative_code & 0x00FFFF
            topBits = (negative_code & 0xFF0000) >> 16
            self.setRegister(0x00A0 + 2*index, bottomBits)
            self.setRegister(0x00A1 + 2*index, topBits)

        except Exception as e:
            print 'Error in Negative Rail: \n\n',e

    def Voltage(self,index,voltage=None):
        """
            Description
            -----------
            Single write to DAC or single read from ADC
        """
        try:
            if DEBUG: print 'Voltage ',index,voltage
            index   = int(index)
            if self.internal_state['QuADDaughterType_%i'%index] =='DAC':
                voltage = float(voltage)
                print "Writing " + str(voltage) + " to DAC" + str(index)
                #if self.internal_state['QuADDaughterType_%i'%index] == 'Positive':
                code = self.VtoDACCode(index,voltage)
                bottomBits = code & 0x00FFFF
                topBits = (code & 0xFF0000) >> 16
                self.setRegister(0x0010 + 2*index, bottomBits)
                self.setRegister(0x0011 + 2*index, topBits)
                self.xem.ActivateTriggerIn(0x40, index)
                self.internal_state['QuADDaughterVoltage_%i'%index]=voltage

            elif self.internal_state['QuADDaughterType_%i'%index] =='ADC':
                index = int(index)
                self.setRegister(0x01, 0x00 + index)
                self.xem.UpdateWireOuts()
                self.xem.ActivateTriggerIn(0x40, 10)
                lowerByte = self.xem.GetWireOutValue(0x20)
                upperByte = self.xem.GetWireOutValue(0x21)
                lowerByteBinary = "{0:016b}".format(lowerByte)
                upperByteBinary = "{0:016b}".format(upperByte)
                binaryString = upperByteBinary + lowerByteBinary
                binaryString = binaryString[12:]
                #NOTE - need to add a debug option for printing this output
                #print "Got a value: " + binaryString
                #print "Converted int: " + str(int(binaryString, 2))
                shrunkBinaryString = binaryString[1:19]
                #print "Shunk binary: " + shrunkBinaryString
                raw_value = (upperByte << 16) | (lowerByte)
                # NOTE (2/26) - Testing some changes to fix the ADC read error
                #volts = (float(self.twos_comp(raw_value, 20))/(2**19))*10.0 #this is the "original"
                #test_code = (raw_value >> 1)
                #print "{0:18b}".format(test_code)
                #volts = (float(self.twos_comp(raw_value >> 1, 18))/(2**18))*10.0
                #print "Old value: " + str(volts)
                volts = (float(self.twos_comp(int(shrunkBinaryString,2),18))/(2**18))*10.0
                #NOTE - need to add a debug option for printing this output
                #print "New value: " + str(volts)
                self.internal_state['QuADDaughterVoltage_%i'%index] = volts

        except Exception as e:
            print 'Error in Voltage: \n\n',e  


    def configureDaughter(self, index, typ, source, output_mode, range_mode, positive_rail, negative_rail):
        # index - 0 to 7 integer position of the daughter
        # type - string value ("DAC" or "ADC") indicating the type of daughter
        # source - hex code for the source of the DAC output
        # output_mode - string value ("Feedback" or "Single") indicating the write source
        # range_mode - string value ("Positive" or "Dual") indicating the output range
        # positive_rail - float value for the maximum output voltage
        # negative_rail - float value for the minimum output voltage
        try:
            index = int(index)
            # Update the internal state
            self.internal_state['QuADDaughterType_%i'%index]          = typ
            self.internal_state['QuADDaughterSource_%i'%index]        = source
            self.internal_state['QuADDaughterOutputMode_%i'%index]    = output_mode
            self.internal_state['QuADDaughterRangeMode_%i'%index]     = range_mode
            self.internal_state['QuADDaughterPositiveRail_%i'%index]  = float(positive_rail)
            self.internal_state['QuADDaughterNegativeRail_%i'%index]  = float(negative_rail)
            # Calculate the DAC/ADC statuses to be written based on all of the daughters
            DaughterType = sum(map(
                lambda x: int(self.internal_state['QuADDaughterType_%i'%x]=='ADC')<<x, range(8)
                                ))
            # Calculate the feedback statuses to be written based on the status of all DACs
            feedbackStatus = 0
            tempFeedbackStatus = 0     #ugly, ugly, ugly
            for i in range(8):
                if (self.internal_state['QuADDaughterOutputMode_%i'%i]=="Feedback"):
                    feedbackStatus += (1 << i)
                    if (i != index):
                        tempFeedbackStatus += (1 << i)
            # Calculate the range statuses to be written based on the status of all DACs
            RangeMode =  sum(map(
                lambda x: int(self.internal_state['QuADDaughterRangeMode_%i'%x]=='Dual')<<x, range(8)
                                ))
            if (self.internal_state['QuADDaughterRangeMode_%i'%index] == "Positive"):
                rbuf = 1
            else:
                rbuf = 0
            # Calculate code for positive rail; assumed to be > 0
            max_output = int((self.internal_state['QuADDaughterPositiveRail_%i'%index])/20.0 * 2**16)
            # Calculate code for negative rail; may not be < 0
            min_output = int((self.internal_state['QuADDaughterNegativeRail_%i'%index])/20.0 * 2**16)
            if (self.internal_state['QuADDaughterNegativeRail_%i'%index] < 0):
                min_output = (1<<16) + min_output
            # Update the ADC status register
            self.setRegister(0x0000, DaughterType)
            # Update the DAC source register
            self.setRegister(0x0080 + index, SOURCE_LIST[source])
            # Update the rail registers
            self.setRegister(0x0090 + 2*index, max_output)
            self.setRegister(0x0091 + 2*index, min_output)
            # Update the range status register
            self.setRegister(0x0004, RangeMode)
            # Update the feedback status registers; the daughter is first pulled out of feedback mode regardless of status
            self.setRegister(0x0002, tempFeedbackStatus)
            if (output_mode == "Feedback"):
                # Set to 2C mode before setting to feedback mode
                if (range_mode == "Positive"):
                    self.setRegister(0x0010 + 2*index, 0x0012)
                    self.setRegister(0x0011 + 2*index, 0x0020)
                else:
                    self.setRegister(0x0010 + 2*index, 0x0000)
                    self.setRegister(0x0011 + 2*index, 0x0020)
                self.xem.ActivateTriggerIn(0x40, index)
                self.setRegister(0x0002, feedbackStatus)
                print "Setting DAC at position " + str(index) + " to 2C mode"
            else:
                # Remove from feedback mode before setting to binary offset
                #self.setRegister(0x0010 + 2*index, 0x0010 | (rbuf<<1))
                if (range_mode == "Positive"):
                    self.setRegister(0x0010 + 2*index, 0x0012)
                    self.setRegister(0x0011 + 2*index, 0x0020)
                else:
                    self.setRegister(0x0010 + 2*index, 0x0010)
                    self.setRegister(0x0011 + 2*index, 0x0020)
                self.xem.ActivateTriggerIn(0x40, index)
                self.setRegister(0x0002, feedbackStatus)
                print "Setting DAC at position " + str(index) + " to binary offset mode"
        except Exception as e:
            print 'ERROR IN CONFIG: \n',e
    # Function to write a single voltage value to a specified DAC
    def writeSingleDACVoltage(self, index, voltage):
        # index - 0 to 7 integer position of the DAC
        # voltage - -10 to 10 float voltage to be written
        voltage = float(voltage)
        index = int(index)
        # Convert the voltage to a DAC code with write prefix
        # NOTE - need to add a flag here to check which range mode the DAC is in
        if (self.internal_state['QuADDaughterRangeMode_%i'%index] == "Positive"):
            if (voltage < 0.0):
                voltage = 0.0
                print "Negative voltages not allowed in this mode!"
            code = int((voltage)/10.0 * 2**20)
        else:
            code = int((voltage + 10.0)/20.0 * 2**20)    #presumes the DAC is in binary offset and dual rail mode
        code = code | 0x100000
        # Update the internal state
        self.internal_state['DACVoltage'][index]=voltage
        print "Writing " + str(voltage) + " to DAC at position " + str(index)
        # Calculate the upper and lower word corresponding to the voltage
        bottomBits = code & 0x00FFFF
        topBits = (code & 0xFF0000) >> 16
        self.setRegister(0x0010 + 2*index, bottomBits)
        self.setRegister(0x0011 + 2*index, topBits)
        # Activate the trigger corresponding to the DACs index
        self.xem.ActivateTriggerIn(0x40, index)
    
    # Function to control how quickly new voltages change
    def rampToVoltage(self, index, voltage):
        # index - 0 to 7 integer position of the DAC
        # voltage - desired final voltage as a float
        index = int(index)
        voltage = float(voltage)
        stepSize = 0.2
        dt = 50 #ms
        # Check for mode compliance
        if (self.internal_state['QuADDaughterRangeMode'+str(index)] == "Positive"):
            if(voltage < 0.0):
                voltage = 0.0
                print "Negative voltages not allowed in this mode!"
        # Get the current voltage on the chosen DAC
        currentVoltage = self.internal_state['DACVoltage'][index]
        # Update the voltage until it matches the desired level
        while (currentVoltage != voltage):
            if (currentVoltage < voltage):
                newVoltage = currentVoltage + stepSize
                if (newVoltage > voltage):
                    newVoltage = voltage
            else:
                newVoltage = currentVoltage - stepSize
                if (newVoltage < voltage):
                    newVoltage = voltage
            self.writeSingleDACVoltage(index, newVoltage)
            time.sleep(dt*10**-3)
            currentVoltage = self.internal_state['DACVoltage'][index]
    
    def getSingleADCValue(self, index):
        # index - 0 to 7 integer position of the ADC
        index = int(index)
        self.setRegister(0x01, 0x00 + index)
        self.xem.UpdateWireOuts()
        self.xem.ActivateTriggerIn(0x40, 10)        
        lowerByte = self.xem.GetWireOutValue(0x20)
        upperByte = self.xem.GetWireOutValue(0x21)
        lowerByteBinary = "{0:016b}".format(lowerByte)
        upperByteBinary = "{0:016b}".format(upperByte)
        binaryString = upperByteBinary + lowerByteBinary
        #print "Got a value: " + binaryString[12:]
        raw_value = (upperByte << 16) | (lowerByte)
        volts = (float(self.twos_comp(raw_value, 20))/(2**19))*10.0
        #print volts
        self.internal_state['QuADDaughterVoltage_%i'%index] = volts
    
    def pipeRead(self, numPoints, verbose):
        # numPoints - length of the output FIFO
        # verbose - prints extra data from the read
        pointSize = 4
        data = '\x00'*(numPoints*pointSize)
        if (verbose):
            print "Attempting a read!"
        readBytes = self.xem.ReadFromPipeOut(0xA0, data)
        if (verbose):
            print "Read %g bytes!"%(readBytes)
            print repr(data)
        structFormat = 'HH'*numPoints
        return struct.unpack(structFormat, data)
    
    # Simple function that just waits until the FIFO is full and then grabs the data on it
    # NOTE - Should move the number of points and time step to somewhere else
    def getTimeData(self, verbose, divisor):
        timeStep = (1/48000000.0)*(divisor+1)*2 #NOTE- why is it twice the divisor?
        sampleRate = 1/float(timeStep)
        # NOTE - This should be moved to a parameter somewhere that can be initialized at FPGA loading
        points = 8192
        # Initialize array for storing the raw time data
        timeData = [[0 for i in range(points)] for j in range(2)]
        # Trigger the ADC to fill up the FIFO
        self.xem.ActivateTriggerIn(0x40, 8)
        #Sleep to let the FIFO fill up
        # NOTE - Should be able to clear the FIFO of old data before reading new data
        # NOTE - this wait is *definitely* too long
        time.sleep(2)
        
        # NOTE - Replace with a trigger to improve the speed of this process
        self.xem.UpdateWireOuts()
        binary = self.xem.GetWireOutValue(0x22)
        binaryString = '{0:04b}'.format(binary)
        codes = []
        if (binaryString[3] == '1'): #means that the fifo is full
            data = self.pipeRead(points, verbose)
            for i in range(points):
                # NOTE - Why are the incoming words out of order?
                code = data[2*i]*(2**16)+data[2*i+1]
                codes.append(code)
                voltage = codeToVoltage(code)
                # Add the point to the data frame
                timeData[0][i] = timeStep*i
                timeData[1][i] = voltage
        # Print the standard deviation of the codes for debugging purposes
        print "Code sigma = %g"%(np.std(codes))
        
        return timeData
    
    ####END DAUGHTER METHODS####

    ####BEGIN RAMP METHODS####

    def QuADRampAmplitude(self, amplitude):
        amplitude = float(amplitude)
        print "The amplitude is " + str(amplitude)
        self.internal_state["QuADRampAmplitude"] = amplitude
        amplitude_code = int((amplitude/20.0) * 2 **21)
        bottomBits = amplitude_code & 0x00FFFF
        topBits = (amplitude_code & 0xFF0000) >> 16
        self.setRegister(0x00B0, bottomBits)
        self.setRegister(0x00B1, topBits)
        print "Lower byte: " + "{0:016b}".format(bottomBits)
        print "Upper byte: " + "{0:016b}".format(topBits)
        self.configureRamp(self.internal_state["QuADRampAmplitude"], \
            self.internal_state["QuADRampFrequency"])

    def QuADRampFrequency(self, frequency):
        frequency = float(frequency)
        print "The frequency is " + str(frequency)
        self.internal_state["QuADRampFrequency"] = frequency
        self.configureRamp(self.internal_state["QuADRampAmplitude"], \
            self.internal_state["QuADRampFrequency"])

    def QuADRampStatus(self, status):
        print "The ramp status is " + str(status)
        self.internal_state["QuADRampStatus"] = status
        if (self.internal_state["QuADRampStatus"] == "On"):
            print "Switching on"
            self.setRegister(0x00B5, 0x1)
        else:
            self.setRegister(0x00B5, 0x0)

    def configureRamp(self, amplitude, frequency):
        desiredSlope = (amplitude) * frequency * 2
        #Convert to LSB/sec
        fullScale = 20.0
        systemClockFrequency = SYSTEMCLOCK * 10**6
        desiredRatio = desiredSlope/fullScale * 2**20 / systemClockFrequency
        print "Desired ratio = " + str(desiredRatio)
        clkDivGuess = 1
        stepSizeGuess = 1
        while (desiredRatio*(clkDivGuess+1) < 10):
            clkDivGuess += 1
        stepSizeGuess = np.floor(desiredRatio*(clkDivGuess+1))
        print "Step size = " + str(stepSizeGuess)
        print "Clock divider = " + str(clkDivGuess)
        self.setRegister(0x00B4, int(clkDivGuess))
        self.setRegister(0x00B7, int(stepSizeGuess))
    
    ####END RAMP METHODS####

    ####BEGIN FILTER METHODS####

    def filtercalc(self,index):
        """
            Description
            -----------
            Calculates filter parameters for FPGA
        """
        typ     = self.internal_state['QuADFilterType_%i'%index] 
        cutoff  = self.internal_state['QuADFilterCutoff_%i'%index]
        gain    = self.internal_state['QuADFilterGain_%i'%index]
        offset  = self.internal_state['QuADFilterOffset_%i'%index]
        index   = int(index)

        registerOffset = 0x20 + index * 0x10
        # NOTE - This would be the place to add a smarter algorithm for finding these shifts
        a1_shift=8
        a2_shift=8
        b0_shift=4
        b1_shift=4
        b2_shift=4
        self.setRegister(registerOffset | 0xA, (a1_shift << 8) | a2_shift)
        self.setRegister(registerOffset | 0xB, (b0_shift << 8) | b1_shift)
        self.setRegister(registerOffset | 0xC, b2_shift)

        # Constants for calculating filter coefficients
        Ts = 560*10**-9
        f0_bar = np.pi*cutoff*Ts
        K = gain
        Q = 10.0
        g = 20.0
        # Configure coefficients depending on the filter type
        if (typ == "P"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=K
            b1_raw=0.0
            b2_raw=0.0
        elif (typ == "I"):
            a1_raw = 1
            a2_raw = 0.0
            b0_raw = K*f0_bar
            b1_raw = K*f0_bar
            b2_raw = 0.0
        elif (typ == "P_Lag"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=0.0
            b1_raw=K     
            b2_raw=0.0
        elif (typ == "P_LagLag"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=0.0
            b1_raw=0.0     
            b2_raw=K
        elif (typ == "FIR_TEST"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=K/2
            b1_raw=K/2    
            b2_raw=0.0
        elif (typ == "LP"):
            a1_raw = (1-f0_bar)/(1+f0_bar)
            a2_raw = 0.0
            b0_raw = K*f0_bar/(1+f0_bar)
            b1_raw = K*f0_bar/(1+f0_bar)
            b2_raw = 0.0
        elif (typ == "HP"):
            a1_raw = (1-f0_bar)/(1+f0_bar)
            a2_raw = 0.0
            b0_raw = K/(1+f0_bar)
            b1_raw = -K/(1+f0_bar)
            b2_raw = 0.0
        elif (typ == "PI"):
            a1_raw = (1-f0_bar/g)/(1+f0_bar/g)
            a2_raw = 0.0
            b0_raw = K*(1+f0_bar)/(1+f0_bar/g)
            b1_raw = -K*(1-f0_bar)/(1+f0_bar/g)
            b2_raw = 0.0
        elif (typ == "LP2"):
            a1_raw = 2*(1-f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            a2_raw = -(1-f0_bar/Q+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b0_raw = K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
            b1_raw = 2*K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
            b2_raw = K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
        elif (typ == "NOTCH"):
            a1_raw = 2*(1-f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            a2_raw = -(1-f0_bar/Q+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b0_raw = K*(1+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b1_raw = -2*K*(1-f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b2_raw = K*(1+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
        # Set the coefficient shifts
        # NOTE - This would be the place to add a smarter algorithm for finding these shifts
        a1_shift=8
        a2_shift=8
        b0_shift=4
        b1_shift=4
        b2_shift=4
        self.setRegister(registerOffset | 0xA, (a1_shift << 8) | a2_shift)
        self.setRegister(registerOffset | 0xB, (b0_shift << 8) | b1_shift)
        self.setRegister(registerOffset | 0xC, b2_shift)

        # Adjust the coefficient values and write
        a1_in = int((1<<(17-a1_shift))*a1_raw)
        a2_in = int((1<<(17-a2_shift))*a2_raw)
        b0_in = int((1<<(17-b0_shift))*b0_raw)
        b1_in = int((1<<(17-b1_shift))*b1_raw)
        b2_in = int((1<<(17-b2_shift))*b2_raw)

        return [a1_in,a2_in,b0_in,b1_in,b2_in]

    def FilterType(self,index, typ):
        """
            Description
            -----------
            Specifies filter type, low pass, high pass etc...
        """

        try:
            index = int(index)
            typ   = str(typ)
            self.internal_state['QuADFilterType_%i'%index]   = typ

            registerOffset = 0x20 + index * 0x10

            filtercoeff = self.filtercalc(index)

            for i,coeff in enumerate(filtercoeff):  
                word1 = coeff & 0xFFFF
                word2 = (coeff >> 16) & 0x0003
                self.setRegister(registerOffset | 2*i, word1)
                self.setRegister(registerOffset | 2*i+1, word2)
        except Exception as e:
            print 'Error in FilterType: \n\n',e

    def FilterSource(self,index, source):
        """
            Description
            -----------
            Specifies filter source, e.g. ADC0, or IIR0
        """
        try:
            if DEBUG: print 'Filter source ',index,source
            index = int(index)
            source= str(source)
            self.internal_state['QuADFilterSource_%i'%index]   = source

            registerOffset = 0x20 + index * 0x10

            filtercoeff = self.filtercalc(index)

            for i,coeff in enumerate(filtercoeff):  
                word1 = coeff & 0xFFFF
                word2 = (coeff >> 16) & 0x0003
                self.setRegister(registerOffset | 2*i, word1)
                self.setRegister(registerOffset | 2*i+1, word2)
        except Exception as e:
            print 'Error in PilterSource: \n\n',e
    def FilterCutoff(self,index, cutoff):
        """
            Description
            -----------
            Specifies filter cut off frequency [Hz]
        """
        try:
            if DEBUG: print 'Filter cutoff ',index,cutoff
            index = int(index)
            cutoff= float(cutoff)
            self.internal_state['QuADFilterCutoff_%i'%index]   = cutoff

            registerOffset = 0x20 + index * 0x10

            filtercoeff = self.filtercalc(index)

            for i,coeff in enumerate(filtercoeff):  
                word1 = coeff & 0xFFFF
                word2 = (coeff >> 16) & 0x0003
                self.setRegister(registerOffset | 2*i, word1)
                self.setRegister(registerOffset | 2*i+1, word2)
        except Exception as e:
            print 'Error in FilterCutOff: \n\n',e

    def FilterGain(self,index, gain):
        """
            Description
            -----------
            Specifies filter gain
        """
        try:
            if DEBUG: print 'Filter gain ',index,gain
            index = int(index)
            gain  = float(gain)
            self.internal_state['QuADFilterGain_%i'%index]   = gain

            registerOffset = 0x20 + index * 0x10

            filtercoeff = self.filtercalc(index)

            for i,coeff in enumerate(filtercoeff):  
                word1 = coeff & 0xFFFF
                word2 = (coeff >> 16) & 0x0003
                self.setRegister(registerOffset | 2*i, word1)
                self.setRegister(registerOffset | 2*i+1, word2)
        except Exception as e:
            print 'Error in FilterGain: \n\n',e

    def FilterOffset(self,index, offset):
        """
            Description
            -----------
            Specifies filter type, low pass, high pass etc...
        """
        try:
            if DEBUG: print 'Filter offset ',index,offset
            index = int(index)
            offset= float(offset)
            self.internal_state['QuADFilterOffset_%i'%index]   = offset

            registerOffset = 0x20 + index * 0x10
            #NOTE (2/29) - Quickly changing this method to get the offsets working again
            code = int((offset)/20.0 * 2**21)
            code = self.twos_comp(code, 21)
            word1 = code & 0x00FFFF
            word2 = (code & 0xFF0000) >> 16
            self.setRegister(registerOffset | 0xD, word1)
            self.setRegister(registerOffset | 0xE, word2)

           # filtercoeff = self.filtercalc(index)

            #for i,coeff in enumerate(filtercoeff): 
            #    word1 = coeff & 0xFFFF
            #    word2 = (coeff >> 16) & 0x0003
            #    self.setRegister(registerOffset | 2*i, word1)
            #    self.setRegister(registerOffset | 2*i+1, word2)
        except Exception as e:
            print 'Error in FilterOffset: \n\n',e
    
    def configureFilter(self, index, typ, source, cutoff, gain, offset):
        # Update the internal state
        cutoff  = float(cutoff)
        gain    = float(gain)
        offset  = float(offset)
        index   = int(index)
        self.internal_state['QuADFilterType_%i'%index]   = typ
        self.internal_state['QuADFilterSource_%i'%index] = source
        self.internal_state['QuADFilterCutoff_%i'%index] = cutoff
        self.internal_state['QuADFilterGain_%i'%index]   = gain
        self.internal_state['QuADFilterOffset_%i'%index] = offset
        # Update the filter source
        self.setRegister(0x0088 + index, SOURCE_LIST[source])
        # Set the register offset
        registerOffset = 0x20 + index * 0x10
        # Set the pipeline delays
        # NOTE - values to stick with should be 0, 10, 12
        delay_a = 0
        delay_b = 10
        delay_c = 12
        code = (delay_a << 10) | (delay_b << 5) | (delay_c);
        binaryCode = "{0:016b}".format(code)
        print "Delay code = " + binaryCode
        self.setRegister(registerOffset | 0xF, code)
        # Set the filter offset
        code = int((offset)/20.0 * 2**21)
        code = self.twos_comp(code, 21)
        word1 = code & 0x00FFFF
        word2 = (code & 0xFF0000) >> 16
        self.setRegister(registerOffset | 0xD, word1)
        self.setRegister(registerOffset | 0xE, word2)
        # Constants for calculating filter coefficients
        Ts = 560*10**-9
        f0_bar = np.pi*cutoff*Ts
        K = gain
        Q = 10.0
        g = 20.0
        # Configure coefficients depending on the filter type
        if (typ == "P"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=K
            b1_raw=0.0
            b2_raw=0.0
        elif (typ == "I"):
            a1_raw = 1
            a2_raw = 0.0
            b0_raw = K*f0_bar
            b1_raw = K*f0_bar
            b2_raw = 0.0
        elif (typ == "P_Lag"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=0.0
            b1_raw=K     
            b2_raw=0.0
        elif (typ == "P_LagLag"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=0.0
            b1_raw=0.0     
            b2_raw=K
        elif (typ == "FIR_TEST"):
            a1_raw=0.0
            a2_raw=0.0
            b0_raw=K/2
            b1_raw=K/2    
            b2_raw=0.0
        elif (typ == "LP"):
            a1_raw = (1-f0_bar)/(1+f0_bar)
            a2_raw = 0.0
            b0_raw = K*f0_bar/(1+f0_bar)
            b1_raw = K*f0_bar/(1+f0_bar)
            b2_raw = 0.0
        elif (typ == "HP"):
            a1_raw = (1-f0_bar)/(1+f0_bar)
            a2_raw = 0.0
            b0_raw = K/(1+f0_bar)
            b1_raw = -K/(1+f0_bar)
            b2_raw = 0.0
        elif (typ == "PI"):
            a1_raw = (1-f0_bar/g)/(1+f0_bar/g)
            a2_raw = 0.0
            b0_raw = K*(1+f0_bar)/(1+f0_bar/g)
            b1_raw = -K*(1-f0_bar)/(1+f0_bar/g)
            b2_raw = 0.0
        elif (typ == "LP2"):
            a1_raw = 2*(1-f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            a2_raw = -(1-f0_bar/Q+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b0_raw = K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
            b1_raw = 2*K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
            b2_raw = K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
        elif (typ == "NOTCH"):
            a1_raw = 2*(1-f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            a2_raw = -(1-f0_bar/Q+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b0_raw = K*(1+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b1_raw = -2*K*(1-f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
            b2_raw = K*(1+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
        # Set the coefficient shifts
        # NOTE - This would be the place to add a smarter algorithm for finding these shifts
        a1_shift=8
        a2_shift=8
        b0_shift=4
        b1_shift=4
        b2_shift=4
        self.setRegister(registerOffset | 0xA, (a1_shift << 8) | a2_shift)
        self.setRegister(registerOffset | 0xB, (b0_shift << 8) | b1_shift)
        self.setRegister(registerOffset | 0xC, b2_shift)
        # Adjust the coefficient values and write
        a1_in = int((1<<(17-a1_shift))*a1_raw)
        a2_in = int((1<<(17-a2_shift))*a2_raw)
        b0_in = int((1<<(17-b0_shift))*b0_raw)
        b1_in = int((1<<(17-b1_shift))*b1_raw)
        b2_in = int((1<<(17-b2_shift))*b2_raw)
        
        print "a1 = " + str(a1_in)
        word1 = a1_in & 0xFFFF
        word2 = (a1_in >> 16) & 0x0003
        self.setRegister(registerOffset | 0x0, word1)
        self.setRegister(registerOffset | 0x1, word2)
        print "a2 = " + str(a2_in)
        word1 = a2_in & 0xFFFF
        word2 = (a2_in >> 16) & 0x0003
        self.setRegister(registerOffset | 0x2, word1)
        self.setRegister(registerOffset | 0x3, word2)
        print "b0 = " + str(b0_in)
        word1 = b0_in & 0xFFFF
        word2 = (b0_in >> 16) & 0x0003
        self.setRegister(registerOffset | 0x4, word1)
        self.setRegister(registerOffset | 0x5, word2)
        print "b1 = " + str(b1_in)
        word1 = b1_in & 0xFFFF
        word2 = (b1_in >> 16) & 0x0003
        self.setRegister(registerOffset | 0x6, word1)
        self.setRegister(registerOffset | 0x7, word2)
        print "b2 = " + str(b2_in)
        word1 = b2_in & 0xFFFF
        word2 = (b2_in >> 16) & 0x0003
        self.setRegister(registerOffset | 0x8, word1)
        self.setRegister(registerOffset | 0x9, word2)
