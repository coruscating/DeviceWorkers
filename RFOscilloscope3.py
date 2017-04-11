import socket
import time
import sys
import os
import numpy as np
import string

#Define global variables
DEBUG = False
DEVICELOC = "/dev/twins/RFOscilliscope3"
PORT = 5025
print "hello"

def write_to_device(self,command):
        """
            Write command to device, command should be a non-terminated key word. e.g. "*IDN?"
        """
        os.write(self.dev, command)
def read_from_device(self,length=9000):
        """
            Reads message
        """
        try:
            rv = os.read(self.dev, length)
            return rv     
        except Exception as e:
            print "Could not read from device",e
            return -1
#DATa:SOUrce CH<4>
#DATa:SOUrce?