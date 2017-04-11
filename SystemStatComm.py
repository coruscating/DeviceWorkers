# gets CPU and memory usage

import subprocess

class Comm:
    def __init__(self):
        
        try:
            self.internal_state = {}
            self.internal_state["SysMemoryTotal"] = 0
            self.internal_state["SysMemoryUsed"] = 0
            self.UPDATE()

        except Exception as e:
            print 'Could not initialize SystemStatComm',e
            sys.exit(1)
        
 

            
    def UPDATE(self):
        '''
            Updates all internal state values 
            and returns them in a string array [".",".",...]
            
        '''
        try:

            # get memory usage
            output=subprocess.check_output("free | sed -n 2p", shell=True)
            output=output.split()
            
            self.internal_state["SysMemoryTotal"] = float(output[1])
            self.internal_state["SysMemoryUsed"] = float(output[2])
            
            
            output=subprocess.check_output("mpstat -P ALL 2 1 | tail -n +5 | sed '/^$/q'", shell=True)
            output=output.split("\n")
            
            for l in output:
                l2=l.split()
                if len(l2)>2:
                    self.internal_state["CPU" + l2[2]] = float(l2[3])

        except Exception as e:
            print 'Failed in Update: ',e
            pass

    def STOP(self):
        pass

