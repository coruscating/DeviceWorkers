from __future__ import division # non-truncating division, to be safe
import csv
import numpy as np
from scipy.misc import derivative
from scipy.optimize import *
import zachmath
import scipy as sp
class IonTrap:
    def __init__(self, v_rf, m_over_Ze, omega_rf, dc_voltages = None, electrode_def_file = None):
        self.v_rf = v_rf
        self.omega_rf = omega_rf
        self.m_over_Ze = m_over_Ze
        self.dc_voltages = dc_voltages
        self.center = None
        self.escape = None
        self.depth = None
        self.rf_channels = []
        self.dc_channels = []
        self.trap_parameters = {} # dict. set cmds/values from electrode file
        self.electrodes = {} # dict. key=channel label, value=Electrode array
        # example:  {'v1':[Electrode, Electrode], 'v2':[Electrode], ...}
        
        if electrode_def_file is not None:
            self.load(electrode_def_file)
    
    def add_electrode(self, channel, e, is_rf = False):
        if is_rf and not channel in self.rf_channels:
            self.rf_channels.append(channel)
        elif not channel in self.dc_channels:
            self.dc_channels.append(channel)
        
        if channel in self.electrodes:
            self.electrodes[channel].append(e)
        else:
            self.electrodes[channel] = [e]
	
    def load(self, electrode_def_file):
        edef_file = csv.reader(open(electrode_def_file, "rb"), 
							     delimiter='\t')

        params = {}
        for row in edef_file:
            if len(row) > 0:
                etype = row[0]
                if etype.lower() == 'set':
                    params[row[1]] = eval(row[2])
                elif etype.lower() == 'rf' or etype.lower() == 'dc':
                    channel = row[1]
                    x1 = self._interpret_def_file_entry(row[2], params)
                    z1 = self._interpret_def_file_entry(row[3], params)
                    x2 = self._interpret_def_file_entry(row[4], params)
                    z2 = self._interpret_def_file_entry(row[5], params)
                    e = Electrode(x1, z1, x2, z2)
                    self.add_electrode(channel, e, etype.lower() == 'rf')
        
        self.trap_parameters = params
        
    def find_center(self, guess=[50e-6, 1500e-6]):
        if self.center is None:
            # x0 = 1e6 * np.array(guess)
            #  print 'x0 =',x0
            #  result = fmin_slsqp(lambda x:self.pseudopotential(x[0]/1e6,x[1]/1e6,0), 
            #                      guess, disp = 3)
            #  print 'result =',result
            #  self.center = (result[0]/1e6, result[1]/1e6)
            #  print 'cent =',self.center
            (a,b,c) = (self.trap_parameters['a'], self.trap_parameters['b'], self.trap_parameters['c'])
            x0 = a * c / (b + c)
            y0 = np.sqrt(a * b * c * (a + b + c)) / (b + c)
            self.center = (x0, y0)
        return self.center

    def find_escape(self):
        if self.escape is None:
            center = [1e6*x for x in self.find_center()]
            def ineq_constraint(y):
                f = lambda y2:self.pseudopotential(center[0]/1e6, y2, 0)
                dy = derivative(f, y/1e6, n = 2, order = 5, dx = 1e-5)
                return -1e15*dy
            result = fmin_slsqp(lambda y2:-self.pseudopotential(center[0]/1e6,y2/1e6,0), 
                                [center[1] + 1], 
                                ieqcons = [ineq_constraint, lambda y:y-center[1]],
                                disp = 0)
            self.escape = (center[0]/1e6, result[0]/1e6)
            
        return self.escape
        
    def find_depth(self):
        if self.depth is None:
            esc = self.find_escape()
            self.depth = self.pseudopotential_fn()(esc[0], esc[1], 0)
        
        return self.depth
        
    # def find_escape(self):
    #     x0 = self.find_center()
    #     
    #     def dphix(x,y,z,n,dx=1e-10):
    #         f = lambda x2:self.pseudopotential(x2,y,z)
    #         return derivative(f, x, n = n, dx = dx)
    #     def dphiy(x,y,z,n,dy=1e-10):
    #         f = lambda y2:self.pseudopotential(x,y2,z)
    #         return derivative(f, y, n = n, dx = dy)
    #     def eq_constraint(r):
    #         x = r[0]
    #         y = r[1]
    #         dx = dphix(x,y,0,1)
    #         dy = dphiy(x,y,0,1)
    #         return np.array([dx, dy])
    #     def ineq_constraint(r):
    #         x = r[0]
    #         y = r[1]
    #         dx2 = dphix(x,y,0,2)
    #         dy2 = dphiy(x,y,0,2)
    #         return np.array([max(dx2, dy2), -min(dx2, dy2)])
            
        print fmin_slsqp(lambda r:np.sum(np.square(r - x0)), x0, f_eqcons = eq_constraint, f_ieqcons = ineq_constraint)
    
    @classmethod
    def _interpret_def_file_entry(cls, entry, params = {}):
	    if entry.lower() == 'inf':
	        return np.infty
	    elif entry.lower() == '-inf':
	        return -np.infty
	    else:
	        return eval(entry, params)
    
    def pseudopotential(self, x, y, z):
        return self.pseudopotential_fn()(x,y,z)
    
    #potential energy when considering only the secular motion of the ion
    def pseudopotential_fn(self): 
        applied_voltages = {c:self.v_rf for c in self.rf_channels}
        d = 4 * self.m_over_Ze * self.omega_rf**2
        return lambda x,y,z:np.sum(np.square(self.grad_potential_fn(applied_voltages)(x,y,z))) / d
    #static potential
    def potential_fn(self, applied_voltages):
        return lambda x,y,z: np.sum([applied_voltages[c]*np.sum([e.potential(x,y,z) for e in self.electrodes[c]]) for c in applied_voltages])

    #gradient of potential (zero at the point where ion is trapped)
    def grad_potential_fn(self, applied_voltages):
        def result_fn(x,y,z):
            r = np.array([0,0,0])
            for channel in applied_voltages.iterkeys():
                for electrode in self.electrodes[channel]:
                    r = r + applied_voltages[channel] * electrode.grad_potential(x,y,z)
            return r
        return result_fn
        
    def hess_potential_fn(self, applied_voltages, i, j):
        def result_fn(x,y,z):
            r = 0
            for channel in applied_voltages.iterkeys():
                for electrode in self.electrodes[channel]:
                    r = r + applied_voltages[channel] * electrode.hess_potential(x,y,z,i,j)
            return r
        return result_fn
        
    def hess_potential_fn_ij(self, i, j):
        return lambda applied_voltages:self.hess_potential_fn(applied_voltages, i, j)
        
    def hess_potential(self, applied_voltages):
        def result_fn(x,y,z):
            diagn = [self.hess_potential_fn(applied_voltages, i, i)(x,y,z) for i in xrange(3)]
            mixed = [self.hess_potential_fn(applied_voltages, i[0], i[1])(x,y,z) for i in [(0,1),(0,2),(1,2)]]
            m1 = np.diag(diagn)
            m2 = np.array([[0, mixed[0], mixed[1]],[0,0,mixed[2]],[0,0,0]])
            return m1 + m2 + m2.transpose()
        return result_fn

    #A and Q are unitless measures of the curvature of the potential
    def find_Q(self):
        (x0, y0) = self.find_center()
        rf_unit = {c:self.v_rf for c in self.rf_channels}

        rf_potential = self.potential_fn(rf_unit)
        ddphi_rf = self.hess_potential(rf_unit)(x0,y0,0)
 
        Q = 2 / (self.m_over_Ze * self.omega_rf**2) * ddphi_rf
        return Q
    
    def find_A(self, dc_voltages):
        (x0, y0) = self.find_center()
        dc_potential = self.potential_fn(dc_voltages)
        ddphi_dc = self.hess_potential(dc_voltages)(x0,y0,0)
        A = 4 / (self.m_over_Ze * self.omega_rf**2) * ddphi_dc
        return A
    
    def dc_electrodes(self):
        return {c:self.electrodes[c] for c in self.dc_channels}
    
    def rf_electrodes(self):
        return {c:self.electrodes[c] for c in self.rf_channels}
        
    def find_dc_voltages(self, constraints, location = 0): #constraints evaluated at the trap center
        try:
            (x0, y0, z0) = location
        except TypeError:
            (x0, y0) = self.find_center()
            z0 = location
        
        def flatten_maybeiterable(a):
            r = []
            for e in a:
                try:
                    for e2 in e:
                        r.append(e2)
                except TypeError:
                    r.append(e)
            return r
        
        dc_electrodes = self.dc_electrodes()
        cfs = constraints.keys()
        cvs = flatten_maybeiterable([constraints[cf] for cf in cfs])
        
        ne = len(dc_electrodes)
        n = ne + len(cvs)
        
        ces = []
        for dc_channel in dc_electrodes:
            channel_unit = {dc_channel: 1}
            ce = [cf(channel_unit)(x0,y0,z0) for cf in cfs]
            ces.append(flatten_maybeiterable(ce))
        
        mi = np.array([[2 if (i == j and i < ne) else 0 for j in xrange(n)] for i in xrange(n)])
        mc = np.array([[ces[i][j-ne] if (i < ne and j >= ne) else 0 for j in xrange(n)] for i in xrange(n)])
        m = mi + mc + mc.transpose()
        b = [cvs[i - ne] if i >= ne else 0 for i in xrange(n)]
        mi = np.linalg.inv(m)
        x = np.dot(mi, b)
        return dict(zip(dc_electrodes.keys(), x[:ne]))
    
    
    def find_omega_secular(self, dc_voltages, m_over_Ze, omega_rf):
        (x0, y0) = self.find_center()
        z0 = 0.0
        dx = 1e-7
        dy = 1e-7
        dz = 1e-7
        psi = self.pseudopotential
        #Total Potential Function
        V = lambda x,y,z:psi(x,y,z) + self.potential_fn(dc_voltages)(x,y,z)
        
        o2 = (1/m_over_Ze) * np.array(zachmath.secondderiv_matrix(V, x0, y0, z0, dx, dy, dz))
        #Calculating the eigenvalues of the o2 matrix which corresponds to the secular frequencies^2
        (freqs_squared, trap_axes) = np.linalg.eig(o2)
        talist = trap_axes.tolist()
        tadict = {}
        freqlist= (freqs_squared**.5).tolist()
        freqdict = {}
        j = 0
        print np.linalg.eig(o2)
        print talist
        for i in talist:
            index = sp.argmax(np.absolute(i))
            if index == 2:
                tadict['z-axis'] = i
                freqdict['omega_z']= freqlist[j]
            elif index == 1:
                tadict['y-axis'] = i
                freqdict['omega_y']= freqlist[j]
            elif index == 0:
                tadict['x-axis'] = i
                freqdict['omega_x']= freqlist[j]
            j += 1
##        tadict['z-axis'] = talist[2]
##        tadict['y-axis'] = talist[1]
##        tadict['x-axis'] = talist[0]

        
##        freqdict['omega_z'] = freqlist[2]
##        freqdict['omega_y'] = freqlist[1]
##        freqdict['omega_x'] = freqlist[0]
        print freqdict, tadict
        return freqdict , tadict
        
        

class Electrode:
    def __init__(self, x1, z1, x2, z2):
        self.x1 = x1
        self.z1 = z1
        self.x2 = x2
        self.z2 = z2
        #print (x1, z1, x2, z2)
    
    def potential(self, x, y, z):
        return (self._potential_corner(x, y, z, self.x1, self.z1) - self._potential_corner(x, y, z, self.x1, self.z2)
                - self._potential_corner(x, y, z, self.x2, self.z1) + self._potential_corner(x, y, z, self.x2, self.z2))
    
    def grad_potential(self, x, y, z):
        return (self._grad_potential_corner(x, y, z, self.x1, self.z1) - self._grad_potential_corner(x, y, z, self.x1, self.z2)
                - self._grad_potential_corner(x, y, z, self.x2, self.z1) + self._grad_potential_corner(x, y, z, self.x2, self.z2))
    
    def hess_potential(self, x, y, z, i, j):
        return (self._hess_potential_corner(x, y, z, self.x1, self.z1, i, j) - self._hess_potential_corner(x, y, z, self.x1, self.z2, i, j)
                - self._hess_potential_corner(x, y, z, self.x2, self.z1, i, j) + self._hess_potential_corner(x, y, z, self.x2, self.z2, i, j))
    
    def coordinates(self):
        return [self.x1, self.z1, self.x2, self.z2]

    @classmethod
    def _potential_corner(cls, x, y, z, xe, ze):
        if all(np.isinf([xe, ze])):
            return 0
        elif any(np.isinf([xe, ze])):
            return cls._potential_semifinitecorner(x,y,z,xe,ze)
        else:
            return cls._potential_finitecorner(x,y,z,xe,ze)
    
    @classmethod
    def _potential_finitecorner(cls, x, y, z, xe, ze):
        return np.arctan((xe - x) * (ze - z) / y / np.sqrt(y**2 + (xe - x)**2 + (ze - z)**2)) / 2 / np.pi
    
    @classmethod
    def _potential_semifinitecorner(cls, x, y, z, xe, ze):
        if not np.isinf(xe):
            return cls._potential_semifinitecorner(z, y, x, ze, xe)
        # we can now assume xe is the infinite coordinate.
        if np.isneginf(xe):
            return -cls._potential_semifinitecorner(-x, y, z, np.infty, ze)
        # we can now assume xe is positive infty
        return np.arctan((ze - z) / y) / 2 / np.pi
    
    @classmethod
    def _grad_potential_corner(cls, x, y, z, xe, ze):
        if all(np.isinf([xe, ze])):
            return np.array([0,0,0])
        elif any(np.isinf([xe, ze])):
            return cls._grad_potential_semifinitecorner(x,y,z,xe,ze)
        else:
            return cls._grad_potential_finitecorner(x,y,z,xe,ze)
    
    """
    _grad_potential_finitecorner(x, y, z, xe, ze)
    
    Internal method for finding the gradient of the potential due to a single
    electrode corner with finite coordinates (xe, 0, ze).
    
    Source: http://www.wolframalpha.com/input/?i=gradient+of+arctangent%28%28a+
    -+x%29+*+%28b+-+z%29+%2F+%28y+*+sqrt%28y%5E2+%2B+%28a-x%29%5E2+%2B+%28b+-+z
    %29%5E2%29%29%29
    """
    @classmethod
    def _grad_potential_finitecorner(cls, x, y, z, xe, ze):
        dx2 = (xe - x)**2 + y**2
        dz2 = (ze - z)**2 + y**2
        dr = np.sqrt(dx2 + dz2 - y**2)
        gx = -y * (ze - z) / dx2 / dr
        gy = -(xe - x) * (ze - z) * (dx2 + dz2) / dx2 / dz2 / dr
        gz = -(xe - x) * y / dz2 / dr
        # print 'g = ',np.array([gx, gy, gz]) / 2 / np.pi
        return np.array([gx, gy, gz]) / 2 / np.pi
        
    """
    _grad_potential_semifinitecorner(x, y, z, xe, ze)
    
    Internal method for finding the gradient of the potential due to a single
    electrode corner with one infinite coordinate (xe, 0, ze). One of xe, ze is
    finite, the other should be +/- np.infty. 
    
    Source: http://www.wolframalpha.com/input/?i=%5Bd%2Fdy+arctangent%28%28b+-+
    z%29+%2F+y%29%2C+d%2Fdz+arctangent%28%28b+-+z%29+%2F+y%29%5D
    """
    @classmethod
    def _grad_potential_semifinitecorner(cls, x, y, z, xe, ze):
        if not np.isinf(xe):
            return cls._grad_potential_semifinitecorner(z, y, x, ze, xe)[::-1]
        # we can now assume xe is the infinite coordinate.
        if np.isneginf(xe):
            return -cls._grad_potential_semifinitecorner(-x, y, z, np.infty, ze)
        # we can now assume xe is positive infty
        
        dz2 = (ze - z)**2 + y**2
        gy = -(ze - z) / dz2
        gz = -y / dz2
        return np.array([0, gy, gz]) / 2 / np.pi

    @classmethod
    def _hess_potential_corner(cls, x, y, z, xe, ze, i, j):
        if all(np.isinf([xe, ze])):
            return 0
        elif any(np.isinf([xe, ze])):
            return cls._hess_potential_semifinitecorner(x,y,z,xe,ze,i,j)
        else:
            return cls._hess_potential_finitecorner(x,y,z,xe,ze,i,j)
    

    @classmethod
    def _hess_potential_semifinitecorner(cls, x, y, z, xe, ze, i, j):
        if not np.isinf(xe): 
            i = 2 - i if i != 1 else i # gonna swap x and z
            j = 2 - j if j != 1 else j # again
            
            return cls._hess_potential_semifinitecorner(z, y, x, ze, xe, i, j)
        
        # we can now assume xe is the infinite coordinate. no more x dependence!
        
        if np.isneginf(xe):
            return -cls._hess_potential_semifinitecorner(-x, y, z, np.infty, ze, i, j)
        
        # we can now assume xe is positive infty. no more worrying about signs!
        
        i, j = sorted([i, j])
        q = 1 + (ze - z)**2 / y**2
        
        if i == 0:
            return 0
        elif (i, j) == (1, 1):
            return 2 * (ze - z) / (y**3) * (1/q + (ze - z)**2 / y**2 / q**2) / 2 / np.pi
        elif (i, j) == (1, 2):
            return y**(-2) * (1 / q - 2*(ze - z)**2 / y**2 / q**2) / 2 / np.pi
        elif (i, j) == (2, 2):
            return -cls._hess_potential_semifinitecorner(x, y, z, xe, ze, 1, 1)
        
        return 0
    
    @classmethod
    def _hess_potential_finitecorner(cls, x, y, z, xe, ze, i, j):
        i, j = sorted([i, j])
        
        dx = xe - x
        dy = y
        dz = ze - z
        dx2 = dx**2
        dy2 = dy**2
        dz2 = dz**2
        r3 = np.sqrt(dx2 + dy2 + dz2)**3
        if (i, j) == (0, 0):
            return - dx * dy * dz * (3*dx2 + 3*dy2 + 2*dz2) / (dx2 + dy2)**2 / r3 / 2 / np.pi
        elif (i, j) == (0, 1):
            return -dz * (dx2**2 + dx2 * (dz2 - dy2) - dy2 * (2*dy2 + dz2)) / (dx2 + dy2)**2 / r3 / 2 / np.pi
        elif (i, j) == (0, 2):
            return dy / r3 / 2 / np.pi
        elif (i, j) == (1, 1):
            return (-cls._hess_potential_finitecorner(x, y, z, xe, ze, 0, 0)
                        -cls._hess_potential_finitecorner(x, y, z, xe, ze, 2, 2))
        elif (i, j) == (1, 2):
            return -dx*(dx2*dy2 - dx2*dz2 + 2*dy2**2 + dy2 * dz2 - dz2**2) / (dy2 + dz2) ** 2 / r3 / 2 / np.pi
        if (i, j) == (2, 2):
            return - dx * dy * dz * (2*dx2 + 3*dy2 + 3*dz2) / (dy2 + dz2)**2 / r3 / 2 / np.pi
    
    @classmethod
    def _hess_potential_semifinitecorner(cls, x, y, z, xe, ze, i, j):
        if not np.isinf(xe): 
            i = 2 - i if i != 1 else i # gonna swap x and z
            j = 2 - j if j != 1 else j # again
            
            return cls._hess_potential_semifinitecorner(z, y, x, ze, xe, i, j)
        
        # we can now assume xe is the infinite coordinate. no more x dependence!
        
        if np.isneginf(xe):
            return -cls._hess_potential_semifinitecorner(-x, y, z, np.infty, ze, i, j)
        
        # we can now assume xe is positive infty. no more worrying about signs!
        
        i, j = sorted([i, j])
        q = y**2 + (ze - z)**2
        
        if i == 0:
            return 0
        elif (i, j) == (1, 1):
            return 2 * y * (ze - z) / q**2 / 2 / np.pi
        elif (i, j) == (1, 2):
            return (y**2 - (ze - z)**2) / q**2 / 2 / np.pi
        elif (i, j) == (2, 2):
            return -cls._hess_potential_semifinitecorner(x, y, z, xe, ze, 1, 1)
        
        return 0
