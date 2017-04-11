DeviceWorkers
=============

Created by: Michael Gutierrez 2014-08-11

These are the device specific portion of MTServer. The intention is to abstract
the device specific communication method to a universal socket based
communication method. 

As of 2014-08-11:
	There are several requirements for this file to be compatible with
	MTServer/Worker

	1. There needs to be a dictionary containing all device parameters 
	that you'll want to set / read. This needs to be stored in 
	self.internal_state

	2. There are two requried methods in the Comm class
	STOP - Which should contain whatever is necessary to safely close and stop
		the device
	UPDATE - Which should update self.internal_state

	While not necessary we should stick to the convention that ALL methods
	which you intend to be called from clients be in ALL caps. e.g. STOP().
	All methods which are only intended to be used internally or for debugging
	be in all lower case, e.g. get_device_name()

Update 2014-08-13:

	Additional Method necessary is now: METHODSAVAILABLE, which should return
	a list of all available methods to the server

Auxiliary Files
---------------

**MCxem.py**: XEM communication library for LaserController
**monocontroller.bit**: FPGA programming file for LaserController
**XEM6001_275bins.bit**: FPGA programming file for PhotonCounter
