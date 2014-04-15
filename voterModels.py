from mydecorators import autoassign, cached_property, setdefaultattr

import random
from numpy.lib.scimath import sqrt
from numpy.core.fromnumeric import mean, std
from numpy.lib.function_base import median
from numpy.ma.core import floor
from test.test_binop import isnum
from debugDump import *

class Voter(tuple):
    """A tuple of candidate utilities.
    
    

    """
    
    @classmethod
    def rand(cls, ncand):
        """Create a random voter with standard normal utilities.
        
        ncand determines how many utilities a voter should have
            >>> [len(Voter.rand(i)) for i in list(range(5))]
            [0, 1, 2, 3, 4]
        
        utilities should be in a standard normal distribution
            >>> v100 = Voter.rand(100)
            >>> -0.3 < mean(v100) < 0.3
            True
            >>> 0.8 < std(v100) < 1.2
            True
        """
        return cls(random.gauss(0,1) for i in range(ncand))
        
    
    def hybridWith(self, v2, w2):
        """Create a weighted average of two voters. 
        
        The weight of v1 is always 1; w2 is the weight of v2 relative to that.
        
        If both are
        standard normal to start with, the result will be standard normal too.
        
        Length must be the same
            >>> Voter([1,2]).hybridWith(Voter([1,2,3]),1)
            Traceback (most recent call last):
              ...
            AssertionError

        A couple of basic sanity checks:
            >>> v2 = Voter([1,2]).hybridWith(Voter([3,2]),1)
            >>> [round(u,5) for u in v2.hybridWith(v2,1)]
            [4.0, 4.0]
            >>> Voter([1,2,5]).hybridWith(Voter([-0.5,-1,0]),0.75)
            (0.5, 1.0, 4.0)
        """
        assert len(self) == len(v2)
        return self.copyWithUtils(  ((self[i] / sqrt(1 + w2 ** 2)) + 
                                    (w2 * v2[i] / sqrt(1 + w2 ** 2)))
                                 for i in range(len(self)))
            
    def copyWithUtils(self, utils):
        """create a new voter with attrs as self and given utils.
        
        This version is a stub, since this voter class has no attrs."""
        return self.__class__(utils)
    
    def mutantChild(self, muteWeight):
        """Returns a copy hybridized with a random voter of weight muteWeight.
        
        Should remain standard normal:
            >>> v100 = Voter.rand(100)
            >>> for i in range(30):
            ...     v100 = v100.mutantChild(random.random())
            ... 
            >>> -0.3 < mean(v100) < 0.3 #3 sigma
            True
            >>> 0.8 < std(v100) < 1.2 #meh that's roughly 3 sigma
            True

        """
        return self.hybridWith(self.__class__.rand(len(self)), muteWeight)
    
class PersonalityVoter(Voter):
    
    cluster_count = 0
    
    def __init__(self, *args, **kw):
        super().__init__()#*args, **kw) #WTF, python?
        self.cluster = self.__class__.cluster_count
        self.__class__.cluster_count += 1
        self.personality = random.gauss(0,1) #probably to be used for strategic propensity
        #but in future, could be other clustering voter variability, such as media awareness
        #print(self.cluster, self.personality)
        
    #@classmethod
    #def rand(cls, ncand):
    #    voter = super().rand(ncand)
    #    return voter
    
    @classmethod
    def resetClusters(cls):
        cls.cluster_count = 0
    
    def copyWithUtils(self, utils):
        voter = super().copyWithUtils(utils)
        voter.personality = self.personality
        voter.cluster = self.cluster
        return voter
            
class Electorate(list):
    """A list of voters.
    Each voter is a list of candidate utilities"""
    @cached_property
    def socUtils(self):
        """Just get the social utilities.
        
        >>> e = Electorate([[1,2],[3,4]])
        >>> e.socUtils
        [2.0, 3.0]
        """
        return list(map(mean,zip(*self)))
    
class RandomModel:
    """Empty base class for election models; that is, electorate factories.
    
    >>> e4 = RandomModel()(4,3)
    >>> [len(v) for v in e4]
    [3, 3, 3, 3]
    """
    def __call__(self, nvot, ncand, vType=PersonalityVoter):
        return Electorate(vType.rand(ncand) for i in range(nvot))
    
class DeterministicModel:
    """Basically, a somewhat non-boring stub for testing.
    
        >>> DeterministicModel(3)(4, 3)
        [(0, 1, 2), (1, 2, 0), (2, 0, 1), (0, 1, 2)]
    """
    
    @autoassign
    def __init__(self, modulo):
        pass
    
    def __call__(self, nvot, ncand, vType=PersonalityVoter):
        return Electorate(vType((i+j)%self.modulo for i in range(ncand))
                          for j in range(nvot))
    
class ReverseModel(RandomModel):
    """Creates an even number of voters in two diametrically-opposed camps
    (ie, opposite utilities for all candidates)
    
    >>> e4 = ReverseModel()(4,3)
    >>> [len(v) for v in e4]
    [3, 3, 3, 3]
    >>> e4[0].hybridWith(e4[3],1)
    (0.0, 0.0, 0.0)
    """
    def __call__(self, nvot, ncand, vType=PersonalityVoter):
        if nvot % 2:
            raise ValueError
        basevoter = vType.rand(ncand)
        return Electorate( ([basevoter] * (nvot//2)) + 
                           ([vType(-q for q in basevoter)] * (nvot//2))
                        )

class QModel(RandomModel):
    """Adds a quality dimension to a base model,
    by generating an election and then hybridizing all voters
    with a common quality vector.
    
    Useful along with ReverseModel to create a poor-man's 2d model.
    
    Basic structure
        >>> e4 = QModel(sqrt(3), RandomModel())(100,1)
        >>> len(e4)
        100
        >>> len(e4.socUtils)
        1
        
    Reduces the standard deviation
        >>> 0.4 < std(list(zip(e4))) < 0.6
        True

    """
    @autoassign
    def __init__(self, qWeight=0.5, baseModel=ReverseModel()):
        pass
    
    def __call__(self, nvot, ncand, vType=PersonalityVoter):
        qualities = vType.rand(ncand)
        return Electorate([v.hybridWith(qualities,self.qWeight)
                for v in self.baseModel(nvot, ncand, vType)])


class PolyaModel(RandomModel):
    """This creates electorates based on a Polya/Hoppe/Dirchlet model, with mutation.
    You start with an "urn" of n=seedVoter voters from seedModel,
     plus alpha "wildcard" voters. Then you draw a voter from the urn, 
     clone and mutate them, and put the original and clone back into the urn.
     If you draw a "wildcard", use voterGen to make a new voter.
     """
    @autoassign
    def __init__(self, seedVoters=2, alpha=1, seedModel=QModel(),
                 mutantFactor=0.2):
        pass
    
    def __call__(self, nvot, ncand, vType=PersonalityVoter):
        """Tests? Making statistical tests that would pass reliably is
        a huge hassle. Sorry, maybe later.
        """
        vType.resetClusters()
        election = self.seedModel(self.seedVoters, ncand, vType)
        while len(election) < nvot:
            i = random.randrange(len(election) + self.alpha)
            if i < len(election):
                election.append(election[i].mutantChild(self.mutantFactor))
            else:
                election.append(vType.rand(ncand))
        return election



