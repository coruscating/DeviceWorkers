from andor import *
import time
import sys
import signal
<<<<<<< HEAD
import numpy as np
import matplotlib.pyplot as plt

=======
import threading
import numpy as np
>>>>>>> c78461766338b7ba583f57d2f308331ca73d25c9
#####################
# Initial settings  #
#####################

<<<<<<< HEAD
IMAGESAVEPATH = '/tmp/render.bmp'
PALETTEPATH = '/Dropbox/Quanta/Software/GitHub/Jarvis/www/images/camera/colors.pal'

#Tset = -70
EMCCDGain = 200
=======
Tset = -20
EMCCDGain = 0
>>>>>>> c78461766338b7ba583f57d2f308331ca73d25c9
PreAmpGain = 0

def signal_handler(signal, frame):
    print 'Shutting down the camera...'
    cam.ShutDown()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Initialising the Camera
<<<<<<< HEAD
cam = Andor()
cam.I2CReset()
cam.SetSingleScan()
cam.SetTriggerMode(7)
cam.SetShutter(1,1,0,0)
cam.SetPreAmpGain(PreAmpGain)
cam.SetEMCCDGain(EMCCDGain)
cam.SetExposureTime(0.1)
#cam.SetCoolerMode(1)

#cam.SetTemperature(Tset)
cam.CoolerOFF()
=======

#cam.SetCoolerMode(1)

#cam.SetTemperature(Tset)
#cam.CoolerON()
>>>>>>> c78461766338b7ba583f57d2f308331ca73d25c9

#while cam.GetTemperature() is not 'DRV_TEMP_STABILIZED':
#    print "Temperature is: %g [Set T: %g]" % (cam.temperature, Tset)
#    time.sleep(10)
IMGPATH='test.bmp'
PALPATH = '/media/twins_HDD/Dropbox (MIT)/Quanta/Twins/Control Software/Jarvis/www/images/camera/colors.pal'

def LoopUpdate():
    cam = Andor()
    #cam.GetCameraHandle(0)
    
    #cam.SetSingleScan()
    #cam.SetTriggerMode(7)
    #cam.SetShutter(1,1,0,0)
    cam.SetEMGainMode(2)
    cam.SetEMCCDGain(EMCCDGain)
    cam.SetExposureTime(0.1)
    param=[1,1000,200,700]
    cam.SetImage(1,1,*param)
    cam.GetEMGainRange()
    print 'EM gain range',cam.gainRange

    i = 0
    print "here"

    t0 = time.time()
    while True:

            i += 1
            #print cam.GetTemperature()
            #print cam.temperature
            print "Ready for Acquisition"
            cam.StartAcquisition()
            #data = []
            #cam.GetAcquiredData(data)
            
            cam.SaveAsBmpOnCamera(IMGPATH,PALPATH)

            data = []
            selectionData = []
            #cam.GetAcquiredData(data)
            #print len(data)
            #data = np.array(data).reshape((100,100))
            #print data
            #print cam.SaveAsBmpNormalised(IMGPATH)
            #print cam.SaveAsBmp("%03g.bmp" %i)
            #cam.SaveAsTxt("%03g.txt" %i)
            print 'Time for operation %f'%(time.time()-t0)
            break
    if running == False:
        cam.ShutDown()

running = True
t = threading.Thread(target = LoopUpdate)
t.start()

<<<<<<< HEAD
i = 0
'''
while True:
        i += 1
        #print cam.GetTemperature()
        #print cam.temperature
        print "Ready for Acquisition"
        cam.StartAcquisition()
        data = []
        #cam.GetAcquiredData(data)
        #cam.SaveAsBmpNormalised("%03g.bmp" %i)
        #cam.SaveAsBmp("%03g.bmp" %i)
        #cam.SaveAsTxt("%03g.txt" %i)
'''
print "ready for acquisition"

cam.I2CReset()
print "num of images acquired="
print cam.GetTotalNumberImagesAcquired()
cam.StartAcquisition()
print "num of images acquired="
print cam.GetTotalNumberImagesAcquired()
cam.GetStatus()
print "sleep"
time.sleep(1)
cam.I2CReset()
cam.GetStatus()
cam.GetSeriesProgress()
cam.GetStatus()
print "num of images acquired="
print cam.GetTotalNumberImagesAcquired()
cam.SaveAsBmpOnCamera(IMAGESAVEPATH, PALETTEPATH)
print "num of images acquired="
print cam.GetTotalNumberImagesAcquired()
data=cam.AcquireImage()
print "num of images acquired="
print cam.GetTotalNumberImagesAcquired()
plt.imshow(data)
plt.show()
=======
time.sleep(5)
running = False
>>>>>>> c78461766338b7ba583f57d2f308331ca73d25c9
