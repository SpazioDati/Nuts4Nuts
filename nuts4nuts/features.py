#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import urllib
import requests
import re
import codecs

from pprint import pprint

# globals
PLACETYPES = set([u'http://dbpedia.org/ontology/PopulatedPlace',
                  u'http://dbpedia.org/ontology/Place',
                  u'http://schema.org/Place'
                  ])

PARENTTYPES = set([u'/NUTS3',
                   u'/NUT2',
                   u'/NUTS1',
                   u'/NUTS0'
                   ])

ALLOWEDTYPES = set([u'/LAU2', u'/LAU3'])

PARENTHESIS = re.compile('\(.*\)')

SAMPLE_LENGHT = 9


# NUTS recon
class NutsRecon():
    '''
    Query the NUTS reconciliation service:
        http://nuts.spaziodati.eu/
    '''

    def __init__(self):
        self.RECONCILE_URL = 'http://nuts.spaziodati.eu/reconcile'
        self.SUGGEST_URL = 'http://nuts.spaziodati.eu/suggest'

    def query(self, query):
        request = json.dumps({
            'q0': {'query': query}})
        return requests.get(self.RECONCILE_URL, params={'queries': request}).json()['q0']['result']


# features
class FeatureList():
    '''
    List of features for the Neural Network
    '''

    def __init__(self):
        self.hasParentType = False
        self.isParent = False
        self.hasLocality = False
        self.rho = 0
        self.feats = [0, 0, 0, 0]
        self.featsdict = dict()

    def dump_features(self):
        self.feats[0] = int(self.hasParentType)
        self.feats[1] = int(self.isParent)
        self.feats[2] = int(self.hasLocality)
        self.feats[3] = self.rho

        #print 'feats: ', self.feats
        return self.feats

    def get_features(self):
        self.featsdict['hasParentType'] = self.hasParentType
        self.featsdict['isParent'] = self.isParent
        self.featsdict['hasLocality'] = self.hasLocality
        self.featsdict['rho'] = self.rho

        return self.featsdict

    def dict2list(self):
        self.feats[0] = int(self.featsdict['hasParentType'])
        self.feats[1] = int(self.featsdict['isParent'])
        self.feats[2] = int(self.featsdict['hasLocality'])
        self.feats[3] = self.featsdict['rho']

        return self.feats

    def __repr__(self):
        return 'FeatureList<({hasParentType},{isParent},{hasLocality},{rho})>'.format(
               hasParentType=self.hasParentType,
               isParent=self.isParent,
               hasLocality=self.hasLocality,
               rho=self.rho)


class FeatureExtractor(object):
    """
    Extracts the features from a given set of places
    """

    def __init__(self, place, otherplaces):
        self.place = place
        self.name = place['name']
        self.features = FeatureList()
        self.otherplaces = otherplaces
        self._set_feats()

    def _set_feats(self):
        for type_ in self.place['types']:
            if type_ in PARENTTYPES:
                self.features.hasParentType = True

        for op in self.otherplaces:
            if self.name in op['fathers']:
                self.features.isParent = True

        self.features.rho = self.place['rho']

        if self.place.get('localityname', None) is not None:
            if self.place['localityname'] == self.name:
                self.features.hasLocality = True

    def get_features(self):
        return self.features.get_features()

    def dump_features(self):
        return self.features.dump_features()


class PlaceCandidate(object):

    def __init__(self, name, features):
        self.name = name
        self.features = features
        self.score = None
        self.match = False

    @property
    def id(self):
        return self.name

    def set_score(self, score):
        self.score = score

    def set_match(self):
        self.match = True

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return 'PlaceCandidate<(name={name}, features={features})>'.format(
               name=repr(self.name), features=repr(self.features))


class PlacesGetter():
    '''
    Write features on a file
    '''

    def __init__(self, page, queryres):
        self.page = codecs.encode(page, 'utf-8')
        self.cleanpage = urllib.unquote(self.page)
        self.queryres = queryres
        self.features = self.extract_types()

        self.finalplaces = list()
        self.nr = NutsRecon()

        self.localityname = None
        match = PARENTHESIS.search(self.cleanpage)
        if match:
            self.localityname = match.group(0).strip('(').strip(')')

    def extract_types(self):
        self.features = list()
        annotations = list()
        try:
            annotations = self.queryres['annotations']
        except:
            pass
        for an in annotations:
            isPlace = False
            for t in an['type']:
                if t in PLACETYPES:
                    isPlace = True
            if isPlace:
                self.features.append({'name': an['title'],
                                      'rho': an['rho']
                                      })
        return self.features

    def get_finalplaces(self):
        for place in self.features:
            place['localityname'] = self.localityname or ''
            place['fathers'] = list()
            place['types'] = list()
            reconres = self.nr.query(query=place['name'])

            for r in reconres:
                place['fathers'].append(r['name'].split('->')[0])
                place['types'].append(r['type'][0]['id'])

            placenamematch = PARENTHESIS.search(place['name'])
            if placenamematch:
                place['name'] = PARENTHESIS.sub('', place['name']).strip()

            if set(place['types']).intersection(ALLOWEDTYPES):
                self.finalplaces.append(place)

        return self.finalplaces

    def get_candidates(self):

        self.candidates = list()

        if not self.finalplaces:
            self.get_finalplaces()

        for place in self.finalplaces:

            otherplaces = self.finalplaces[:]
            otherplaces.remove(place)
            fe = FeatureExtractor(place, otherplaces)

            candidate = PlaceCandidate(place['name'], fe.features)

            self.candidates.append(candidate)

        return self.candidates

    def write_to_file(self, outfile):
        if not self.candidates:
            self.get_finalplaces()

        printlist = list()
        printlist.append(self.page)
        i = 1

        for place in self.finalplaces:
            otherplaces = self.finalplaces[:]
            otherplaces.remove(place)
            fe = FeatureExtractor(place, otherplaces)
            if i == 1:
                features1 = fe.dump_features()

            if i > 2:
                outfile.write(','.join(printlist)+'\n')
                printlist = list()
                printlist.append(self.page)
                printlist.append(self.finalplaces[0]['name'].strip())
                printlist += [codecs.encode(str(x), 'utf-8') for x in features1]

            i += 1

            printlist.append(place['name'].strip())
            printlist += [str(x) for x in fe.dump_features()]

            print 'printlist: ', printlist
            if len(printlist) < SAMPLE_LENGHT:
                print 'continuing'
                continue

            if all(i == '' for i in printlist):
                continue
            outfile.write(','.join(printlist)+'\n')
            print ','.join(printlist)

if __name__ == "__main__":
    from datasets.testset import TEST

    outfile = codecs.open('butta.csv', 'w+', 'utf-8')

    for tr in TEST:
        print '-----'
        print 'page: %s' % tr[0]
        print '-----'

        pg = PlacesGetter(tr)
        finalplaces = pg.get_finalplaces()
        print '-----'
        print 'types: ', pg.extract_types()
        print 'finalplaces:', finalplaces

        print 'candidates: ', pg.get_candidates()

    outfile.close()
