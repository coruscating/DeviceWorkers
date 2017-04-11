# helper functions, esp. for calculating partials with SciPy
# written by Zach Fisher, 2012 Jan 18

from __future__ import division
import scipy.misc

def gradient(f, x, y, z, dx = 1.0, dy = 1.0, dz = 1.0):
	f_x = scipy.misc.derivative(lambda x1: f(x1, y, z), x, dx = dx)
	f_y = scipy.misc.derivative(lambda y1: f(x, y1, z), y, dx = dy)
	f_z = scipy.misc.derivative(lambda z1: f(x, y, z1), z, dx = dz)
	return [f_x, f_y, f_z]
	
def secondderiv_matrix(f, x, y, z, dx = 1.0, dy = 1.0, dz = 1.0):
    df = []
    df.append(lambda x2, y2, z2: scipy.misc.derivative(lambda x1: f(x1, y2, z2), x2, dx = dx))
    df.append(lambda x2, y2, z2: scipy.misc.derivative(lambda y1: f(x2, y1, z2), y2, dx = dy))
    df.append(lambda x2, y2, z2: scipy.misc.derivative(lambda z1: f(x2, y2, z1), z2, dx = dz))
    
    return [gradient(dfi,x, y , z, dx, dy, dz) for dfi in df]

# partial(f, order, args, precision = 1e-6):

# def partial(f, order, args, precision = 1e-6, default_step = None):
#     f_eval = f
#     vfieldgenerator = UnitVectorFieldGenerator(order, args)
#     for vfield = vfieldgenerator.iter():
#         step = default_step if default_step is not None else precision
#         f2 = lambda y:f_eval(vfield[1](y))
#         
#         d = None
#         d2 = None
#         step *= 10
#         while d is None or d2 is None or abs(d - d2) < precision:
#             step /= 10
#             d2 = d
#             d = scipy.misc.derivative(f2, vfield[0], dx = step, n = vfield[2], order = 2 * vfield[2] + 1)
#         f_eval = lambda x:scipy.misc.derivative(f_eval, vfield[0], dx = step, n = vfield[2], order = 2 * vfield[2] + 1)
    

def test_derivatives():
    f = lambda x,y,z: x**2 * y + z**2 * x
    assert gradient(f, 1, 2, 3) == [13.0, 1.0, 6.0], 'Problem: Gradient function returned the wrong value.'
    assert secondderiv_matrix(f, 1, 2, 3) == [[4.0, 2.0, 6.0], [2.0, 0.0, 0.0], [6.0, 0.0, 2.0]], 'Problem: 2nd derivative matrix function returned the wrong value.'
    print 'Tests passed.'
    
class UnitVectorFieldGenerator:
    def __init__(self, order, args):
        self.order = order
        self.args = args
        self.len = len(args)
    
    def iter(self):
        n = 0
        for o in self.order:
            if o > 0:
                yield (self.args[n], lambda y:[y if i == n else self.args[i] for i in xrange(self.len)], o)
            n += 1