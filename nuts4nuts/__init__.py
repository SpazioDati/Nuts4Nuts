# -*- coding: utf-8 -*-
"""
nut4nuts

"""

import logging
from datatxt_querist import DataTXTQuerist
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.structure.modules import SigmoidLayer, LinearLayer
from pybrain.structure import FullConnection
from pybrain.structure.networks import FeedForwardNetwork
from pybrain.tools.xml.networkwriter import NetworkWriter
from pybrain.tools.xml.networkreader import NetworkReader
# from pybrain.structure.connections.connection import Connection
# from pprint import pprint

from abstract import AbstractGetter
from features import PlacesGetter

# globals
INFILE = '../training/samples_training.csv'
INFILETEST = '../test/testset.csv'

# --- root logger
rootlogger = logging.getLogger('nuts4nuts')
rootlogger.setLevel(logging.DEBUG)

logger = logging.getLogger('nuts4nuts.__init__.py')


# utility functions
def read_line(line):
    data = dict()
    line = line.split(',')
    data['line'] = line
    data['page'] = line[0]
    data['option0'] = line[1]
    data['option1'] = line[6]
    datasample = line[2:6]+line[7:11]
    data['sample'] = tuple([float(i) for i in datasample])
    data['target'] = float(line[11])

    return data


def print_data(data):
    print '-----'
    print 'page: ', data['page'], 'sample: ', data['sample']
    print '%s, %s: %s' % (data['option0'], data['option1'], data['target'])
    print


# Nut4Nuts class
class Nuts4Nuts(object):
    LOWER_THRESHOLD = 0.33
    UPPER_THRESHOLD = 0.66
    TRAINER_LEARNINGRATE = 0.02
    TRAINER_LRDECAY = 1.0
    DATATXT_RHO = 0.2
    DATATXT_DBPEDIA = True
    W_PARENT_TYPE = 1
    W_IS_PARENT = 1
    W_HAS_LOCALITY = 1
    BIAS = 0.1

    def __init__(self,
                 datatxt_app_id,
                 datatxt_app_key,
                 lang='it'
                 ):

        #create network and modules
        self.net = FeedForwardNetwork()
        self.inp = LinearLayer(9, name='input')
        self.h1 = LinearLayer(4, name='h1')
        self.h2 = LinearLayer(4, name='h2')
        self.hrho = LinearLayer(1, name='hrho')
        self.hsig = SigmoidLayer(3, name='hsig')
        self.outp = LinearLayer(1, name='output')

        # add modules
        self.net.addOutputModule(self.outp)
        self.net.addInputModule(self.inp)
        self.net.addModule(self.h1)
        self.net.addModule(self.h2)
        self.net.addModule(self.hrho)
        self.net.addModule(self.hsig)

        # create connections
        self.net.addConnection(FullConnection(self.inp, self.h1, name='input->h1'))
        self.net.addConnection(FullConnection(self.inp, self.h2, name='input->h2'))

        # self.net.addConnection(FullConnection(self.inp, self.h1,
        #                                       name='input->h1',
        #                                       inSliceFrom=0,
        #                                       inSliceTo=4))
        # self.net.addConnection(FullConnection(self.inp, self.h2,
        #                                       name='input->h2',
        #                                       inSliceFrom=4,
        #                                       inSliceTo=8))
        self.net.addConnection(FullConnection(self.inp, self.hrho,
                                              name='input->hrho',
                                              inSliceFrom=8,
                                              inSliceTo=9))
        self.net.addConnection(FullConnection(self.h1, self.hsig))
        self.net.addConnection(FullConnection(self.h2, self.hsig))
        self.net.addConnection(FullConnection(self.hrho, self.hsig))
        self.net.addConnection(FullConnection(self.hsig, self.outp))

        # finish up
        self.net.sortModules()

        self.ds = SupervisedDataSet(9, 1)

        self.trainer = BackpropTrainer(self.net, self.ds,
                                       learningrate=self.TRAINER_LEARNINGRATE,
                                       lrdecay=self.TRAINER_LRDECAY)

        self.dq = DataTXTQuerist(app_id=datatxt_app_id,
                                 app_key=datatxt_app_key)

        self.dq.set_params(lang=lang,
                           rho=self.DATATXT_RHO,
                           dbpedia=self.DATATXT_DBPEDIA)

    def _treat_sample(self, sample):
        newsample0 = sample[0:3]
        newsample1 = sample[4:7]
        rho0 = sample[3]
        rho1 = sample[7]

        wsample0 = (self.W_PARENT_TYPE*(newsample0[0]+self.BIAS),
                    self.W_IS_PARENT*(newsample0[1]+self.BIAS),
                    self.W_HAS_LOCALITY*(newsample0[2]+self.BIAS),
                    rho0)

        wsample1 = (self.W_PARENT_TYPE*(newsample1[0]+self.BIAS),
                    self.W_IS_PARENT*(newsample1[1]+self.BIAS),
                    self.W_HAS_LOCALITY*(newsample1[2]+self.BIAS),
                    rho1)

        return wsample0 + wsample1 + tuple([rho0-rho1])

    def add_sample(self, sample, target):
        sample = self._treat_sample(sample)
        self.ds.addSample(sample, target)

    def train(self, nsteps=None):
        if nsteps:
            for _ in range(0, nsteps):
                self.trainer.train()
        else:
            self.trainer.trainUntilConvergence()

    def activate_from_sample(self, sample):
        sample = self._treat_sample(sample)
        return self.net.activate(sample)

    def activate(self, candidate0, candidate1):
        feat0 = candidate0.features.dump_features()
        feat1 = candidate1.features.dump_features()
        return self.activate_from_sample(feat0+feat1)

    def _decide(self, nnres):
        result = None
        if nnres < self.LOWER_THRESHOLD:
            result = 0.0
        elif nnres > self.UPPER_THRESHOLD:
            result = 1.0
        else:
            result = 0.5

        return result

    def _dedup_candidates(self, candidates):
        names = [c.name for c in candidates]
        for name in names:
            dups = [c for c in enumerate(candidates) if c[1].name == name]
            if len(dups) > 1:
                max_feat = max([c[1].features.rho for c in dups])
                dedups = [c for c in dups if c[1].features.rho == max_feat][0]
                for d in dups:
                    if d[0] != dedups[0]:
                        del candidates[d[0]]

        return candidates

    def _calculate_score(self, nnres, result):
        score = 0.0
        if nnres <= 0.5:
            if nnres <= 0.0:
                score = 1.0
            else:
                score = 1.0-nnres/0.5
        else:
            if nnres <= 0.0:
                score = 1.0
            else:
                score = nnres/0.5-1.0

        return score

    def _select_couples(self, couples):
        logger.setLevel(logging.DEBUG)
        logger.debug('call _select_couples')

        winning_candidates = list()
        for c in couples:
            logger.debug('couple: {}'.format(c))
            score = 0

            if c[0].name == c[1].name:
                score = 1.0
                if c[0].features.rho >= c[1].features.rho:
                    c[0].set_score(score)
                    winning_candidates.append(c[0])
                else:
                    c[1].set_score(score)
                    winning_candidates.append(c[1])

            else:
                nnres = self.activate(c[0], c[1])
                result = self._decide(nnres)
                score = self._calculate_score(nnres, result)

                logger.debug('nnres: {nnres}, result: {result}'.format(nnres=nnres,
                                                                       result=result))
                if result != 0.5:
                    result = int(result)
                    c[result].set_score(score)
                    c[result].set_match()
                    winning_candidates.append(c[result])
                else:
                    c[0].set_score(score)
                    c[1].set_score(score)
                    winning_candidates.append(c[0])
                    winning_candidates.append(c[1])

        winning_candidates = self._dedup_candidates(winning_candidates)

        logger.debug('winning_candidates: {}'.format(winning_candidates))
        logger.debug('(deduped) winning_candidates: {}'.format(winning_candidates))

        if len(winning_candidates) == 1:
            winning_candidates[0].set_match()
            winning_candidates = [winning_candidates[0]]
            return winning_candidates

        elif len(winning_candidates) == 2:
            nnres = self.activate(winning_candidates[0], winning_candidates[1])
            result = self._decide(nnres)

            winning_candidates[0].set_score(score)
            winning_candidates[1].set_score(score)

            logger.debug('nnres: {nnres}, result: {result}'.format(nnres=nnres,
                                                                   result=result))

            logger.setLevel(logging.INFO)
            if result != 0.5:
                result = int(result)
                return [winning_candidates[result].set_match()]
            else:
                return winning_candidates
        else:
            winning_couples = [(winning_candidates[i], winning_candidates[i+1])
                               for i in range(0, len(winning_candidates)-1, 2)]

            if (len(winning_candidates) % 2) != 0:
                winning_couples = winning_couples + [(winning_candidates[-2], winning_candidates[-1])]

            logger.debug('winning couples: %s' % winning_couples)

            return self._select_couples(winning_couples)

    def from_candidates(self, candidates):
        logger.debug('candidates: %s' % candidates)
        logger.debug('len(candidates): %s' % len(candidates))

        candidates = self._dedup_candidates(candidates)

        logger.debug('(deduped) candidates: %s' % candidates)
        logger.debug('(deduped) len(candidates): %s' % len(candidates))

        if len(candidates) == 0:
            logger.warning('No candidates found')
            return []

        if len(candidates) == 1:
            candidates[0].set_match()
            return [candidates[0]]

        couples = [(candidates[i], candidates[i+1])
                   for i in range(0, len(candidates)-1, 2)]

        if (len(candidates) % 2) != 0:
            couples = couples + [(candidates[-2], candidates[-1])]

        logger.debug('couples: %s' % couples)

        return self._select_couples(couples)

    def find_municipality(self, page):
        logger.setLevel(logging.INFO)
        ag = AbstractGetter(page)
        self.abstract = ag.get_abstract()
        querytext = self.dq.query(self.abstract)

        # logger.debug(pprint(querytext))

        pg = PlacesGetter(page=page,
                          queryres=querytext)

        self.candidates = pg.get_candidates()

        logger.debug('candidates: {candidates}'.format(candidates=self.candidates))

        return self.from_candidates(candidates=self.candidates)

    def show(self):
        for mod in self.net.modules:
            print "Module: {name} ({mod})".format(name=mod.name, mod=mod)
            if mod.paramdim > 0:
                print "* parameters:", mod.params
            for conn in self.net.connections[mod]:
                print conn
                try:
                    paramdim = len(conn.params)
                except:
                    paramdim = conn.paramdim
                for cc in range(paramdim):
                    print conn.whichBuffers(cc), conn.params[cc]

    def save(self, filename='nut4nutsNN.xml'):
        logger.info('Writing NN to file: {filename}'.format(filename=filename))
        NetworkWriter.writeToFile(self.net, filename)

    def load(self, filename='nut4nutsNN.xml'):
        logger.info('Loading NN from file: {filename}'.format(filename=filename))
        self.net = NetworkReader.readFrom('nut4nutsNN.xml')


if __name__ == "__main__":
    LOGFORMAT_STDOUT = {logging.DEBUG: '%(module)s:%(funcName)s:%(lineno)s - %(levelname)-8s: %(message)s',
                        logging.INFO: '%(levelname)-8s: %(message)s',
                        logging.WARNING: '%(levelname)-8s: %(message)s',
                        logging.ERROR: '%(levelname)-8s: %(message)s',
                        logging.CRITICAL: '%(levelname)-8s: %(message)s'
                        }

    # --- logging ---
    logger = logging.getLogger()
    console = logging.StreamHandler()

    lvl_config_logger = logging.DEBUG

    console.setLevel(lvl_config_logger)

    formatter = logging.Formatter(LOGFORMAT_STDOUT[lvl_config_logger])
    console.setFormatter(formatter)

    logger.addHandler(console)

    logger.setLevel(logging.DEBUG)

    # --- variables ---
    DATATXT_APP_ID = 'ac0d0af0'
    DATATXT_APP_KEY = '27bc8c33b4af532704cd621c9f39f261'

    # --- main ---
    print
    print '== TEST 1 =='

    n4n = Nuts4Nuts(datatxt_app_id=DATATXT_APP_ID,
                    datatxt_app_key=DATATXT_APP_KEY)

    n4n.load()

    print "Find the municipality for: 'Chiesa di San Terenzio'"
    print n4n.find_municipality('Chiesa_di_San_Terenzio')
    print
    print "Find the municipality for: 'Grattacielo Pirelli'"
    print n4n.find_municipality('Grattacielo_Pirelli')
    print
    print "Find the municipality for: 'Parco Sempione (Milano)'"
    print n4n.find_municipality("Parco Sempione (Milano)")
    print
    print "Find the municipality for: 'asfjviolvj' (non-existing page)"
    print n4n.find_municipality("asfjviolvj")
    print

    exit(0)
