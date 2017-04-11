'''
    Jules Stuart: 2015-10-13
    Communication class for the QuAD boards using the OK library; giving credit where it is due - 
     I copied most of the form of the code below from Helena's PhotonCounterComm.py
    
    Available methods:
    setRegister - use the Register Assignment Module to set one of the internal registers
    configureDaughter - update the status of an individual daughter
    
    Edit on 2016-2-13
    I will be adding in the ability to output live data for viewing in an oscilloscope-style
    output.  At first, I just want to feed out randomly-generated data, independent of the
    connection to the QuAD.
	
	Edit on 2016-2-22
	I'm now going to add in the interface for the new version of the ramp generator.  I'm also going
	to try to eliminate some unused methods
	Need to remember that I've switched to a new bitfile.  I didn't want to replace the old one
	just yet since this might break everything.
    
    Edit on 2016-2-23
    Now I'm finally getting rid of all the references to binary offset mode.  This should simplify
    the methods for changing the feedback status of the daughters
 '''

import ok, struct, time, sys, math
import numpy as np
import matplotlib.pyplot as plt

# Local variables
FREQUENCY = 180.0  #MHz
#DEVICESERIAL = "13450006RO"
DEVICESERIAL = "13450006WW"
# NOTE - with this change it should be able to load the bitfile from any directory
BITFILE = "./NewQuADController.bit"
SOURCE_LIST = {'ADC0':0x00, 'ADC1':0x01, 'ADC2':0x02, 'ADC3':0x03, 'ADC4':0x04, 'ADC5':0x05, \
               'ADC6':0x06, 'ADC7':0x07, 'IIR0':0x10, 'IIR1':0x11, 'IIR2':0x12, 'IIR3':0x13, \
               'IIR4':0x14, 'IIR5':0x15, 'RMP0':0x16}
SINK_LIST   = {'DAC0':0x00, 'DAC1':0x01, 'DAC2':0x02, 'DAC3':0x03, 'DAC4':0x04, 'DAC5':0x05, \
		       'DAC6':0x06, 'DAC7':0x07};


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
          pll.SetVCOParameters(int(FREQUENCY), 24)  # NOTE - make sure this gives the right frequency
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
    
    self.internal_state = {}
    self.internal_state["QuAD674DaughterType"] = ["DAC", "DAC", "DAC", "DAC", "DAC", "DAC", "DAC", "DAC"]
    self.internal_state["QuAD674DaughterOutputMode"] = ["Single", "Single", "Single", "Single", "Single", "Single", "Single", "Single"]
    self.internal_state["QuAD674DaughterRangeMode"] = ["Positive", "Positive", "Positive", "Positive", "Positive", "Positive", "Positive", "Positive"]
    self.internal_state["QuAD674DaughterSource"] = ["ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0"]
    self.internal_state['QuAD674DaughterPositiveRail'] = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]
    self.internal_state['QuAD674DaughterNegativeRail'] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    self.internal_state["QuAD674DaughterVoltage"] = [0,0,0,0,0,0,0,0]
    self.internal_state["QuAD674FilterType"] = ["P", "P", "P", "P", "P", "P"]
    self.internal_state["QuAD674FilterSource"] = ["ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0"]
    self.internal_state["QuAD674FilterCutoff"] = [20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0]
    self.internal_state["QuAD674FilterGain"] = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    self.internal_state["QuAD674FilterOffset"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    # Private internal states for distinguishing ADC voltages from DAC voltages
    self.internal_state["DACVoltage"] = [0,0,0,0,0,0,0,0]
    self.internal_state["ADCVoltage"] = [0,0,0,0,0,0,0,0]

    #Stuff for testing the scope interface
    self.internal_state["SCOPEDATA"] = [[0,0],[1,1],[1,2]]
      
    #Settings for the ramp controller
    self.internal_state["QuAD674RampTarget"] = "DAC0"
    self.internal_state["QuAD674RampFrequency"] = 1000.0
    self.internal_state["QuAD674RampStatus"] = "Off"
    
    # Now run initialization methods to reach a common start state
    print "Engaging default state..."
    # All daughters initialize as DACs
    self.setRegister(0x0000, 0x00)
    # All daughters initialize into non-feedback mode
    self.setRegister(0x0002, 0x00)
    # Update DAC source registers and set each into binary offset mode; RBUF configured for unity
	#ISSUE -  Here is where I need to change the initialization into binary offset mode
    for i in range(8):
      self.setDaughterRails(i, self.internal_state['QuAD674DaughterNegativeRail'][i], \
        self.internal_state['QuAD674DaughterPositiveRail'][i])
      self.setRegister(0x0080 + i, SOURCE_LIST["ADC0"])
      self.setRegister(0x0010 + 2*i, 0x0002)
      self.setRegister(0x0011 + 2*i, 0x0020)
      self.xem.ActivateTriggerIn(0x40, i)
      print "Setting DAC at position " + str(i) + " to twos complement mode"
      self.setRegister(0x0010 + 2*i, 0x0000)
      self.setRegister(0x0011 + 2*i, 0x0018)
      self.xem.ActivateTriggerIn(0x40, i)
      print "Writing 0.0 to DAC at position " + str(i)
    # Set all of the feedback modes to positive only
    self.setRegister(0x0004, 0x00)
    # Set all of the filters to the on state
    # ISSUE - I removed the control for the filter on/off; need to check this more thoroughly
    #self.setRegister(0x0003, 0x003F)
    # Update each of the filters to the internal state configuration
    for i in range(5):
      self.configureFilter(i, self.internal_state["QuAD674FilterType"][i], \
        self.internal_state["QuAD674FilterSource"][i], self.internal_state["QuAD674FilterCutoff"][i], \
        self.internal_state["QuAD674FilterGain"][i], self.internal_state["QuAD674FilterOffset"][i])
    # Update the ramp to the internal state configuration
    self.configureRamp(self.internal_state["QuAD674RampTarget"], self.internal_state["QuAD674RampFrequency"])
    print "Default state set.  Welcome to the QuAD674Con!"
  
  def UPDATE(self):
    #self.internal_state['SCOPEDATA'] = self.getTimeData(False, 10)
    for i in range(len(self.internal_state['QuAD674DaughterType'])):
      if (self.internal_state['QuAD674DaughterType'][i] == 'ADC'):
        self.getSingleADCValue(i)
        self.internal_state['QuAD674DaughterVoltage'][i] = self.internal_state['ADCVoltage'][i]
      else:
        self.internal_state['QuAD674DaughterVoltage'][i] = self.internal_state['DACVoltage'][i]
    pass
  
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
	# address - location of the register in the RAM
	# value - value to write to the specified register
    # Set the register address and value
    self.xem.SetWireInValue(0x00, address)
    self.xem.SetWireInValue(0x01, value)
    self.xem.UpdateWireIns()
    # Trigger the register addressing module
    self.xem.ActivateTriggerIn(0x40, 9)
  
  #Function for setting the step size and clock divider for a ramp
  def configureRamp(self, sink, frequency):
    # sink - position of the DAC targeted by the ramp generator
    # frequency - floating point frequency of the ramp
    frequency = float(frequency)
    self.internal_state['QuAD674RampFrequency'] = frequency
    self.internal_state['QuAD674RampTarget'] = sink
    #Use the positive and negative rail for this target as the extents of the ramp
    minvalue = self.internal_state['QuAD674DaughterNegativeRail'][SINK_LIST[sink]]
    maxvalue = self.internal_state['QuAD674DaughterPositiveRail'][SINK_LIST[sink]]
    print "Range is " + str(maxvalue - minvalue)
    desiredSlope = (maxvalue - minvalue)*frequency*2
    #Convert the slope to LSB/sec
    # NOTE - Need to make these into global variables
    fullScale = 20.0
    systemClock = FREQUENCY * 10**6
    desiredRatio = desiredSlope/fullScale * 2**20 / systemClock
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
    #Update the ramp target
    self.setRegister(0x00B6, SINK_LIST[sink])
  
  #Function to toggle the status of the ramp
  def toggleRamp(self, status):
    # currentStatus = string indicating the current state of the ramp
    self.internal_state['QuAD674RampStatus'] = status
    if (status == "On"):
      print "Turning the ramp on!"
      self.setRegister(0x00B5, 0x1)
    else:
      print "Turning the ramp off!"
      self.setRegister(0x00B5, 0x0)
  
  def configureDaughter(self, index, type, source, output_mode, range_mode):
    # index - 0 to 7 integer position of the daughter
    # type - string value ("DAC" or "ADC") indicating the type of daughter
    # range_mode - string value ("Positive" or "Dual") indicating the output range
    index = int(index)
    # Update the internal state
    self.internal_state['QuAD674DaughterType'][index] = type
    self.internal_state['QuAD674DaughterRangeMode'][index] = range_mode
    # Calculate the DAC/ADC statuses to be written based on all of the daughters
    daughterStatus = 0
    for i in range(len(self.internal_state['QuAD674DaughterType'])):
      if (self.internal_state['QuAD674DaughterType'][i]=="ADC"):
        daughterStatus += (1 << i)
    # NOTE - Even though the mode selection is moved to the other method, I still need to have mode control here
    # Calculate the feedback statuses to be written based on the status of all DACs
    feedbackStatus = 0
    tempFeedbackStatus = 0   #ugly, ugly, ugly
    for i in range(len(self.internal_state['QuAD674DaughterOutputMode'])):
      if (self.internal_state['QuAD674DaughterOutputMode'][i]=="Feedback"):
        feedbackStatus += (1 << i)
        if (i != index):
          tempFeedbackStatus += (1 << i)
    # Calculate the range statuses to be written based on the status of all DACs
    rangeStatus = 0
    for i in range(len(self.internal_state['QuAD674DaughterRangeMode'])):
      if (self.internal_state['QuAD674DaughterRangeMode'][i]=="Dual"):
        rangeStatus += (1 << i)
    
    # Update the ADC status register
    self.setRegister(0x0000, daughterStatus)
    # Update the range status register
    self.setRegister(0x0004, rangeStatus)
    # Update the feedback status registers; the daughter is first pulled out of feedback mode regardless of status
    self.setRegister(0x0002, tempFeedbackStatus)
    if (range_mode == "Positive"):
      self.setRegister(0x0010 + 2*index, 0x0002)
      self.setRegister(0x0011 + 2*index, 0x0020)
      print "Setting DAC at position " + str(index) + " to positive mode"
    else:
      self.setRegister(0x0010 + 2*index, 0x0000)
      self.setRegister(0x0011 + 2*index, 0x0020)
      print "Setting DAC at position " + str(index) + " to dual mode"
    self.xem.ActivateTriggerIn(0x40, index)
    self.setRegister(0x0002, feedbackStatus)
  
  # Function for only changing feedback status and source
  def setDaughterFeedback(self, index, source, outputMode):
    # index - integer index of the daughter to adjust
    # source - string indicating which source should be sunk
    # outputMode - either "Feedback" or "Single," indicating which mode to use
    index = int(index)
    self.internal_state['QuAD674DaughterSource'][index] = source
    self.internal_state['QuAD674DaughterOutputMode'][index] = outputMode
    self.setRegister(0x0080 + index, SOURCE_LIST[source])
    # Calculate the feedback statuses to be written based on the status of all DACs
    feedbackStatus = 0
    for i in range(len(self.internal_state['QuAD674DaughterOutputMode'])):
      if (self.internal_state['QuAD674DaughterOutputMode'][i]=="Feedback"):
        feedbackStatus += (1 << i)
    self.setRegister(0x0002, feedbackStatus)
    print "LOL"
  
  # Function to set the rail of the QuAD daughter output
  def setDaughterRails(self, index, negativeRail, positiveRail):
    # index - integer index of the daughter to adjust
    # negativeRail - float for the negative value
    # positiveRail - float for the positive value
    index = int(index)
    self.internal_state['QuAD674DaughterNegativeRail'][index] = float(negativeRail)
    self.internal_state['QuAD674DaughterPositiveRail'][index] = float(positiveRail)
    # Convert the rail settings to twos complement 20 bit representation
    # ISSUE - Need to account for behaviour in positive only mode
    negativeCode = int((self.internal_state['QuAD674DaughterNegativeRail'][index]/20.0) * 2**20)
    negativeCode = self.twos_comp(negativeCode, 20)
    bottomBits = negativeCode & 0x00FFFF
    topBits = (negativeCode & 0xFF0000) >> 16
    self.setRegister(0x00A0 + 2*index, bottomBits)
    self.setRegister(0x00A1 + 2*index, topBits)
    
    positiveCode = int((self.internal_state['QuAD674DaughterPositiveRail'][index]/20.0) * 2**20)
    positiveCode = self.twos_comp(positiveCode, 20)
    bottomBits = positiveCode & 0x00FFFF
    topBits = (positiveCode & 0xFF0000) >> 16
    self.setRegister(0x0090 + 2*index, bottomBits)
    self.setRegister(0x0091 + 2*index, topBits)
  
  # Function to write a single voltage value to a specified DAC
  def writeSingleDACVoltage(self, index, voltage):
    # index - 0 to 7 integer position of the DAC
    # voltage - -10 to 10 float voltage to be written
    voltage = float(voltage)
    index = int(index)
    # Convert the voltage to a DAC code with write prefix
    # NOTE - need to add a flag here to check which range mode the DAC is in
    if (self.internal_state['QuAD674DaughterRangeMode'][index] == "Positive"):
      if (voltage < 0.0):
        voltage = 0.0
        print "Negative voltages not allowed in this mode!"
      #voltage -= 5.0
      code = int((voltage-5.0)/10.0 * 2**20)
      if (voltage < 5):
        code = (1<<20) + code
    else:
      code = int((voltage)/20.0 * 2**20)  #presumes the DAC is in binary offset and dual rail mode
      if (voltage < 0):
        code = (1<<20) + code
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
    if (self.internal_state['QuAD674DaughterRangeMode'][index] == "Positive"):
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
    print "Got a value: " + binaryString[12:]
    raw_value = (upperByte << 16) | (lowerByte)
    volts = (float(self.twos_comp(raw_value, 20))/(2**19))*10.0
    print volts
    self.internal_state['ADCVoltage'][index] = volts
  
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
  # NOTE (2/15) - I'm changing this function to match the one from the command line
  #  version of the QuADCon
  def getTimeData(self, verbose, divisor):
    timeStep = (1/48000000.0)*(divisor+1)*2 #NOTE- why is it twice the divisor?
    ADCPERIOD = timeStep
    sampleRate = 1/float(timeStep)
    #Hacking in a ceiling to limit the number of points written
    sendcap = 1000
    # NOTE - This should be moved to a parameter somewhere that can be initialized at FPGA loading
    points = 8192
    # Initialize array for storing the raw time data
    # NOTE - Currently assuming only one connected ADC
    #timeData = [[0 for i in range(points)] for j in range(2)]
    timeData = [[0 for i in range(2)] for j in range(sendcap)]
    # Trigger the ADC to fill up the FIFO
    self.xem.ActivateTriggerIn(0x40, 8)
    
    # NOTE - Replace with a trigger to improve the speed of this process
    #self.xem.UpdateWireOuts()
    #binary = self.xem.GetWireOutValue(0x22)
    #binaryString = '{0:04b}'.format(binary)
    #codes = []
    #if (binaryString[3] == '1'): #means that the fifo is full
    #  data = self.pipeRead(points, verbose)
    #  for i in range(points):
    #    # NOTE - Why are the incoming words out of order?
    #    code = data[2*i]*(2**16)+data[2*i+1]
    #    codes.append(code)
    #    voltage = codeToVoltage(code)
    #    # Add the point to the data frame
    #    timeData[0][i] = timeStep*i
    #    timeData[1][i] = voltage
    
  #ADCIndex = 0
  #individualIndex = 0
    attempts = 10
    while (attempts > 0):
      # Keep checking for a full flag from the input FIFO
      self.xem.UpdateTriggerOuts()
      if (self.xem.IsTriggered(0x60, 0x01)):
        print "Triggered!"
        data = self.pipeRead(points, verbose)
        #for i in range(points):
        for i in range(sendcap):
          code = data[2*i]*(2**16)+data[2*i+1]
          voltage = self.codeToVoltage(code)
          # Add the point to the data frame
          timeData[i][0] = ADCPERIOD*i
          timeData[i][1] = voltage
          # Increment the indices
          #ADCIndex = (ADCIndex + 1) % ADCCOUNT
          #if (ADCIndex == 0): individualIndex += 1
        break
      time.sleep(0.1)
      print "No trigger!"
      attempts -= 1

    return timeData
  
  def configureFilter(self, index, type, source, cutoff, gain, offset):
    # Update the internal state
    cutoff = float(cutoff)
    gain = float(gain)
    offset = float(offset)
    index = int(index)
    self.internal_state['QuAD674FilterType'][index] = type
    self.internal_state['QuAD674FilterSource'][index] = source
    self.internal_state['QuAD674FilterCutoff'][index] = cutoff
    self.internal_state['QuAD674FilterGain'][index] = gain
    self.internal_state['QuAD674FilterOffset'][index] = offset
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
    code = int((offset + 10.0)/20.0 * 2**20)
    code = self.twos_comp(code, 20)
    word1 = code & 0xFFFF
    word2 = (code >> 16) & 0x0003
    self.setRegister(registerOffset | 0xD, word1)
    self.setRegister(registerOffset | 0xE, word2)
    # Constants for calculating filter coefficients
    Ts = 560*10**-9
    f0_bar = np.pi*cutoff*Ts
    K = gain
    Q = 10.0
    g = 20.0
    # Configure coefficients depending on the filter type
    if (type == "P"):
      a1_raw=0.0
      a2_raw=0.0
      b0_raw=K
      b1_raw=0.0
      b2_raw=0.0
    elif (type == "I"):
      a1_raw = 1
      a2_raw = 0.0
      b0_raw = K*f0_bar
      b1_raw = K*f0_bar
      b2_raw = 0.0
    elif (type == "P_Lag"):
      a1_raw=0.0
      a2_raw=0.0
      b0_raw=0.0
      b1_raw=K   
      b2_raw=0.0
    elif (type == "P_LagLag"):
      a1_raw=0.0
      a2_raw=0.0
      b0_raw=0.0
      b1_raw=0.0   
      b2_raw=K
    elif (type == "FIR_TEST"):
      a1_raw=0.0
      a2_raw=0.0
      b0_raw=K/2
      b1_raw=K/2  
      b2_raw=0.0
    elif (type == "LP"):
      a1_raw = (1-f0_bar)/(1+f0_bar)
      a2_raw = 0.0
      b0_raw = K*f0_bar/(1+f0_bar)
      b1_raw = K*f0_bar/(1+f0_bar)
      b2_raw = 0.0
    elif (type == "HP"):
      a1_raw = (1-f0_bar)/(1+f0_bar)
      a2_raw = 0.0
      b0_raw = K/(1+f0_bar)
      b1_raw = -K/(1+f0_bar)
      b2_raw = 0.0
    elif (type == "PI"):
      a1_raw = (1-f0_bar/g)/(1+f0_bar/g)
      a2_raw = 0.0
      b0_raw = K*(1+f0_bar)/(1+f0_bar/g)
      b1_raw = -K*(1-f0_bar)/(1+f0_bar/g)
      b2_raw = 0.0
    elif (type == "LP2"):
      a1_raw = 2*(1-f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
      a2_raw = -(1-f0_bar/Q+f0_bar**2)/(1+f0_bar/Q+f0_bar**2)
      b0_raw = K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
      b1_raw = 2*K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
      b2_raw = K*f0_bar**2/(1+f0_bar/Q+f0_bar**2)
    elif (type == "NOTCH"):
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
