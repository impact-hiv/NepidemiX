from nepidemix.process import ExplicitStateProcess

from nepidemix.utilities.networkxtra import attributeCount, neighbors_data_iter

import numpy


class SIRProcess(ExplicitStateProcess):
    """
    S I R process,

    Attributes
    ----------
    beta - Infection rate.
    gamma - Recovery rate. 
    """
    def __init__(self, beta, gamma):
        
        super(SIRProcess, self).__init__(['S', 'I', 'R'],
                                         [],
                                         runNodeUpdate = True,
                                         runEdgeUpdate = False,
                                         runNetworkUpdate = False,
                                         constantTopology = True)
        self.beta = float(beta)
        self.gamma = float(gamma)

    
    def nodeUpdateRule(self, node, srcNetwork, dt):
        # Read original node state.
        srcState = node[1][self.STATE_ATTR_NAME]
        # By default we have not changed states, so set
        # the destination state to be the same as the source state.
        dstState = srcState

        # Start out with a dictionary of zero neighbors in each state.
        nNSt = dict(zip(self.nodeStateIds,[0]*len(self.nodeStateIds)))
        # Calculate the actual numbers and update dictionary.
        nNSt.update(attributeCount(neighbors_data_iter(srcNetwork, node[0]),
                                   self.STATE_ATTR_NAME))

        # Pick a random number.
        eventp = numpy.random.random_sample()
        # Go through each state name, and chose an action.
        if srcState == 'S':
            if eventp < self.beta*nNSt['I']*dt:
                dstState = 'I'
        elif srcState == 'I':
            if eventp < self.gamma*dt:
                dstState = 'R'

        node[1][self.STATE_ATTR_NAME] = dstState

        return node



class SIJRProcess(ExplicitStateProcess):
    """
    S I (J) R process, where J is a super-spreader state of the Infected class.
    For simplicity we assume that the recovery rate of the J class is the same
(gamma) as for the I class.

    Attributes
    ----------
    beta - Infection rate.
    gamma - Recovery rate. 
    alpha - Rate at which an infected node turns into a super-spreader.
    """
    def __init__(self, beta, gamma, alpha):
        
        super(SIJRProcess, self).__init__(['S', 'I', 'J', 'R'],
                                            [],
                                          runNodeUpdate = True,
                                          runEdgeUpdate = False,
                                          runNetworkUpdate = True,
                                          constantTopology = True)
        self.beta = float(beta)
        self.gamma = float(gamma)
        self.alpha = float(alpha)

    
    def nodeUpdateRule(self, node, srcNetwork, dt):
        
        # Read original node state.
        srcState = node[1][self.STATE_ATTR_NAME]
        # By default we have not changed states, so set
        # the destination state to be the same as the source state.
        dstState = srcState

        # Start out with a dictionary of zero neighbors in each state.
        nNSt = dict(zip(self.nodeStateIds,[0]*len(self.nodeStateIds)))
        # Calculate the actual numbers and update dictionary.
        nNSt.update(attributeCount(neighbors_data_iter(srcNetwork, node[0]),
                                   self.STATE_ATTR_NAME))

        # Pick a random number.
        eventp = numpy.random.random_sample()
        # Go through each state name, and chose an action.
        if srcState == 'S':
            if eventp < ( self.beta*(nNSt['I'] +nNSt['J']) + srcNetwork.graph['fracJ'])*dt:
                dstState = 'I'
        elif srcState == 'I':
            # Check recovery before super spreader.
            if eventp < self.gamma*dt:
                dstState = 'R'
            elif eventp - self.gamma*dt < self.alpha*dt:
                dstState = 'J'
                self.Jcounter += 1
            # Super spreaders are still infected and can recover.
        elif srcState == 'J':
            if eventp < self.gamma*dt:
               dstState = 'R' 
               self.Jcounter -= 1

        node[1][self.STATE_ATTR_NAME] = dstState

        return node

    def networkUpdateRule(self, network, dt):
        # We have to count the fraction of the population
        # in the J state here.
        # However as the variable self.Jcounter contains
        # the number of nodes in state J we can use that.
        network.graph['fracJ'] = self.Jcounter/float(len(network))
        return network

    def initializeNetworkNodes(self, network, *args, **kwargs):
        # Use most of the functionality in the superclass.
        super(SIJRProcess, self).initializeNetworkNodes(network, *args, **kwargs)
        # Now the network should be initialized so we can compute the right fraction of super-spreaders.
        d = attributeCount(network.nodes_iter(data=True),self.STATE_ATTR_NAME)
        self.Jcounter = d.get('J',0.0)
        network.graph['fracJ'] = self.Jcounter/float(len(network))
        return network
