import traceback
import xmlrpclib
import time
import sys

server_url = 'http://comb:system@quanta-comb.mit.edu:8123/RPC2';

class Comm:
    def __init__(self):  
        try:
            
            self.server = xmlrpclib.ServerProxy(server_url);

            self.internal_state = {}
            self.internal_state["RepRateCounter"] = 0
            self.internal_state["OffsetCounter"] = 0
            self.internal_state["Beat1SqueezerX"] = 0
            self.internal_state["Beat1SqueezerY"] = 0
            self.internal_state["Beat1SqueezerZ"] = 0
            self.internal_state["Beat1StageX"] = 0
            self.internal_state["Beat1StageY"] = 0
            self.internal_state["Beat1StageZ"] = 0
            self.internal_state["OffsetLockStat"] = 0 
            self.internal_state["OffsetLockMon"] = 0
            self.internal_state["RepRateLockStat"] = 0 #lb1.mon, lb1.status not working
            self.internal_state["RepRateLockMon"] = 0
            self.internal_state["PLOStatus"] = 0
            self.internal_state["SynthesizerFreq"] = 0
            print "Connected to " + self.server.hello()
            
        except Exception as e:
            print 'Failed to connect to comb: ',e
            sys.exit(1)

    def UPDATE(self):
        
        try:
            self.server.param.set("BeatCW1.SqueezerXYZ.Y", 7.2)
            self.internal_state["SynthesizerFreq"]=self.server.comb.reprate.synth.getFreq()
            data=self.server.data.query(-1.000) # only get the most recent query

            if (type(data)!=type('str')):
                timestamps=data.keys()
                ts=timestamps[0]
                
                self.internal_state["Beat1SqueezerX"]=data[ts]['beat1.squeezer.x']
                self.internal_state["Beat1SqueezerY"]=data[ts]['beat1.squeezer.y'] 
                self.internal_state["Beat1SqueezerZ"]=data[ts]['beat1.squeezer.z']
                self.internal_state["Beat1StageX"]=data[ts]['beat1.stage.x']
                self.internal_state["Beat1StageY"]=data[ts]['beat1.stage.y']
                self.internal_state["Beat1StageZ"]=data[ts]['beat1.stage.z']
                self.internal_state["OffsetLockStat"]=data[ts]['lb2.status']
                self.internal_state["OffsetLockMon"]=data[ts]['lb2.mon']
                
        except Exception as e:
            print "Error", e
            print traceback.format_exc()

    def Beat1SqueezerX(self, value):
        self.server.param.set("BeatCW1.SqueezerAMP.X", float(value))
    def Beat1SqueezerY(self, value):
        self.server.param.set("BeatCW1.SqueezerAMP.Y", float(value))
    def Beat1SqueezerZ(self, value):
        self.server.param.set("BeatCW1.SqueezerAMP.Z", float(value))

    def Beat1StageX(self, value):
        self.server.param.set("BeatCW1.SqueezerXYZ.X", float(value))
    def Beat1StageY(self, value):
        self.server.param.set("BeatCW1.SqueezerXYZ.Y", float(value))
    def Beat1StageZ(self, value):
        self.server.param.set("BeatCW1.SqueezerXYZ.Z", float(value))


    def STOP(self):
        pass
    
            
