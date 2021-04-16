
import numpy as np
from .utils.utils import *
from .bool_graph import BooleanGraph

##############################
#      GENERAL FUNCTIONS     #
##############################

def hill(x_array, n, k):
    return x_array**n / (x_array**n + k**n)

def normalised_hill(x_array, n, k):
    return hill(x_array, n, k) / hill(1, n, k)

##############################
#        CHILD CLASS         #
##############################

def ODE(graph, transform, **kwargs):
    '''
    Generate an ODE from RegulatoryNetwork/Boolean graph.

    Parameters
    ----------
    transform : str
        One of accepted transforms. See `booldog.ode_transforms` for
        options.

    Other Parameters
    ----------
    **kwargs
        Additional arguments and keyword arguments passed to
        specif parent class initializer.

    Returns
    ----------
    ode : ODE
        An ODE object

    Notes
    ----------
    Here is a summary of key word arguments, which may be out of date. For
    more comprehensive documentation of a specific transform, see
    `help(booldog.ode.<CLASS>)`, where <CLASS> can be determined from
    `booldog.ode.ode_classes[<transform>]. E.g
    `booldog.ode.ode_classes['squad']', when a SQUAD transformer is
    applicable.

    If ODE parameters are passed as an int or float, the value is assigned for
    all variables. Otherwise the parameter arguments should be a dict with a
    default' key and value pair, and key value pairs for other nodes.

    'squad'
    See [1] for additional information.
    - gamma : self-decay
    - h :  sigmoid gain

    'boolcube'/'boolecube'
    See [2] for additional information.

    - tau : life-time of species
    - n : Hill coefficient
    - k : Hill dissociation constant


    References
    ----------
    [1] Di Cara, A., Garg, A., De Micheli, G., Xenarios, I., & Mendoza, L.
    (2007). Dynamic simulation of regulatory networks using SQUAD.
    BMC Bioinformatics, 8(1), 1–10. https://doi.org/10.1186/1471-2105-8-462

    [2] Wittmann, D. M., Krumsiek, J., Saez-Rodriguez, J., Lauffenburger, D.
    A., Klamt, S., & Theis, F. J. (2009). Transforming Boolean models to
    continuous models: Methodology and application to T-cell receptor
    signaling. BMC Systems Biology, 3(1), 98.
    https://doi.org/10.1186/1752-0509-3-98
    '''

    ParentClass = ode_classes[transform]

    class ODE(ParentClass):

        def __init__(self, graph, transform, **kwargs):

            if not isinstance(graph, BooleanGraph):
                raise TypeError(f"'graph' argument must be a BooleanGraph object."\
                                f"not {type(graph)}. ")

            print("Initialising ODE system ... ", end="")
            self.n = len(graph)
            self.boolean_graph = graph
            self.transform = transform

            super().__init__(transform, **kwargs)

            print("done. ")


        def event_function(self, t, x, event_t, *args):
            return t - event_t
        event_function.terminal = True

        def update(self, off_nodes=[]):
            self._get_system(off_nodes=[],  **kwargs)


    return ODE(graph, transform, **kwargs)

##############################
#       PARENT CLASSES       #
##############################

# https://github.com/krumsieklab/Odefy/blob/11d048d550a8f64250ba01f76f5a83048c8be6cf/Odefy-1.20/code/models/CreateCubeCalls.m
class BoolCubeODE():
    ''' Use of multivariate polynomial interpolation for the transformation of a Boolean graph to a system of ODEs.

    Source: Transforming Boolean models to continuous models: methodology and application to T-cell receptor signaling [1].

    Attributes
    ----------
    dxdt
    param_tau
    param_n
    param_k
    param_dict

    Methods
    ----------
    homologue_b1

    References
    ----------
    [1] Wittmann, D. M., Krumsiek, J., Saez-Rodriguez, J., Lauffenburger, D.
    A., Klamt, S., & Theis, F. J. (2009). Transforming Boolean models to
    continuous models: Methodology and application to T-cell receptor
    signaling. BMC Systems Biology, 3(1), 98.
    https://doi.org/10.1186/1752-0509-3-98
    '''
    def __init__(self, transform, tau=1, n=3, k=0.5):
        ''' Initialise BoolCube ODE system.

        Parameters
        ----------
        transform : str

        tau : int, float, or dict, optional
            life-time of species

        n : int, float, or dict, optional
            Hill coefficient

        k : int, float, or dict, optional
            Hill dissociation constant

        Notes
        ----------
        Only used as Parent class.

        tau_i = zero --> dx_i/dt = 0

        If ODE parameters are passed as an int or float, the value is assigned
        for all variables. Otherwise the parameter arguments should be a dict
        with a default' key and value pair, and key value pairs for other
        nodes.
        '''

        self.param_n = parameter_to_array(n, self.boolean_graph.index)
        self.param_k = parameter_to_array(k, self.boolean_graph.index)

        self.param_tau = parameter_to_array(tau, self.boolean_graph.index)

        self.param_dict = {"n":self.param_n,
                           "k":self.param_k,
                           "tau":self.param_tau}


        off_nodes = set(np.where(self.param_tau ==0)[0])


        if transform in ('boolecube', 'boolcube'):
            self.dxdt =  self._get_system(lambda x, n, k: x,
                                          tau, n=n, k=k,
                                          off_nodes=off_nodes)

        elif transform in ('hill', 'hillcube'):
            self.dxdt =  self._get_system(hill,
                                          tau, n=n, k=k,
                                          off_nodes=off_nodes)

        elif transform in ('normalisedhill', 'normalisedhillcube'):
            self.dxdt =  self._get_system(normalised_hill,
                                          tau, n=n, k=k,
                                          off_nodes=off_nodes)

        else:
            raise TypeError(f"Unknown transform {transform}. ")


    def _get_system(self, transform_function, tau, off_nodes=[],  **kwargs):

        B1 = self.homologue_b1()

        def dxdt(t, x_array, *args):
            x_array[x_array < 0] = 0
            x_array[x_array > 1] = 1

            x_array = transform_function(x_array, **kwargs)
            b = B1(x_array)
            d = 1/self.param_tau * ( b  - x_array)
            for i in off_nodes:
                d[i] = 0
            return d

        return dxdt

    def homologue_b1(self):
        ''' Create function to calculate the multivariate polynomial
        interpolation of Boolean functions

        Returns
        ----------

        B1 : function

        '''
        spaces = set()
        sums = []
        all_B1s = ['0']*self.boolean_graph.n
        for node in self.boolean_graph.nodes: # iterate over all nodes
            for prime_dict in self.boolean_graph.primes[node][1]:
                for x_bool in self.boolean_graph.generate_states(
                                            fixed=prime_dict):
                    if not tuple(x_bool) in spaces:
                        spaces.add(tuple(x_bool))
                        product = []
                        for i, b in enumerate(x_bool):
                            if b ==0:
                                product.append(f'(1-x[{i}])')
                            else:
                                product.append(f'x[{i}]')
                    sums.append('*'.join(product))
            B1 = " + ".join(sums)
            if B1 != '':
                all_B1s[self.boolean_graph.index[node]]  = B1

        return eval('lambda x:' + 'np.array([' + ','.join(all_B1s) + '])')

class SquadODE():
    ''' Use of SQUAD for the transformation of a Boolean graph to a system of ODEs.

    Source: Dynamic simulation of regulatory networks using SQUAD [1].

    Attributes
    ----------
    dxdt
    param_gamma
    param_h
    Act
    Inh

    Methods
    ----------

    References
    ----------
    [1] Di Cara, A., Garg, A., De Micheli, G., Xenarios, I., & Mendoza, L.
    (2007). Dynamic simulation of regulatory networks using SQUAD.
    BMC Bioinformatics, 8(1), 1–10. https://doi.org/10.1186/1471-2105-8-462
    '''

    def __init__(self, transform, gamma=1, h=10):
        '''Transform a Activation/Inhibition Boolean network
        into an ODE system via SQUAD transform.

        Parameters
        ----------

        transform : str

        gamma : int, float, or dict, optional
            decay rate

        h : int, float, or dict, optional
            sigmoidal gain

        Notes
        ----------
        Only used as Parent class.

        If ODE parameters are passed as an int or float, the value is assigned
        for all variables. Otherwise the parameter arguments should be a dict
        with a default' key and value pair, and key value pairs for other
        nodes.
        '''

        self.param_gamma = parameter_to_array(gamma, self.boolean_graph.index)
        self.param_h = parameter_to_array(h, self.boolean_graph.index)

        # matrices
        self.Act, self.Inh = self.boolean_graph.primes_to_matrices()

        # needed for computations
        col_ones = np.ones((self.n))
        self._A1 = self.Act.dot(col_ones)
        self._a1 = (1+self._A1)/self._A1
        self._B1 = self.Inh.dot(col_ones)
        self._b1 = (1+self._B1)/self._B1

        self.dxdt = self._get_system()

    def _omega(self, x):
        '''
        Equation (2) of Di Cara et al (2007)
        http://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-8-462
        Based on Andre Blejec R code.
        '''

        x = ensure_ndarray(x)

        col_ones = np.ones((self.n))

        Ax = self.Act.dot(x)
        a = ensure_ndarray( self._a1 * Ax/(1+Ax) )
        a[~np.isfinite(a)] = 1

        Bx = self.Inh.dot(x)
        b = ensure_ndarray( self._b1 * Bx/(1+Bx) )
        b[~np.isfinite(b)] = 0

        o = ensure_ndarray(a * (1-b))
        o[np.where(self._A1 + self._B1 ==0)] = 0

        return o

    def _dxdt_transform(self, x, w):
        ''' Equation (2) of Di Cara et al (2007) '''
        return (-np.exp(0.5*self.param_h) + np.exp(-self.param_h*(w-0.5))) / \
              ((1-np.exp(0.5*self.param_h))*(1+np.exp(-self.param_h*(w-0.5))))\
                - self.param_gamma*x

    def _get_system(self, off_nodes=[]):

        def dxdt(t, x_array, *args):
            w = self._omega(x_array)
            d = self._dxdt_transform(x_array, w)
            for i in off_nodes:
                d[i] = 0
            return d

        return dxdt






class ShaoODE():
    '''
    Source: From Boolean Network Model to Continuous Model Helps in Design of
    Functional Circuits
    '''
    def __init__(self, graph):
        super().__init__(graph)
        self.dxdt = self._squad(graph, gamma, h)





class RacipeODE():

    def __init__(self, graph, transform, gamma=1, h=10):
        '''
        Transform a Activation/Inhibition Boolean network
        into an ODE system via the RACIPE transform.

        If ODE parameters are passed as an int or float, the value is
        assigned for all variables
        other wise a dict with a 'default' key and value, and key value
        pairs for all others.

        Parameters
        ----------

        gamma : float, dict
            decay rate

        h : float, dict
            gain(?)


        '''
        super().__init__(graph)

        self.dxdt = self._squad(graph, gamma, h)
        print("done. ")




ode_classes = {'squad':SquadODE,
               'shao':ShaoODE,
               'hillcube':BoolCubeODE,
               'normalisedhillcube':BoolCubeODE,
               'boolcube':BoolCubeODE,
               'boolecube':BoolCubeODE}

ode_transforms = set(ode_classes.keys())