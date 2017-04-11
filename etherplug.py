import socket, time, threading, re, string


class etherplug:
    def __init__(self, execfunc, port, hostip = None):
        self.quitting = False
        self.hooks = {}
        self.hooknames = []
        self.execute = execfunc

        # start_network
    	try:
            self.netthread = threading.Thread()
            self.netthread.run = self.listen_to_network
            if not hostip:
                hostip = socket.gethostbyname(socket.gethostname())
            self.netsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.netsock.bind((hostip, port))
            self.netsock.settimeout(.5)
            self.netsock.listen(4)
	    
            self.netthread.start()
	except Exception, e:
	    print "Couldn't start listening on IP", hostip, "port", port, "-", e[1]

    def close(self):
        self.quitting = True
        print "Exiting network daemon"
        try:
            self.netthread.join(1.0)
        except:
            pass

    def register_hook(self, hookname, hookfunc):
        self.hooks[hookname] = hookfunc
        self.hooknames = self.hooks.keys()
        self.hooknames.sort(lambda x, y: len(y) - len(x))
        return

    #################################################################################
    # listen_to_network
    #
    # Executed by a separate thread. Listens for connections, if it's a valid
    # command, executes it
    #################################################################################
    def listen_to_network(self):
        while not self.quitting:
            addr = None
            try:
                connsock, addr = self.netsock.accept()
                cmd = connsock.recv(1024).strip()
                rv = 'N/A\n'
                try:
                    for name in self.hooknames:
                        if (name == cmd[0:len(name)]):
                            break
                    else:
                        rv = "Bad command #%s#\n"%(cmd)
                        raise Exception(rv)

                    f = self.hooks[name]
                    args = cmd[len(name):]
                    if args:
                        m = re.match(r'\s*(([0-9.eE-]+\s*)*)$', args)
                        if m:
                            args = map(float, m.group(1).split())
                        else:
                            args = map(lambda x: x.strip(), args.split())
    
                    rv = self.execute(f, args)
                    if not (rv.__class__ == 'str'.__class__):
                        rv = 'ACK\n'
                except Exception, e:
                    print e
                connsock.sendall(rv)
                connsock.shutdown(2)
                connsock.close()
            except:
                pass
        self.netsock.close()
        return
