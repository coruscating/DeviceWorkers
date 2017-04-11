import ok, threading, numpy, time
import os
import sys

CONFIG_FILE = "config.monocontroller"

class DeviceError(Exception):
	def __init__(self,value):
		self.value=value
	def __str__(self):
		return repr(self.value)

class MCxem:
    def __init__(self, passedmodule=0):

        self.lock = threading.Lock()
        xem = ok.FrontPanel()
        module_count = xem.GetDeviceCount()
        
        print "Found %d modules"%(module_count)
        if (module_count == 0): raise DeviceError("No XEMS found!")
        serial = [-1] * module_count
        for i in range(module_count):
            serial[i] = xem.GetDeviceListSerial(i)
            tmp = ok.FrontPanel()
            tmp.OpenBySerial(serial[i])
            print "Module %d: XEM3001v%s.%s, ID: %s, serial #: %s "%(i, tmp.GetDeviceMajorVersion(), tmp.GetDeviceMinorVersion(),tmp.GetDeviceID(),tmp.GetSerialNumber())
            tmp = None
            
        if (module_count > 1):
            if passedmodule != 0:
                module = passedmodule
            else:
                print "Choose a module: " 
                module = int(raw_input())
        else:
            module = 0

	print "module %d selected" %(module)            
        xem.OpenBySerial(serial[module])

        print "Loading PLL config"
        pll = ok.PLL22150()
        xem.GetEepromPLL22150Configuration(pll)
        pll.SetVCOParameters(200, 48)
        pll.SetDiv1(pll.DivSrc_VCO,4)
        pll.SetDiv2(pll.DivSrc_VCO,4)
        pll.SetOutputSource(0, pll.ClkSrc_Div1By2)
        for i in range(6):
            pll.SetOutputEnable(i, (i == 0))
            
        print "Ref is at %gMHz, PLL is at %gMHz"%(pll.GetReference(), pll.GetVCOFrequency())
        for i in range(6):
            if (pll.IsOutputEnabled(i)):
		print "Clock %d at %gMHz"%(i, pll.GetOutputFrequency(i))
		

        print "Programming PLL"
        #xem.SetEepromPLL22150Configuration(pll)
        xem.SetPLL22150Configuration(pll)
        
        print "Programming FPGA"
        prog = xem.ConfigureFPGA('monocontroller.bit')
        if(prog != 0):
            print 'failed! code:',prog
            raise 

        self.xem = xem
        self.name = xem.GetDeviceID()
        self.err1f = self.err3f = self.photodiode = self.trace = 0.0
	
	self.netport = 13004
        
        self.state = {'DAC0wave' : [0.0, 0.0, 200.0], 'DAC1wave' : [0.0, 0.0, 200.0], 'FREQ' : 0x07ae, 'DAC2wave': [0.0, 0.0, 200.0], 'DAC3wave': [0.0, 0.0, 200.0], 'DAC2wave' : [0.0, 0.0, 200.0], 'DAC3wave' : [0.0, 0.0, 200.0], 'DAC0lock' : [1, 0, 0.00001, 0.00001, 0.00001, 0.01, 0], 'DAC1lock' : [1, 0, 0.00001, 0.00001, 0.00001, 0.01, 0], 'DAC2lock' : [1, 0, 0.00001, 0.00001, 0.00001, 0.01, 0], 'DAC3lock' : [1, 0, 0.00001, 0.00001, 0.00001, 0.01, 0]}
        self.read_config()

        print "Initialization of hardware done"

    def write_to_xem(self, address, value):
        try:
            self.lock.acquire()
            self.xem.SetWireInValue(0x0, int(address))
            self.xem.SetWireInValue(0x1, int(value))
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn(0x40, 1)
        finally:
            self.lock.release()
        return

    def get_state(self, key):
        return self.state[key]

    def get_adc_value(self, adc, adctype, speed):
        try:
            self.lock.acquire()
	    if (adc == 0):
	        adc_num = 4
		wire1 = 0x25
		wire2 = 0x24
	    elif (adc == 1):
		adc_num = 5
		wire1 = 0x27
		wire2 = 0x26
	    elif(adc == 2):
		adc_num = 2
		wire1 = 0x21
		wire2 = 0x20
	    else:
		adc_num = 3
		wire1 = 0x23
		wire2 = 0x22

            # ask for data
            if (adctype == 'SLOW'):
                adc_cmd = speed<<3
                self.xem.SetWireInValue(0x00, adc_cmd, 0xFFFF)
                self.xem.UpdateWireIns()
		self.xem.ActivateTriggerIn(0x40, adc_num)
                self.xem.UpdateWireOuts()
            else:
		self.xem.ActivateTriggerIn(0x40, adc_num)
                self.xem.UpdateWireOuts()

            # rescale
            binval = self.xem.GetWireOutValue(wire1)*65536 + self.xem.GetWireOutValue(wire2)

            if (adctype == 'SLOW'):
                floval = 20.0*((binval^0x800000) - 2.**23)/(2.**24 - 1)
            elif (adctype == 'FAST'):
                floval = 32.768*((binval^0x20000) - 2.**17)/(2.**18 - 1)

        finally:
            self.lock.release()
            
        return floval

    def log_state(self):
        f = file('LOG-%s'%(self.name), 'a')
        t = time.time()
        logstr = "%.2f, %f, %f, %f, %f, %f\n"%(t, self.state['DAC0wave'], self.state['DAC1wave'], self.state['DAC2wave'], self.state['DAC3wave'])
        f.write(logstr)
        f.close

    def update_lockin_state(self):
        rawdata = '\x00'*4095
        try:
            self.lock.acquire()
            rv = self.xem.ReadFromPipeOut(0xA0, rawdata)
        finally:
            self.lock.release()

            
        # Sync check
        header = rawdata[0:16]
        if (header[0:2] != '>>' or header[-2:] != '<<'):
            print "Bad header! ", map(ord, header)
            return
	print header
        # Update internal state
        dac0_bin = ord(header[2])*256 + ord(header[3])
        dac1_bin = ord(header[4])*256 + ord(header[5])
        err1f_bin = ord(header[6])*(2**24) + ord(header[7])*(2**16) + ord(header[8])*255 + ord(header[9])
        err3f_bin = ord(header[10])*(2**24) + ord(header[11])*(2**16) + ord(header[12])*255 + ord(header[13])

        stream = rawdata[16:]
        samples = len(stream)/12
        # Parse
        data = numpy.zeros([samples, 5], 'Float32')
        for i in range(samples):
            row = stream[i*12 : (i+1)*12]
            if (row[10:12] != '##'):
                print "Corrupted stream! Row %d"%(i), map(ord, row)
                return
            data[i][0] = ord(row[0])*256 + ord(row[1])
            data[i][1] = bintofl(ord(row[2])*256 + ord(row[3]), 16)
            data[i][2] = bintofl(ord(row[4])*256 + ord(row[5]), 16)
            data[i][3] = bintofl(ord(row[6])*256 + ord(row[7]), 16)
            data[i][4] = bintofl(ord(row[8])*256 + ord(row[9]), 16)
  
        self.state['DAC0wave'] = round(100000.*bintofl(dac0_bin, 16))/10000
        self.state['DAC1wave'] = round(100000.*bintofl(dac1_bin, 16))/10000

        self.err1f = bintofl(err1f_bin, 32)
        self.err3f = bintofl(err3f_bin, 32)
        self.photodiode = numpy.average(data.take((2,), axis = 1))
        self.trace = data

        return
    
    def set_state(self, key, value):
        self.state[key] = value

        if (key == 'FREQ'):
            self.write_to_xem(0x1000, value)
            self.write_to_xem(0x1001, value)
            self.write_to_xem(0x1002, 3*value)
            
        elif (key == 'DAC0wave'):
            # Convert floats to integers
            int_max = flto16dac(value[0] + value[1])
            int_min = flto16dac(value[0] - value[1])
            int_step = int(8*((int_max - int_min) & 0xFFFF)/value[2])
            # Set the dacs
            self.write_to_xem(0xA000, 0xB0)
            self.write_to_xem(0xA001, int_max)
            self.write_to_xem(0xA002, int_min)
            self.write_to_xem(0xA003, int_step)

        elif (key == 'DAC1wave'):
            # Convert floats to integers
            int_max = flto16dac(value[0] + value[1])
            int_min = flto16dac(value[0] - value[1])
            int_step = int(8*((int_max - int_min) & 0xFFFF)/value[2])
            # Set the dacs
            self.write_to_xem(0xB000, 0xB0)
            self.write_to_xem(0xB001, int_max)
            self.write_to_xem(0xB002, int_min)
            self.write_to_xem(0xB003, int_step)

        elif (key == 'DAC2wave'):
            # Convert floats to integers
            int_max = flto16dac(value[0] + value[1])
            int_min = flto16dac(value[0] - value[1])
            int_step = int(8*((int_max - int_min) & 0xFFFF)/value[2])
            # Set the dacs
            self.write_to_xem(0x8000, 0xB0)
            self.write_to_xem(0x8001, int_max)
            self.write_to_xem(0x8002, int_min)
            self.write_to_xem(0x8003, int_step)
    
        elif (key == 'DAC3wave'):
            # Convert floats to integers
            int_max = flto16dac(value[0] + value[1])
            int_min = flto16dac(value[0] - value[1])
            int_step = int(8*((int_max - int_min) & 0xFFFF)/value[2])
            # Set the dacs
            self.write_to_xem(0x9000, 0xB0)
            self.write_to_xem(0x9001, int_max)
            self.write_to_xem(0x9002, int_min)
            self.write_to_xem(0x9003, int_step)
        #else:
        #    print "Bad setting on key %s to value %f!"%(key, value)

        return

    def read_config(self):
        keys = self.state.keys()
        for key in keys:
            value = read_from_config(self.name + ':' + key)
            if not value:
                continue
            floval = map(float, value.strip('[]').split(','))
            if len(floval) == 1: floval = floval[0]
            self.set_state(key, floval)            

        return

    def save_config(self):
        keys = self.state.keys()
        for key in keys:
            if (key == 'LOCK' or key == 'QUIET'): continue
            
            value =  self.state[key]
            save_to_config(self.name + ':' + key, value)
        return

    def get_name(self): return self.name
    def get_trace(self): return self.trace
    def reset(self): self.xem.ActivateTriggerIn(0x40, 0)

#####################################################
# Binary to float and back
######################################################
def bintofl(bitval, bits):
    topbit = 2**(bits - 1)
    bitval = 1.0 * (bitval^topbit)
    return (bitval - topbit)/(topbit - 1)

def flto16dac(fl):
    fl = min(10.0, max(-10.0, fl))
    bitval = (0x8000 ^ int((2**16 - 1)*(fl + 10.)/20.))
    return bitval

######################################################################
# save_to_config
#
# saves a value to a CONFIG_FILE file, under header root. It either
# updates the value, if such header is already present, or adds
# both the header and value
######################################################################
def save_to_config(root, value):
    if (os.access(CONFIG_FILE, os.F_OK) == 1):
        fd = file(CONFIG_FILE, "r+")
    else:
        fd = file(CONFIG_FILE, "w+")
    
    fd.seek(0,2)
    filesize = fd.tell()
    fd.seek(0,0)

    # Look for the header root
    start = 0
    for line in fd:
        if line.startswith(root):
            end = start + len(line)
            break
        start = start + len(line)
    else:
        start = filesize
        end = filesize

    fd.seek(end, 0)

    newtext = root + ":" + str(value) + '\n'
    # save all after the header root
    oldcontent = fd.read(filesize - end)
    fd.seek(start)
    # truncate the file at the header root
    fd.truncate(start)
    # Write new data, and rest of file
    # (effectively replacing old data with new)
    fd.write(newtext + oldcontent)
    fd.close()

################################################################
# read_from_config
#
# Reads the value saved under header root from CONFIG_FILE
################################################################
def read_from_config(root):
    if (os.access(CONFIG_FILE, os.F_OK) == 0): return
    fd = file(CONFIG_FILE, "r")
    for line in fd:
        if line.startswith(root + ':'):
            return line[len(root + ':'):-1]
    return
