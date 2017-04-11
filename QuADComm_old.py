'''
    Jules Stuart: 2015-10-13
    Communication class for the QuAD boards using the OK library; giving credit where it is due - 
     I copied most of the form of the code below from Helena's PhotonCounterComm.py
    
    Available methods:
    setRegister - use the Register Assignment Module to set one of the internal registers
    configureDaughter - update the status of an individual daughter
    

 '''

import ok, struct, time, sys, math
import numpy as np
import matplotlib.pyplot as plt

# Local variables
FREQUENCY = 180.0  #MHz
DEVICESERIAL = "13450006RO"
# NOTE - with this change it should be able to load the bitfile from any directory
BITFILE = "./QuADController.bit"
SOURCE_LIST = {'ADC0':0x00, 'ADC1':0x01, 'ADC2':0x02, 'ADC3':0x03, 'ADC4':0x04, 'ADC5':0x05, \
               'ADC6':0x06, 'ADC7':0x07, 'IIR0':0x10, 'IIR1':0x11, 'IIR2':0x12, 'IIR3':0x13, \
               'IIR4':0x14, 'IIR5':0x15}


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
    self.internal_state["QuADDaughterType"] = ["DAC", "DAC", "DAC", "DAC", "DAC", "DAC", "DAC", "DAC"]
    self.internal_state["QuADDaughterOutputMode"] = ["Single", "Single", "Single", "Single", "Single", "Single", "Single", "Single"]
    self.internal_state["QuADDaughterRangeMode"] = ["Positive", "Positive", "Positive", "Positive", "Positive", "Positive", "Positive", "Positive"]
    self.internal_state["QuADDaughterSource"] = ["ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0"]
    self.internal_state['QuADDaughterPositiveRail'] = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]
    self.internal_state['QuADDaughterNegativeRail'] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    self.internal_state["QuADDaughterVoltage"] = [0,0,0,0,0,0,0,0]
    self.internal_state["QuADFilterType"] = ["P", "P", "P", "P", "P", "P"]
    self.internal_state["QuADFilterSource"] = ["ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0", "ADC0"]
    self.internal_state["QuADFilterCutoff"] = [20000.0, 20000.0, 20000.0, 20000.0, 20000.0, 20000.0]
    self.internal_state["QuADFilterGain"] = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    self.internal_state["QuADFilterOffset"] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    # Private internal states for distinguishing ADC voltages from DAC voltages
    self.internal_state["DACVoltage"] = [0,0,0,0,0,0,0,0]
    self.internal_state["ADCVoltage"] = [0,0,0,0,0,0,0,0]
    # Private internal states for controlling ouptut statuses
    #self.internal_state["RBUF"] = 0xFF #state of the ouput amplifier; controls the output rails
    #self.internal_state["2CM
    
    # Now run initialization methods to reach a common start state
    print "Engaging default state..."
    # All daughters initialize as DACs
    self.setRegister(0x0000, 0x00)
    # All daughters initialize into non-feedback mode
    self.setRegister(0x0002, 0x00)
    # Update DAC source registers and set each into binary offset mode; RBUF configured for unity
    for i in range(8):
      self.setRegister(0x0080 + i, SOURCE_LIST["ADC0"])
      self.setRegister(0x0010 + 2*i, 0x0012)
      self.setRegister(0x0011 + 2*i, 0x0020)
      self.xem.ActivateTriggerIn(0x40, i)
      print "Setting DAC at position " + str(i) + " to binary offset mode"
      # NOTE - the following zeroing is not necessary if you start in positive only mode
      # Write 0.0 volts to each of the DACs
      #code = int((10.0)/20.0 * 2**20)
      #code = code | 0x100000
      #bottomBits = code & 0x00FFFF
      #topBits = (code & 0xFF0000) >> 16
      self.setRegister(0x0010 + 2*i, 0x0000)
      self.setRegister(0x0011 + 2*i, 0x0010)
      self.xem.ActivateTriggerIn(0x40, i)
      print "Writing 0.0 to DAC at position " + str(i)
    # Set all of the feedback modes to positive only
    self.setRegister(0x0004, 0x00)
    # Set all of the filters to the on state
    # NOTE - I removed the control for the filter on/off; need to check this more thoroughly
    #self.setRegister(0x0003, 0x003F)
    # Update each of the filters to the internal state configuration
    for i in range(5):
      self.configureFilter(i, self.internal_state["QuADFilterType"][i], \
        self.internal_state["QuADFilterSource"][i], self.internal_state["QuADFilterCutoff"][i], \
        self.internal_state["QuADFilterGain"][i], self.internal_state["QuADFilterOffset"][i])
    print "Default state set.  Welcome to the QuADCon!"
  
  def UPDATE(self):
    for i in range(len(self.internal_state['QuADDaughterType'])):
      if (self.internal_state['QuADDaughterType'][i] == 'ADC'):
        self.getSingleADCValue(i)
        self.internal_state['QuADDaughterVoltage'][i] = self.internal_state['ADCVoltage'][i]
      else:
        self.internal_state['QuADDaughterVoltage'][i] = self.internal_state['DACVoltage'][i]
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
    # Set the register address and value
    self.xem.SetWireInValue(0x00, address)
    self.xem.SetWireInValue(0x01, value)
    self.xem.UpdateWireIns()
    # Trigger the register addressing module
    self.xem.ActivateTriggerIn(0x40, 9)
  
  def configureDaughter(self, index, type, source, output_mode, range_mode, positive_rail, negative_rail):
    # index - 0 to 7 integer position of the daughter
    # type - string value ("DAC" or "ADC") indicating the type of daughter
    # source - hex code for the source of the DAC output
    # output_mode - string value ("Feedback" or "Single") indicating the write source
    # range_mode - string value ("Positive" or "Dual") indicating the output range
    # positive_rail - float value for the maximum output voltage
    # negative_rail - float value for the minimum output voltage
    index = int(index)
    # Update the internal state
    self.internal_state['QuADDaughterType'][index] = type
    self.internal_state['QuADDaughterSource'][index] = source
    self.internal_state['QuADDaughterOutputMode'][index] = output_mode
    self.internal_state['QuADDaughterRangeMode'][index] = range_mode
    self.internal_state['QuADDaughterPositiveRail'][index] = float(positive_rail)
    self.internal_state['QuADDaughterNegativeRail'][index] = float(negative_rail)
    # Calculate the DAC/ADC statuses to be written based on all of the daughters
    daughterStatus = 0
    for i in range(len(self.internal_state['QuADDaughterType'])):
      if (self.internal_state['QuADDaughterType'][i]=="ADC"):
        daughterStatus += (1 << i)
    # Calculate the feedback statuses to be written based on the status of all DACs
    feedbackStatus = 0
    tempFeedbackStatus = 0   #ugly, ugly, ugly
    for i in range(len(self.internal_state['QuADDaughterOutputMode'])):
      if (self.internal_state['QuADDaughterOutputMode'][i]=="Feedback"):
        feedbackStatus += (1 << i)
        if (i != index):
          tempFeedbackStatus += (1 << i)
    # Calculate the range statuses to be written based on the status of all DACs
    rangeStatus = 0
    for i in range(len(self.internal_state['QuADDaughterRangeMode'])):
      if (self.internal_state['QuADDaughterRangeMode'][i]=="Dual"):
        rangeStatus += (1 << i)
    # Determine the value of the RBUF register
    if (self.internal_state['QuADDaughterRangeMode'][index] == "Positive"):
      rbuf = 1
    else:
      rbuf = 0
    # Calculate code for positive rail; assumed to be > 0
    max_output = int((self.internal_state['QuADDaughterPositiveRail'][index])/20.0 * 2**16)
    # Calculate code for negative rail; may not be < 0
    min_output = int((self.internal_state['QuADDaughterNegativeRail'][index])/20.0 * 2**16)
    if (self.internal_state['QuADDaughterNegativeRail'][index] < 0):
      min_output = (1<<16) + min_output
    # Update the ADC status register
    self.setRegister(0x0000, daughterStatus)
    # Update the DAC source register
    self.setRegister(0x0080 + index, SOURCE_LIST[source])
    # Update the rail registers
    self.setRegister(0x0090 + 2*index, max_output)
    self.setRegister(0x0091 + 2*index, min_output)
    # Update the range status register
    self.setRegister(0x0004, rangeStatus)
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
  
  # Function to write a single voltage value to a specified DAC
  def writeSingleDACVoltage(self, index, voltage):
    # index - 0 to 7 integer position of the DAC
    # voltage - -10 to 10 float voltage to be written
    voltage = float(voltage)
    index = int(index)
    # Convert the voltage to a DAC code with write prefix
    # NOTE - need to add a flag here to check which range mode the DAC is in
    if (self.internal_state['QuADDaughterRangeMode'][index] == "Positive"):
      if (voltage < 0.0):
        voltage = 0.0
        print "Negative voltages not allowed in this mode!"
      code = int((voltage)/10.0 * 2**20)
    else:
      code = int((voltage + 10.0)/20.0 * 2**20)  #presumes the DAC is in binary offset and dual rail mode
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
    if (self.internal_state['QuADDaughterRangeMode'][index] == "Positive"):
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
    self.xem.ActivateTriggerIn(0x40, 10)
    self.xem.UpdateWireOuts()
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
  
  def configureFilter(self, index, type, source, cutoff, gain, offset):
    # Update the internal state
    cutoff = float(cutoff)
    gain = float(gain)
    offset = float(offset)
    index = int(index)
    self.internal_state['QuADFilterType'][index] = type
    self.internal_state['QuADFilterSource'][index] = source
    self.internal_state['QuADFilterCutoff'][index] = cutoff
    self.internal_state['QuADFilterGain'][index] = gain
    self.internal_state['QuADFilterOffset'][index] = offset
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