import pylibftdi as p    
import time
import binascii
import struct 
import array
import serial
import sys
import traceback
import inspect

# PRM1-Z8
# 1919.64 EncCnt per mm
# scaling 42941.66 mm/s
# POS_APT = EncCnt x Pos

MGMSG_MOD_IDENTIFY = 0x0223
MGMSG_HW_RESPONSE = 0x0080

MGMSG_HW_REQ_INFO = 0x0005
MGMSG_HW_GET_INFO = 0x0006

MGMSG_MOT_ACK_DCSTATUSUPDATE = 0x0492

# Motor Commands
MGMSG_MOT_SET_PZSTAGEPARAMDEFAULTS = 0x0686

MGMSG_MOT_MOVE_HOME = 0x0443
MGMSG_MOT_MOVE_HOMED = 0x0444
MGMSG_MOT_MOVE_ABSOLUTE = 0x0453
MGMSG_MOT_MOVE_COMPLETED = 0x0464

MGMSG_MOT_SET_HOMEPARAMS = 0x0440
MGMSG_MOT_REQ_HOMEPARAMS = 0x0441
MGMSG_MOT_GET_HOMEPARAMS = 0x0442

MGMSG_MOT_REQ_POSCOUNTER = 0x0411
MGMSG_MOT_GET_POSCOUNTER = 0x0412

MGMSG_MOT_REQ_DCSTATUSUPDATE = 0x0490
MGMSG_MOT_GET_DCSTATUSUPDATE = 0x0491

MGMSG_MOT_SET_VELPARAMS = 0x413
MGMSG_MOT_REQ_VELPARAMS = 0x414
MGMSG_MOT_GET_VELPARAMS = 0x415

MGMSG_MOT_SUSPEND_ENDOFMOVEMSGS = 0x046B
MGMSG_MOT_RESUME_ENDOFMOVEMSGS = 0x046C

MGMSG_MOT_MOVE_STOP = 0x0465
MGMSG_MOT_MOVE_STOPPED = 0x0466


p.USB_PID_LIST.append(0xfaf0)
p.USB_VID_LIST.append(0x0403)




# get info
#self.dev.write('\x05\x00\x00\x00\x21\x01')
#time.sleep(1)
#res=self.dev.read(90)
#print struct.unpack(90*"B",res)

#
# get status
#
#self.dev.write('\x80\x04\x01\x00\x21\x01')
#reslen=20
#res=self.dev.read(reslen)
#print struct.unpack(reslen*"B",res)
#for i in struct.unpack(reslen*"B",res):
#   print hex(i)

class Comm:
    def __init__(self):
        try:
            serial_settings = {"port":"/dev/ttyUSB5","baudrate":115200, "timeout":None, "rtscts": True}
            self.dev=serial.Serial(**serial_settings)
            self.dev.flush()

            # blink Active LED
            self.dev.write('\x23\x02\x00\x00\x21\x01')
            self.internal_state={}
            self.internal_state['Position']=0
            self.Req_DCStatusUpdate()
            self.Set_MoveRelParams()
            self.Req_MoveRelParams()
            sys.exit()
            #Req_MoveAbsParams()
            #Move_Relative()
        except Exception as e:
            print str(e)
            print traceback.format_exc()
    def UPDATE(self):
        pass
    def STOP(self):
        sys.exit()
    def pack(self, verbose=True):
        """
        Returns a byte array representing this message packed in little endian
        """
        if self.data:
          """
          <: little endian
          H: 2 bytes for message ID
          H: 2 bytes for data length
          B: unsigned char for dest
          B: unsigned char for src
          %dB: %d bytes of data
          """
          datalen = len(self.data)
          if type(self.data) == str:
            datalist = list(self.data)
          else:
            datalist = self.data

          ret = st.pack(  '<HHBB%dB'%(datalen),
                          self.messageID,
                          datalen,
                          self.dest|0x80,
                          self.src,
                          *datalist)
        else:
          """
          <: little endian
          H: 2 bytes for message ID
          B: unsigned char for param1
          B: unsigned char for param2
          B: unsigned char for dest
          B: unsigned char for src
          """
          ret = st.pack(  '<HBBBB',
                          self.messageID,
                          self.param1,
                          self.param2,
                          self.dest,
                          self.src)
        if verbose:
          print(bytes(self),'=',[hex(ord(x)) for x in ret])

        return ret

    def Req_DCStatusUpdate(self):
        self.dev.write('\x90\x04\x01\x00\x21\x01')
        time.sleep(1)
        res=self.dev.read(20)
        self.printhex(res,20)

    def printhex(self,res,len):
        arr=[]
        for i in struct.unpack("<%dB"%(len),res):
            arr.append(hex(i))
        print "Output from %s: "%(inspect.stack()[1][3])
        print arr


    def Req_MoveAbsParams(self):
        try:
            self.dev.write('\x51\x04\x01\x00\x21\x01')
            time.sleep(1)
            res=self.dev.read(12)
            self.printhex(res,12)
        except Exception as e:
            print str(e)
            print traceback.format_exc()

    def Req_MoveRelParams(self):
        try:
            self.dev.write('\x46\x04\x01\x00\x21\x01')
            time.sleep(1)
            res=self.dev.read(12)
            self.printhex(res,12)
        except Exception as e:
            print str(e)
            print traceback.format_exc()

    def Set_MoveAbsParams(self):
        self.dev.write('\x50\x04\x06\x00\x21\x01\x01\x00\x00\x00\x00\x00')
        time.sleep(1)

    def Set_MoveRelParams(self):
        self.dev.write('\x45\x04\x06\x00\x21\x01\x01\x00x\x00\x00\x00')
        time.sleep(1)    

    def Move_Relative(self):
        try:
            self.dev.write('\x48\x04\x06\x00\x21\x01')
            reslen=20
            res=self.dev.read(reslen)
            self.printhex(res,reslen)
        except Exception as e:
            print str(e)
            print traceback.format_exc()

    def Move_Stop(self):
        self.dev.write('\x65\x04\x01\x01\x21\x01')
        time.sleep(1)
        reslen=20
        res=self.dev.read(reslen)
        self.printhex(res,reslen)

    def Move_Absolute(self):
        try:
            self.dev.write('\x53\x04\x01\x00\x21\x01')
            time.sleep(1)
            reslen=20
            res=self.dev.read(reslen)
            self.printhex(res,reslen)
        except Exception as e:
            print str(e)
            print traceback.format_exc()

