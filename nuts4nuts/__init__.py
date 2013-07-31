# -*- coding: utf-8 -*-
"""
nut4nuts

"""

import logging
from itertools import combinations
from collections import defaultdict
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
from template import TemplateAnalyzer

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
    SCORE_WEIGHT_NN = 0.66
    SCORE_WEIGHT_TEMPLATES = 0.7
    SET_MATCH_THRESHOLD = 0.6

    def __init__(self,
                 datatxt_app_id,
                 datatxt_app_key,
                 lang='it'
                 ):

        self.lang = lang

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
            result = 0
        elif nnres > self.UPPER_THRESHOLD:
            result = 1

        return result

    def _dedup_candidates(self, candidates):
        names = [c.name for c in candidates]
        for name in names:
            dups = [c for c in enumerate(candidates) if c[1].name == name]
            if len(dups) > 1:
                max_feat = max([c[1].features.rho for c in dups])
                dedups = [c for c in dups if c[1].features.rho == max_feat][0]
                dups.reverse()
                for d in dups:
                    if d[0] != dedups[0]:
                        del candidates[d[0]]

        return candidates

    def _select_couples(self, candidates):
        logger.setLevel(logging.DEBUG)
        logger.debug('call _select_couples')

        winning_candidates = defaultdict(int)
        for c in combinations(candidates, 2):
            nnres = self.activate(c[0], c[1])
            result = self._decide(nnres)
            logger.debug('couple: (cand0: {cand0}, cand1: {cand1}), nnres: {nnres}'.format(
                         cand0=c[0],
                         cand1=c[1],
                         nnres=nnres))
            if result is not None:
                winning_candidates[c[result]] += 1

        logger.debug(winning_candidates)
        for cand in candidates:
            cand.score = winning_candidates[cand]/float(len(candidates))

        max_score = max(cand.score for cand in candidates)

        selected_places = [c for c in candidates if c.score >= max_score]

        return selected_places

    def _lau3_from_lau2(self, candidates):
        lau2 = [c for c in candidates if c.type == '/LAU2']
        lau3 = [c for c in candidates if c.type == '/LAU3']

        logger.debug(lau2)
        logger.debug(lau3)

        winning_lau3s = list()

        for cand in lau3:
            lau3_fathers = [father for father in lau2 if father.name in cand.fathers]
            if len(lau3_fathers) == 1:
                winning_lau3s.append((cand, lau3_fathers[0]))

        # logger.debug(winning_lau3s)
        if len(winning_lau3s) == 1:
            winning_lau3s[0][0].score = 1.0
            return [winning_lau3s[0][0]]
        elif len(winning_lau3s) > 1:
            if len(frozenset(father for lau3, father in winning_lau3s)) == 1:
                winning_lau3s[0][1].score = 1.0
                return [winning_lau3s[0][1]]

        return winning_lau3s


    def from_candidates(self, candidates):
        logger.debug('candidates: %s' % candidates)
        logger.debug('len(candidates): %s' % len(candidates))

        candidates = self._dedup_candidates(candidates)

        logger.debug('(deduped) candidates: %s' % candidates)
        logger.debug('(deduped) len(candidates): %s' % len(candidates))

        if len(candidates) == 0:
            logger.debug('No candidates found')
            return candidates

        if len(candidates) == 1:
            candidates[0].score = 1.0
            return candidates

        winning_lau3s = self._lau3_from_lau2(candidates)
        if winning_lau3s:
            return winning_lau3s

        return self._select_couples(candidates)

    def find_municipality(self, page):
        ta = TemplateAnalyzer(page=page, lang=self.lang)
        candidates_from_templates = ta.analyze_templates()

        logger.debug('candidates from templates: {candidates}'.format(
                     candidates=candidates_from_templates))

        ag = AbstractGetter(page=page, lang=self.lang)
        self.abstract = ag.get_abstract()
        querytext = self.dq.query(self.abstract)

        pg = PlacesGetter(page=page,
                          queryres=querytext)


        candidates_for_nn = pg.get_candidates()

        logger.debug('candidates: {candidates}'.format(candidates=candidates_for_nn))

        common_candidates = set([c.name for c in candidates_from_templates]).intersection(
                                 set([c.name for c in candidates_for_nn])
                                 )

        logger.debug(common_candidates)
        if common_candidates:
            result = [c
                      for c in candidates_from_templates
                      for name in common_candidates
                      if c.name == name
                      ]

            if len(result) == 1:
                result[0].set_match()
                result[0].score = 1.0

            return result

        else:
            candidates_from_nn = self.from_candidates(candidates=candidates_for_nn)

            for c in candidates_from_nn:
                c.score = c.score*self.SCORE_WEIGHT_NN

            for c in candidates_from_templates:
                c.score = c.score*self.SCORE_WEIGHT_TEMPLATES

            candidates_from_templates = self._lau3_from_lau2(candidates_from_templates) or \
                                        candidates_from_templates

            logger.debug(candidates_from_templates)
            logger.debug(candidates_from_nn)
            if candidates_from_templates and candidates_from_nn:
                total_candidates = self._lau3_from_lau2(
                    candidates_from_nn + candidates_from_templates)
                if len(total_candidates) == 1:
                    total_candidates[0].set_match()
                return total_candidates
            else:
                if candidates_from_templates:
                    if len(candidates_from_templates) == 1 and \
                       candidates_from_templates[0].score > self.SET_MATCH_THRESHOLD:
                       candidates_from_templates[0].set_match()
                    return candidates_from_templates

                else:
                    if len(candidates_from_nn) == 1 and \
                       candidates_from_nn[0].score > self.SET_MATCH_THRESHOLD:
                       candidates_from_nn[0].set_match()
                    return candidates_from_nn

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
        self.net = NetworkReader.readFrom(filename)


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

    logger.setLevel(logging.INFO)

    try:
        infile = open('../../datatxt-credentials.txt', 'r+')
    except:
        logger.error("Can not find DataTXT credentials. Goodbye!")
        exit(0)

    credentials = [line.strip() for line in infile.readlines()]

    # --- variables ---
    DATATXT_APP_ID = credentials[0]
    DATATXT_APP_KEY = credentials[1]

    # --- main ---
    print
    print '== TEST 1 =='

    n4n = Nuts4Nuts(datatxt_app_id=DATATXT_APP_ID,
                    datatxt_app_key=DATATXT_APP_KEY)

    n4n.load()

    # print "Find the municipality for: 'Chiesa di San Terenzio'"
    # print n4n.find_municipality('Chiesa_di_San_Terenzio')
    # print '----------'
    # print
    # print
    # print "Find the municipality for: 'Grattacielo Pirelli'"
    # print n4n.find_municipality('Grattacielo_Pirelli')
    # print '----------'
    # print
    # print
    # print "Find the municipality for: 'Parco Sempione (Milano)'"
    # print n4n.find_municipality("Parco Sempione (Milano)")
    # print '----------'
    # print
    # print
    # print "Find the municipality for: 'asfjviolvj' (non-existing page)"
    # print n4n.find_municipality("asfjviolvj")
    # print '----------'
    # print
    # print
    # print "Find the municipality for: 'Santuario_di_Pietralba'"
    # print n4n.find_municipality("Santuario_di_Pietralba")
    # print '----------'
    # print
    # print
    # print "Find the municipality for: 'Monte Calisio'"
    # print n4n.find_municipality("Monte Calisio")
    # print '----------'
    # print
    # print
    # print "Find the municipality for: 'Abbazia_di_Santa_Croce_al_Chienti'"
    # print n4n.find_municipality("Abbazia_di_Santa_Croce_al_Chienti")
    # print '----------'
    # print
    # print
    # print "Find the municipality for: 'Palazzo Vecchio'"
    # print n4n.find_municipality("Palazzo Vecchio")
    # print '----------'
    # print
    print
    print "Find the municipality for: 'Montonate'"
    print n4n.find_municipality("Montonate")
    print '----------'
    print
    print
    print "Find the municipality for: 'Museo del Risorgimento (Castelfidardo)'"
    print n4n.find_municipality("Museo del Risorgimento (Castelfidardo)")
    print '----------'
    print
    print
    print "Find the municipality for: 'Castel_San_Felice_(Sant'Anatolia_di_Narco)'"
    print n4n.find_municipality("Castel_San_Felice_(Sant'Anatolia_di_Narco)")
    print '----------'
    print

    exit(0)
