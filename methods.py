
from mydecorators import autoassign, cached_property, setdefaultattr
import random
from numpy.lib.scimath import sqrt
from numpy.core.fromnumeric import mean, std
from numpy.lib.function_base import median
from numpy.ma.core import floor
from test.test_binop import isnum
from debugDump import *

from stratFunctions import *
from dataClasses import *

####EMs themeselves
class Plurality(Method):
    
    #>>> pqs = [Plurality().resultsFor(PolyaModel()(101,5),Plurality.honBallot)[0] for i in range(400)]
    #>>> mean(pqs)
    #0.20534653465346522
    #>>> std(pqs)
    #0.2157069704671751
    bias = 0.2157069704671751
    
    candScore = staticmethod(mean)
    
    @staticmethod
    def oneVote(utils, forWhom):
        ballot = [0] * len(utils)
        ballot[forWhom] = 1
        return ballot
    
    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, utils):
        """Takes utilities and returns an honest ballot
        
        >>> Plurality.honBallot(Plurality, Voter([-3,-2,-1]))
        [0, 0, 1]
        >>> Plurality().stratBallotFor([3,2,1])(Plurality, Voter([-3,-2,-1]))
        [0, 1, 0]
        """
        return cls.oneVote(utils, cls.winner(utils))
    
    def stratBallotFor(self, info):
        """Returns a (function which takes utilities and returns a strategic ballot)
        for the given "polling" info.
        
        >>> Plurality().stratBallotFor([3,2,1])(Plurality, Voter([-3,-2,-1]))
        [0, 1, 0]
        """ 
        
        places = sorted(enumerate(info),key=lambda x:-x[1]) #from high to low
        #print("placesxx",places)
        @rememberBallots
        def stratBallot(cls, voter):
            
            stratGap = voter[places[1][0]] - voter[places[0][0]]
            if stratGap <= 0:
                #winner is preferred; be complacent.
                isStrat = False
                strat = cls.oneVote(voter, places[0][0])
            else:
                #runner-up is preferred; be strategic in iss run
                isStrat = True
                #sort cuts high to low
                #cuts = (cuts[1], cuts[0])
                strat = cls.oneVote(voter, places[1][0])
            return dict(strat=strat, isStrat=isStrat, stratGap=stratGap)
        return stratBallot

class Score(Method): 
    """Score voting, 0-10.
    
    
    Strategy establishes pivots
        >>> Score().stratBallotFor([0,1,2])(Score, Voter([5,6,7]))
        [0, 0, 10]
        >>> Score().stratBallotFor([2,1,0])(Score, Voter([5,6,7]))
        [0, 10, 10]
        >>> Score().stratBallotFor([1,0,2])(Score, Voter([5,6,7]))
        [0, 5.0, 10]
        
    Strategy (kinda) works for ties
        >>> Score().stratBallotFor([1,0,2])(Score, Voter([5,6,6]))
        [0, 10, 10]
        >>> Score().stratBallotFor([1,0,2])(Score, Voter([6,6,7]))
        [0, 0, 10]
        >>> Score().stratBallotFor([1,0,2])(Score, Voter([6,7,6]))
        [10, 10, 10]
        >>> Score().stratBallotFor([1,0,2])(Score, Voter([6,5,6]))
        [10, 0, 10]

    """
    
    #>>> qs += [Score().resultsFor(PolyaModel()(101,2),Score.honBallot)[0] for i in range(800)]
    #>>> std(qs)
    #2.770135393419682
    #>>> mean(qs)
    #5.1467202970297032
    bias2 = 2.770135393419682
    #>>> qs5 = [Score().resultsFor(PolyaModel()(101,5),Score.honBallot)[0] for i in range(400)]
    #>>> mean(qs5)
    #4.920247524752476
    #>>> std(qs5)
    #2.3536762480634343
    bias5 = 2.3536762480634343
    
    candScore = staticmethod(mean)
        #"""Takes the list of votes for a candidate; returns the candidate's score."""

    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, utils):
        """Takes utilities and returns an honest ballot (on 0..10)
        
        
        honest ballots work as expected
            >>> Score().honBallot(Score, Voter([5,6,7]))
            [0.0, 5.0, 10.0]
            >>> Score().resultsFor(DeterministicModel(3)(5,3),Score().honBallot)
            [4.0, 6.0, 5.0]
        """
        bot = min(utils)
        scale = max(utils)-bot
        return [floor(10.99 * (util-bot) / scale) for util in utils]
    
    def stratBallotFor(self, info):
        """Returns a (function which takes utilities and returns a strategic ballot)
        for the given "polling" info.""" 
        
        places = sorted(enumerate(info),key=lambda x:-x[1]) #from high to low
        #print("placesxx",places)
        @rememberBallots
        def stratBallot(cls, voter):
            cuts = [voter[places[0][0]], voter[places[1][0]]]
            stratGap = cuts[1] - cuts[0]
            if stratGap <= 0:
                #winner is preferred; be complacent.
                isStrat = False
            else:
                #runner-up is preferred; be strategic in iss run
                isStrat = True
                #sort cuts high to low
                cuts = (cuts[1], cuts[0])
            if cuts[0] == cuts[1]:
                strat = [(10 if (util >= cuts[0]) else 0) for util in voter]
            else:
                strat = [max(0,min(10,floor(
                                10.99 * (util-cuts[1]) / (cuts[0]-cuts[1])
                            ))) 
                        for util in voter]
            return dict(strat=strat, isStrat=isStrat, stratGap=stratGap)
        return stratBallot
    
    

def toVote(cutoffs, util):
    """maps one util to a vote, using cutoffs.
    
    Used by Mav, but declared outside to avoid method binding overhead."""
    for vote in range(len(cutoffs)):
        if util <= cutoffs[vote]:
            return vote
    return vote + 1
    

class Mav(Method):
    """Majority Approval Voting
    """
    
    
    #>>> mqs = [Mav().resultsFor(PolyaModel()(101,5),Mav.honBallot)[0] for i in range(400)]
    #>>> mean(mqs)
    #1.5360519801980208
    #>>> mqs += [Mav().resultsFor(PolyaModel()(101,5),Mav.honBallot)[0] for i in range(1200)]
    #>>> mean(mqs)
    #1.5343069306930679
    #>>> std(mqs)
    #1.0970202515275356
    bias5 = 1.0970202515275356

    
    baseCuts = [-0.8, 0, 0.8, 1.6]
    def candScore(self, scores):
        """For now, only works correctly for odd nvot
        
        Basic tests
            >>> Mav().candScore([1,2,3,4,5])
            3.0
            >>> Mav().candScore([1,2,3,3,3])
            2.5
            >>> Mav().candScore([1,2,3,4])
            2.5
            >>> Mav().candScore([1,2,3,3])
            2.5
            >>> Mav().candScore([1,2,2,2])
            1.5
            >>> Mav().candScore([1,2,3,3,5])
            2.7
            """
        scores = sorted(scores)
        nvot = len(scores)
        nGrades = (len(self.baseCuts) + 1)
        i = int((nvot - 1) / 2)
        base = scores[i]
        while (i < nvot and scores[i] == base):
            i += 1
        upper =  (base + 0.5) - (i - nvot/2) * nGrades / nvot
        lower = (base) - (i - nvot/2) / nvot
        return max(upper, lower)
    
    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, voter):
        """Takes utilities and returns an honest ballot (on 0..4)

        honest ballot works as intended, gives highest grade to highest utility:
            >>> Mav().honBallot(Mav, Voter([-1,-0.5,0.5,1,1.1]))
            3
            [0, 1, 2, 3, 4]
            
        Even if they don't rate at least an honest "B":
            >>> Mav().honBallot(Mav, Voter([-1,-0.5,0.5]))
            [0, 1, 4]
        """
        cutoffs = [min(cut, max(voter) - 0.001) for cut in cls.baseCuts]
        return [toVote(cutoffs, util) for util in voter]
        
    
    def stratBallotFor(self, info):
        """Returns a function which takes utilities and returns a dict(
            strat=<ballot in which all grades are exaggerated 
                             to outside the range of the two honest frontrunners>,
            extraStrat=<ballot in which all grades are exaggerated to extremes>,
            isStrat=<whether the runner-up is preferred to the frontrunner (for reluctantStrat)>,
            stratGap=<utility of runner-up minus that of frontrunner>
            )
        for the given "polling" info.
        
        
        
        Strategic tests:
            >>> Mav().stratBallotFor([0,1.1,1.9,0,0])(Mav, Voter([-1,-0.5,0.5,1,2]))
            [0, 1, 2, 3, 4]
            >>> Mav().stratBallotFor([0,2.1,2.9,0,0])(Mav, Voter([-1,-0.5,0.5,1,2]))
            [0, 1, 3, 3, 4]
            >>> Mav().stratBallotFor([0,2.1,1.9,0,0])(Mav, Voter([-1,0.4,0.5,1,2]))
            [0, 1, 3, 3, 4]
            >>> Mav().stratBallotFor([1,0,2])(Mav, Voter([6,7,6]))
            [4, 4, 4]
            >>> Mav().stratBallotFor([1,0,2])(Mav, Voter([6,5,6]))
            [4, 0, 4]
            >>> Mav().stratBallotFor([2.1,0,3])(Mav, Voter([6,5,6]))
            [4, 0, 4]
            >>> Mav().stratBallotFor([2.1,0,3])(Mav, Voter([6,5,6.1]))
            [2, 2, 4]
        """ 
        places = sorted(enumerate(info),key=lambda x:-x[1]) #from high to low
        #print("places",places)
        front = (places[0][0], places[1][0], places[0][1], places[1][1])
        
        @rememberBallots
        def stratBallot(cls, voter):
            frontUtils = [voter[front[0]], voter[front[1]]] #utils of frontrunners
            stratGap = frontUtils[1] - frontUtils[0]
            if stratGap is 0:
                strat = extraStrat = [(4 if (util >= frontUtils[0]) else 0)
                                     for util in voter]
                isStrat = True
                
            else:
                if stratGap < 0:
                    #winner is preferred; be complacent.
                    isStrat = False
                else:
                    #runner-up is preferred; be strategic in iss run
                    isStrat = True
                    #sort cuts high to low
                    frontUtils = (frontUtils[1], frontUtils[0])
                top = max(voter)
                cutoffs = [(  (min(frontUtils[0], self.baseCuts[i])) 
                                 if (i < floor(front[3])) else 
                            ( (frontUtils[1]) 
                                 if (i < floor(front[2]) + 1) else
                              min(top, self.baseCuts[i])
                              ))
                           for i in range(4)]
                strat = [toVote(cutoffs, util) for util in voter]
                extraStrat = [max(0,min(10,floor(
                                4.99 * (util-frontUtils[1]) / (frontUtils[0]-frontUtils[1])
                            ))) 
                        for util in voter]
            return dict(strat=strat, extraStrat=extraStrat, isStrat=isStrat,
                        stratGap = stratGap)
        return stratBallot
        
        
class Mj(Mav):
    def candScore(self, scores):
        """This formula will always give numbers within 0.5 of the raw median.
        Unfortunately, with 5 grade levels, these will tend to be within 0.1 of
        the raw median, leaving scores further from the integers mostly unused.
        This is only a problem aesthetically.
        
        For now, only works correctly for odd nvot
        
        tests:
            >>> Mj().candScore([1,2,3,4,5])
            3
            >>> Mj().candScore([1,2,3,3,5])
            2.7
            >>> Mj().candScore([1,3,3,3,5])
            3
            >>> Mj().candScore([1,3,3,4,5])
            3.3
            >>> Mj().candScore([1,3,3,3,3])
            2.9
            >>> Mj().candScore([3] * 24 + [1])
            2.98
            >>> Mj().candScore([3] * 24 + [4])
            3.02
            >>> Mj().candScore([3] * 13 + [4] * 12)
            3.46
            """
        scores = sorted(scores)
        nvot = len(scores)
        lo = hi = mid = nvot // 2
        base = scores[mid]
        while (hi < nvot and scores[hi] == base):
            hi += 1
        while (lo >= 0 and scores[lo] == base):
            lo -= 1
            
        if (hi-mid) == (mid-lo):
            return base
        elif (hi-mid) < (mid-lo):
            return base + 0.5 - (hi-mid) / nvot
        else:
            return base - 0.5 + (mid-lo) / nvot
        
class Irv(Method):
    
    #>>> iqs = [Irv().resultsFor(PolyaModel()(101,5),Irv.honBallot)[0] for i in range(400)]
    #>>> mean(iqs)
    #1.925
    #>>> std(iqs)
    #1.4175242502334846
    bias5 = 1.4175242502334846

    def resort(self, ballots, loser, ncand, piles):
        """No error checking; only works for exhaustive ratings."""
        #print("resort",ballots, loser, ncand)
        #print(piles)
        for ballot in ballots:
            if loser < 0:
                nextrank = ncand - 1
            else:
                nextrank = ballot[loser] - 1
            while 1:
                try:
                    piles[ballot.index(nextrank)].append(ballot)
                    break
                except AttributeError:
                    nextrank -= 1
                    if nextrank < 0:
                        raise
            
    def results(self, ballots):
        """IRV results.
        
        >>> Irv().resultsFor(DeterministicModel(3)(5,3),Irv().honBallot)[0]
        [0, 1, 2]
        >>> Irv().results([[0,1,2]])[2]
        2
        >>> Irv().results([[0,1,2],[2,1,0]])[1]
        0
        >>> Irv().results([[0,1,2]] * 4 + [[2,1,0]] * 3 + [[1,2,0]] * 2)
        [2, 0, 1]
        """
        if type(ballots) is not list:
            ballots = list(ballots)
        ncand = len(ballots[0])
        results = [-1] * ncand
        piles = [[] for i in range(ncand)]
        loserpile = ballots
        loser = -1
        for i in range(ncand):
            self.resort(loserpile, loser, ncand, piles)
            negscores = ["x" if isnum(pile) else -len(pile)
                         for pile in piles]
            loser = self.winner(negscores)
            results[loser] = i 
            loserpile, piles[loser] = piles[loser], -1
        return results
        
            
    @staticmethod #cls is provided explicitly, not through binding
    @rememberBallot
    def honBallot(cls, voter):
        """Takes utilities and returns an honest ballot
        
        >>> Irv.honBallot(Irv,Voter([4,1,6,3]))
        [2, 0, 3, 1]
        """
        ballot = [-1] * len(voter)
        order = sorted(enumerate(voter), key=lambda x:x[1])
        for i, cand in enumerate(order):
            ballot[cand[0]] = i
        return ballot
        
    
    def stratBallotFor(self, info):
        """Returns a function which takes utilities and returns a dict(
            isStrat=
        for the given "polling" info.
        
        
        >>> Irv().stratBallotFor([3,2,1,0])(Irv,Voter([3,6,5,2]))
        [1, 2, 3, 0]
        """ 
        ncand = len(info)
        
        places = sorted(enumerate(info),key=lambda x:-x[1]) #high to low
        @rememberBallots
        def stratBallot(cls, voter):
            stratGap = voter[places[1][0]] - voter[places[0][0]]
            if stratGap < 0:
                #winner is preferred; be complacent.
                isStrat = False
            else:
                #runner-up is preferred; be strategic in iss run
                isStrat = True
                #sort cuts high to low #NOT FOR IRV
                #places = (places[1], places[0])
            i = ncand - 1
            winnerQ = voter[places[0][0]]
            ballot = [-1] * len(voter)
            for nextLoser, loserScore in places[::-1][:-1]:
                if voter[nextLoser] > winnerQ:
                    ballot[nextLoser] = i
                    i -= 1
            ballot[places[0][0]] = i
            i -= 1
            for nextLoser, loserScore in places[1:]:
                if voter[nextLoser] <= winnerQ:
                    ballot[nextLoser] = i
                    i -= 1
            assert(i == -1)
            return dict(strat=ballot, isStrat=isStrat, stratGap=stratGap)
        return stratBallot
        
        
        
        