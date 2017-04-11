'''
    Helena Zhang: 2014-09-30
    Communication class for PhotonCounter using opal kelly's api (ok).
    
    Available methods:
    SampFreq - set sample frequency
    IntTime - set integration time
    DataState - turn on/off sending counts and FFT data for plotting
    Background - turn on/off background

 '''


import ok
import numpy, math
import socket, sys, threading 
from scipy import fftpack

DEBUG = False
DEVICELOC = "PhotonCounter"
PORT = 15973

FREQUENCY = 300.0   # MHz (220 is good for cavity cooling setup)
NMAX = 12
NBINS = 275
PAD = False

DEVICESERIAL = '12070002YC'

class Comm:
    def __init__(self):    
        try: 
            self.xem = ok.FrontPanel()

            self.xem.OpenBySerial(DEVICESERIAL)
            print "Found device called %s"%(self.xem.GetDeviceID())
               

            bitfile = './XEM6001_275bins.bit'
            DEVICE = 'XEM6001'


            print "Loading PLL config"
            pll = ok.PLL22150()
            self.xem.GetEepromPLL22150Configuration(pll)
            print "FREQUENCY=%d"%(FREQUENCY)
            pll.SetVCOParameters(int(FREQUENCY), 48)
            pll.SetDiv1(pll.DivSrc_VCO,4)
            pll.SetDiv2(pll.DivSrc_VCO,4)
            pll.SetOutputSource(0, pll.ClkSrc_Div1By2)
            pll.SetOutputSource(1, pll.ClkSrc_Div1By2)
            for i in range(6):
                pll.SetOutputEnable(i, (i == 0))
            print "Ref is at %gMHz, PLL is at %gMHz"%(pll.GetReference(), pll.GetVCOFrequency())
            for i in range(6):
                if (pll.IsOutputEnabled(i)):
                    print "Clock %d at %gMHz"%(i, pll.GetOutputFrequency(i))

            print "Programming PLL"
            self.xem.SetPLL22150Configuration(pll)

            print "Programming FPGA with:",bitfile
            if(self.xem.ConfigureFPGA(bitfile) < 0): 
                print "Programming failed. Quitting..."
                sys.exit()
         
        except Exception as e:
            print "initialization error" + str(e)
            sys.exit(1)
        
          
        self.internal_state = {}
        self.internal_state["Count"] = 0
        self.internal_state["IntTime"] = 250 # in ms
        self.internal_state["SampFreq"] = 300.0 # in MHz
        self.internal_state["MMAmp"] = 0.0
        self.internal_state["MMPhase"] = 0.0
        self.internal_state["Data"] = 0
        self.internal_state["DataState"] = False
        self.internal_state["Background"] = True
        self.internal_state["OverCount"] = False
        self.used_bins = NBINS
        self.clk_div = 1.0
        self.background_count = 0.
        
        
        # initialization 
        self.SampFreq(30.0)
        self.IntTime(250)

                   
    def UPDATE(self):
        time = self.internal_state["IntTime"]
        time = float(int(time*1000.*FREQUENCY/2.**17.)*(2.**17./1000./FREQUENCY))
        # New data?
        if (not self.check_for_data()): 
            if DEBUG: print(None,"No New Data")
            return True

        buf = self.fetch_data()
        # normalize wrt time
        data, full_flag = self.parse_data(buf)
        data = data*[1, 1000./time, 0, 0]
        fft,total_count = self.fft300(data[:,1])
        data[:,2] = fft[:,0]
        data[:,3] = fft[:,1]
        self.data = data

        # Figure out the frequency component
        freqin = self.internal_state["SampFreq"]
        binNum = self.get_bin_num(freqin)
        if (binNum < NBINS-1):
            self.internal_state["MMAmp"] = fft[int(binNum),0]+(fft[int(binNum+1),0]-fft[int(binNum),0])*(binNum-float(int(binNum)))

            self.internal_state["MMPhase"] = fft[int(binNum),1]+(fft[int(binNum+1),1]-fft[int(binNum),1])*(binNum-float(int(binNum)))

        else:
            self.internal_state["MMAmp"] = 0.0
            self.internal_state["MMPhase"] = 0.0    
        numpy.set_printoptions(threshold='nan')   
        if full_flag:
            self.internal_state['OverCount'] = True
        else: 
            self.internal_state['OverCount'] = False
        self.internal_state['Count'] = int(total_count)
        
        self.window_start = 0
        self.window_end = int(NBINS)        
        data[:,0] *= FREQUENCY/self.clk_div/NBINS
        data[0,2] = 0 # get rid of DC spikes 
        
        if self.internal_state["DataState"] == True:
            self.internal_state["Data"] = numpy.around(data[self.window_start:self.window_end,0:3],3).tolist()
        else:
            self.internal_state["Data"] = 0

        return self.internal_state

    def STOP(self):
        pass
        
    def DataState(self, state):
        if state=="ON":
            self.internal_state["DataState"] = True
        elif state=="OFF":
            self.internal_state["DataState"] = False

    def Background(self, state):
        if state=="ON":
            self.internal_state["Background"] = False
        if state=="OFF":
            self.background_count=0
            self.internal_state["Background"] = True

        
    def SampFreq(self, freq):
        freq=float(freq)
        self.internal_state["SampFreq"] = freq
        
        clk_div = float(int(FREQUENCY*NMAX/NBINS/freq))
        clk_div = min(max(clk_div,1.0),16.0)
        sync_div = float(int(freq*clk_div*NBINS/FREQUENCY))
        sync_div = min(max(sync_div,1.0),256.0)
        self.clk_div = clk_div            

        self.xem.SetWireInValue(0x00, int(clk_div-1.))
        self.xem.UpdateWireIns()
        self.xem.ActivateTriggerIn(0x40, 4)
        self.xem.SetWireInValue(0x00, int(sync_div-1.))
        self.xem.UpdateWireIns()
        self.xem.ActivateTriggerIn(0x40, 5)
        print("Frequency set to %g"%freq)          
        print("Clock Divisions: %g, Sync Divisions: %g."%(self.clk_div,sync_div))
        self.UPDATE()  
    
    def IntTime(self, inttime):
        inttime=float(inttime)
        self.internal_state["IntTime"] = inttime
        self.xem.SetWireInValue(0x00, int(inttime*1000.*FREQUENCY/2**17))
        self.xem.UpdateWireIns()
        self.xem.ActivateTriggerIn(0x40, 1)
        
    
    def check_for_data(self):
        buf = '\x00' * 2
        self.xem.SetWireInValue(0x01,0x01)
        self.xem.UpdateWireIns()
        rv = self.xem.ReadFromPipeOut(0xa0, buf)
        if rv < 0:
            print "Lost connection with counter card. Exiting now."
            sys.exit()
        if (buf != '\xED\xFE'):
            return False
        return True

    def fetch_data(self):
        buf = '\x00' * (2*int(NBINS)+2)
        rv = self.xem.ReadFromPipeOut(0xa0, buf)
        if rv < 0:
            print "Lost connection with counter card. Exiting now."
            sys.exit()
        if (buf[-2:] != '\xED\x0F'):
            print "Failed with",  map(ord, buf)
            return None
        buf = buf[0:2*int(NBINS)]
        self.xem.SetWireInValue(0x01,0x00)
        self.xem.UpdateWireIns()
        return buf              

    def parse_data(self, buf):
        full_flag = False
        data = numpy.zeros([int(NBINS),4], 'Float32') #includes zero-padding
        for sample in range(int(NBINS)):
            data[sample][0] = sample
            if (sample < int(NBINS)):
                data[sample][1] = (256.*ord(buf[2 * sample]) + ord(buf[2 * sample + 1]))

                if (data[sample][1] >= 2**10-1):
                    full_flag = True
        return data, full_flag


        
    def fft300(self, data):
        last_bin = 0
        total = 0.0
        for i in range(int(NBINS),0,-1):
            total += data[i-1]
            if(last_bin == 0 and data[i-1] != 0):
                last_bin = i
        if not self.internal_state["Background"]:
            self.background_count = total
            self.internal_state["Background"] = True

        fft = numpy.zeros([int(NBINS),2],'Float32')
        if(last_bin==0): return fft,0
        if(PAD): fftc = fftpack.fft(numpy.append(data[0:last_bin],\
            numpy.zeros([NBINS-last_bin])+self.background_count/float(last_bin)))
        else: fftc = fftpack.fft(data[0:last_bin])


        if(PAD): self.used_bins = NBINS
        else: self.used_bins = last_bin
        
        for i in range(int(self.used_bins)):
            fft[i,0] = abs(fftc[i])
            if(fft[i,0] == 0):
                fft[i,1] = 0
            else:
                fft[i,1] = math.atan2(fftc[i].imag,fftc[i].real)

        total -= self.background_count
        if(total !=0.): fft[:,0] /= abs(total)
        else: fft[:,0] *= 0.
        return fft, total
            
    def get_bin_num(self, freq):
        #print "used bins=" + str(self.used_bins)
        return self.used_bins*freq*self.clk_div/FREQUENCY    
     
    
