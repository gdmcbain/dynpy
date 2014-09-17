"""Module implementing some base classes useful for implementing dynamical
systems"""

from __future__ import division, print_function, absolute_import
import sys
if sys.version_info < (3,):
    range = xrange

import collections

import numpy as np

from . import mx
from . import caching

# Constants for finding attractors
MAX_ATTRACTOR_LENGTH = 5
TRANSIENT_LENGTH = 30

DEFAULT_TRANSMX_CLASS = mx.DenseMatrix
DEFAULT_STATE_DTYPE = 'float64'


class DynamicalSystemBase(object):
    """Base class for dynamical systems.

    Parameters
    ----------
    discrete_time : bool, optional
        Whether updating should be done using discrete (default) or continuous
        time dynamics.
    """

    #: Whether the dynamical system obeys discrete- or continuous-time dynamics
    discrete_time = True

    def __init__(self, discrete_time=True):
        self.discrete_time = discrete_time

        if self.discrete_time:
            self.iterate = self._iterateDiscrete
            self.iterateOneStep = self._iterateOneStepDiscrete
        else:
            self.iterate = self._iterateContinuous

    def states(self):
        raise NotImplementedError

    def iterate(self, startState, max_time):
        """This method runs the dynamical system for `max_time` starting from
        `startState` and returns the result.  In fact, this method is set at
        run-time by the constructor to either `_iterateDiscrete` or
        `_iterateContinuous` depending on whether the dynamical system object
        is initialized with `discrete_time=True` or `discrete_time=False`. Thus,
        sub-classes should override `_iterateDiscrete` and `_iterateContinuous`
        instead of this method.  See also
        :meth:`dynpy.dynsys.DynamicalSystemBase.iterateOneStep`

        Parameters
        ----------
        startState : numpy array or scipy.sparse matrix
            Which state to start from
        max_time : float
            Until which point to run the dynamical system (number of iterations
            for discrete-time systems or time limit for continuous-time systems)

        Returns
        -------
        numpy array or scipy.sparse matrix
            End state
        """
        raise NotImplementedError

    def iterateOneStep(self, startState):
        """
        This method runs a discrete-time dynamical system for 1 timestep. At
        run-time, the construct either repoints this method to `_iterateOneStep`
        for discrete-time systems, or removes it for continuous time systems.

        Parameters
        ----------
        startState : numpy array or scipy.sparse matrix
            Which state to start from


        Returns
        -------
        numpy array or scipy.sparse matrix
            Iterated state
        """
        raise NotImplementedError

    def _iterateOneStepDiscrete(self, startState, num_iters=1):
        raise NotImplementedError

    def _iterateDiscrete(self, startState, max_time=1.0):
        # TODO: Use this to generate fast weave code, or at least make faster
        if max_time == 1.0:
            return self.iterateOneStep(startState)
        elif max_time == 0.0:
            return startState
        else:
            cState = startState
            for i in range(int(max_time)):
                cState = self.iterateOneStep(cState)
            return cState

    def getTrajectory(self, startState, max_time, num_points=None,
                      logscale=False):
        """This method get a trajectory (i.e. matrix ) runs a discrete-time
        dynamical system for 1 timestep.

        At run-time, the construct either repoints this method to
        `_iterateOneStep` for discrete-time systems, or removes it for
        continuous time systems.

        Parameters
        ----------
        startState : object
            Which state to start from
        max_time : float
            Until which point to run the dynamical system (number of iterations
            for discrete-time systems or time limit for continuous-time systems)
        num_timepoints : int, optional
            How many timepoints to sample the trajectory at.  In other words,
            how big each 'step size' is. By default, equal to ``int(max_time)``
        logscale : bool, optional
            Whether to sample the timepoints on a logscale or not (default)

        Returns
        -------


        """
        # TODO: would this accumulate error for continuous case?
        if num_points is None:
            num_points = int(max_time)

        if logscale:
            timepoints = np.logspace(0, np.log10(max_time), num=num_points,
                                     endpoint=True, base=10.0)
        else:
            timepoints = np.linspace(0, max_time, num=num_points, endpoint=True)

        cState = startState
        trajectory = [cState,]

        for cNdx in range(1, len(timepoints)):
            run_time = timepoints[cNdx]-timepoints[cNdx-1]
            nextState = self.iterate(cState, max_time=run_time)
            cState = nextState
            trajectory.append( cState )

        return np.vstack(trajectory)

    def state2ndx(self, state):
        return state

    def ndx2state(self, ndx):
        return ndx

class MultivariateSystem(object):
    """Class that should be mixed-in for dynamics over multivariate systems.

    Parameters
    ----------
    num_vars : int, optional
        How many variables (i.e., how many 'dimensions' or 'nodes' are in the
        dynamical system). Default is 1
    var_names : list, optional
        Names for the variables (optional).  Default is simply the numeric
        indexes of the variables.
    """

    #: The number of variables in the dynamical system
    num_vars = None

    #: ``(num_states, num_vars)``-shaped matrix which maps from integer state
    #: indexes to their representations in terms of the values of the system
    #: variables.  Any subclass needs to implement.
    ndx2stateMx = None

    def __init__(self, num_vars, var_names=None):
        self.num_vars = num_vars

        self.var_names = tuple(var_names if var_names is not None
                               else range(self.num_vars))
        """The names of the variables in the dynamical system"""

        super(MultivariateSystem, self).__init__()

    @caching.cached_data_prop
    def _state2ndxDict(self):
        d = dict( (mx.hash_np(state), ndx)
                  for ndx, state in enumerate(self.states()))
        return d

    @caching.cached_data_prop
    def _ndx2stateDict(self):
        d = dict( enumerate(self.states()) )
        return d

    def state2ndx(self, state):
        """Function which maps from multidimensional states of variables
        (`state`) to single-integer state indexes.
        """
        # TODOTEST
        h = mx.hash_np(state.astype(self.cDataType))
        try:
            return self._state2ndxDict[h]
        except KeyError:
            raise KeyError('%r (hash=%s)' % (state, h))

    def ndx2StateMx(self):
        raise NotImplementedError

    def ndx2state(self, ndx):
        print('called')
        return self._ndx2stateDict[ndx]

    # Make this a cached property so its not necessarily run every time a
    # dynamical systems object is created, whether we need it or not
    @caching.cached_data_prop
    def var_name_ndxs(self):
        """A mapping from variables names to their indexes
        """
        return dict((l, ndx) for ndx, l in enumerate(self.var_names))

    def getVarNextState(self, state):
        raise NotImplementedError

"""
class MarginalizedMultivariateSystem(MultivariateSystem):

    def __init__(self, base_system, keep_vars):
        self.base_system = base_system
        self.keep_vars = keep_vars
        super(MarginalizedMultivariateSystem, self).__init__(
            len(keep_vars),
            [base_system.var_names[i] for i in keep_vars]
            )

    def states(self):
        done_states = set()
        for state in self.base_system:
            m_state = state[self.keep_vars]
            if m_state not in done_states:
                done_states.add(m_state)
                yield m_state
"""

class LinearSystemBase(DynamicalSystemBase):
    # TODOTESTS
    """This class implements linear dynamical systems, whether continuous or
    discrete-time.  It is also used by :class:`dynpy.dynsys.MarkovChain` to
    implement Markov Chain (discrete-case) or  master equation (continuous-case)
    dynamics.

    For attribute definitions, see documentation of
    :class:`dynpy.dynsys.DynamicalSystemBase`.

    Parameters
    ----------
    updateCls : {:class:`dynpy.mx.DenseMatrix`, :class:`dynpy.mx.SparseMatrix`}, optional
        Whether to use sparse or dense matrices for the update operator matrix.
        Default set by `dynpy.dynsys.DEFAULT_TRANSMX_CLASS`
    discrete_time : bool, optional
        Whether updating should be done using discrete (default) or continuous
        time dynamics.
    """

    updateOperator = None

    def __init__(self, updateCls=None, discrete_time=True):
        super(LinearSystemBase, self).__init__(discrete_time=discrete_time)
        # self.updateOperator = updateOperator
        if updateCls is None:
            updateCls = DEFAULT_TRANSMX_CLASS
        self.updateCls = updateCls
        if discrete_time:
            self.stableEigenvalue = 1.0
        else:
            self.stableEigenvalue = 0.0

    def equilibriumState(self):
        """Get equilibrium state of dynamical system using eigen-decomposition

        Returns
        -------
        numpy array or scipy.sparse matrix
            Equilibrium state
        """

        vals, vecs = self.updateCls.getLargestLeftEigs(self.updateOperator)
        equil_evals = np.flatnonzero(np.abs(vals-self.stableEigenvalue) < 1e-8)
        if len(equil_evals) != 1:
            raise Exception("Expected one stable eigenvalue, but found " +
                            "%d instead (%s)" % (len(equil_evals), equil_evals))

        equilibriumState = np.real_if_close(np.ravel(vecs[equil_evals, :]))
        if np.any(np.iscomplex(equil_evals)):
            raise Exception("Expect equilibrium state to be real! %s" %
                            equil_evals)

        return self.updateCls.formatMx(equilibriumState)

    def _iterateOneStepDiscrete(self, startState):
        # For discrete time systems, one step
        r = self.updateCls.formatMx(startState).dot(self.updateOperator)
        return r

    def _iterateDiscrete(self, startState, max_time=1.0):
        # For discrete time systems
        r = self.updateCls.formatMx(startState).dot(
                self.updateCls.pow(self.updateOperator, int(max_time)))
        return r

    def _iterateContinuous(self, startState, max_time=1.0):
        curStartStates = self.updateCls.formatMx(startState)
        r = curStartStates.dot(
              self.updateCls.expm(max_time * (self.updateOperator)))
        return r

    # TODO
    # def getMultistepDynsys(self, num_iters):
    #     import copy
    #     rObj = copy.copy(self)
    #     rObj.trans = self.updateOperatorCls.pow(self.updateOperator, num_iters)
    #     return rObj

class LinearSystem(LinearSystemBase):
    """
    Parameters
    ----------
    updateOperator : numpy array or scipy.sparse matrix
        Matrix defining the evolution of the dynamical system, i.e. the
        :math:`\\mathbf{A}` in
        :math:`\\mathbf{x_{t+1}} = \\mathbf{x_{t}}\\mathbf{A}` (in the
        discrete-time case) or
        :math:`\\dot{\\mathbf{x}} = \\mathbf{x}\\mathbf{A}` (in the
        continuous-time case)
    """
    def __init__(self, updateOperator, updateCls=None, discrete_time=True):
        super(LinearSystem,self).__init__(updateCls=updateCls, discrete_time=discrete_time)
        self.updateOperator = updateOperator

class MarkovChain(LinearSystemBase):
    """This class implements a Markov Chain over the state-transition graph of
    an underlying dynamical system, specified by the `baseDynamicalSystem`
    parameter.  It maintains properties of the underlying system, such as the
    sparsity of the state transition matrix, and whether the system is discrete
    or continuous-time.  The underlying system must be an instance of
    :class:`dynpy.dynsys.DiscreteStateSystemBase` and provide a transition
    matrix in the form of a `trans` property.

    For example, we can use this to derivate the dynamics of a probability of
    an ensemble of random walkers on the karate club network (this results in a
    heat-equation type system):

    >>> import dynpy
    >>> import numpy as np
    >>> kc = dynpy.sample_nets.karateclub_net
    >>> rw = dynpy.graphdynamics.RandomWalker(graph=kc, transCls=dynpy.mx.DenseMatrix)
    >>> rwEnsemble = dynpy.dynsys.MarkovChain(rw)
    >>>
    >>> initState = np.zeros(rw.num_vars)
    >>> initState[ 5 ] = 1
    >>>
    >>> trajectory = rwEnsemble.getTrajectory(initState, max_time=2)[1,1]

    It can also be done for a Boolean network:

    >>> import dynpy
    >>> yeast = dynpy.sample_nets.yeast_cellcycle_bn
    >>> bn = dynpy.bn.BooleanNetwork(rules=yeast, transCls=dynpy.mx.SparseMatrix)
    >>> bnEnsemble = dynpy.dynsys.MarkovChain(bn)
    >>> init = bnEnsemble.getUniformDistribution()
    >>> trajectory = bnEnsemble.getTrajectory(init, max_time=80)

    If we wish to project the state of the Markov chain back onto the
    activations of the variables in the underlying system, we can use the
    `ndx2stateMx` matrix of the underlying system. For example:

    >>> import dynpy
    >>> import numpy as np
    >>> yeast = dynpy.sample_nets.yeast_cellcycle_bn
    >>> bn = dynpy.bn.BooleanNetwork(rules=yeast, transCls=dynpy.mx.SparseMatrix)
    >>> bnEnsemble = dynpy.dynsys.MarkovChain(bn)
    >>> init = bnEnsemble.getUniformDistribution()
    >>> final_state = bnEnsemble.iterate(init, max_time=80)
    >>> print(np.ravel(final_state.dot(bn.ndx2stateMx)))
    [ 0.          0.05664062  0.07373047  0.07373047  0.91503906  0.          0.
      0.          0.92236328  0.          0.        ]


    Parameters
    ----------
    baseDynamicalSystem : :class:`dynpy.dynsys.DiscreteStateSystemBase`
        an object containing the underlying dynamical system over which an
        ensemble will be created.

    """

    """This is a base class for discrete-state dynamical systems.  It provides
    a transition matrix indicating transitions between system states.

    Parameters
    ----------
    transCls : {:class:`dynpy.mx.DenseMatrix`, :class:`dynpy.mx.SparseMatrix`}, optional
        Whether to use sparse or dense matrices for the transition matrix.
        Default set by `dynpy.dynsys.DEFAULT_TRANSMX_CLASS`
    discrete_time : bool, optional
        Whether updating should be done using discrete (default) or continuous
        time dynamics.
    """


    def __init__(self, updateCls=None, discrete_time=True, underlyingstates=None):
        super(MarkovChain, self).__init__(updateCls=updateCls, 
                                          discrete_time=discrete_time)
        self.underlyingstates = underlyingstates

    def equilibriumState(self):
        """Get equilibrium state (i.e. the stable, equilibrium distribution)
        for this dynamical system.  Uses eigen-decomposition.

        Returns
        -------
        numpy array or scipy.sparse matrix
            Equilibrium distribution
        """

        equilibriumDist = super(MarkovChain, self).equilibriumState()
        equilibriumDist = equilibriumDist / equilibriumDist.sum()

        if np.any(self.updateCls.toDense(equilibriumDist) < 0.0):
            raise Exception("Expect equilibrium state to be positive!")
        return equilibriumDist

    def getUniformDistribution(self):
        """Gets uniform starting distribution over all system states"""
        N = self.updateOperator.shape[0]
        return np.ones(N) / float(N)

    def checkTransitionMatrix(self, trans):
        """Internally used function that checks the integrity/format of
        transition matrices.
        """
        if trans.shape[0] != trans.shape[1]:
            raise Exception('Expect square transition matrix (got %s)' %
                            trans.shape)
        sums = mx.todense(trans.sum(axis=1))
        if self.discrete_time:
            if not np.allclose(sums, 1.0):
                raise Exception('For discrete system, state transitions ' +
                                'entries should add up to 1.0 (%s)' % sums)
        else:
            if not np.allclose(sums, 0.0):
                raise Exception('For continuous system, state transitions ' +
                                'entries should add up to 0.0 (%s)' % sums)

    def stgIgraph(self):
        """
        Returns
        -------
        igraph `Graph` object
            The state transition graph, in the form of an igraph Graph object
        """
        import igraph
        return igraph.Graph(list(zip(*self.updateOperator.nonzero())), directed=True)

    def getAttractorsAndBasins(self):
        """Computes the attractors and basins of the current discrete-state
        dynamical system.

        Returns
        -------
        basinAtts : list of lists
            A list of the the attractor states for each basin (basin order is
            from largest basin to smallest).

        basinStates : list of lists
            A list of all the states in each basin (basin order is from largest
            basin to smallest).

        """

        STG = self.stgIgraph()

        multistepDyn = self.updateCls.pow(self.updateOperator, TRANSIENT_LENGTH)
        attractorStates = np.ravel(
            self.updateCls.make2d(multistepDyn.sum(axis=0)).nonzero()[1])

        basins = collections.defaultdict(list)
        for attState in attractorStates:
            cBasin = tuple(STG.subcomponent(attState, mode='IN'))
            basins[cBasin].append(attState)

        basinAtts = list(basins.values())
        basinStates = list(basins.keys())
        bySizeOrder = np.argsort(list(map(len, basinStates)))[::-1]
        return [basinAtts[b]   for b in bySizeOrder], \
               [list(basinStates[b]) for b in bySizeOrder]

class MarkovChainSampler(DynamicalSystemBase):
    def __init__(self, markov_chain):
        if markov_chain.discrete_time == False:
            raise Exception('Can only sample from discrete-time MCs')
        self.markov_chain = markov_chain
        print(self.markov_chain.underlyingstates)
        super(MarkovChainSampler, self).__init__(discrete_time=True)

    def states(self):
        raise xrange(self.markov_chain.updateOperator.shape[0])

    def _iterateOneStepDiscrete(self, startState):
        mc = self.markov_chain
        initStateDist = np.zeros(mc.updateOperator.shape[0], 'float')
        initStateDist[ startState ] = 1


        probs = mc.iterateOneStep(initStateDist)
        probs = np.ravel(mc.updateCls.toDense(probs))
        num_states = self.markov_chain.updateOperator.shape[0]
        r = np.random.choice(np.arange(num_states), None, replace=True, p=probs)
        print(r)
        print(list(self.markov_chain.underlyingstates())[r])
        return self.markov_chain.ndx2state(r)

    def _iterateContinuous(self, startState, max_time = 1.0):
        raise NotImplementedError



    