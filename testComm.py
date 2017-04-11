import socket
import time
import sys
import os
import numpy as np
import string

DEBUG = False
DEVICELOC = "dyson"
PORT = 41282

class Comm:
    def __init__(self):  
        self.functiondict = {
            'test': self.test,
            'update': self.UPDATE
        }
            
    def test(self, value):
        print "test " + value

    def UPDATE(self):
        print "hi"
        pass
            
            
    def STOP(self):
        '''
            closes socket
        '''
        self.soc.close()

