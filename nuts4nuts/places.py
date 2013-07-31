#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging

# logging
logger = logging.getLogger('nuts4nuts.places')

# globals
ALLOWEDTYPES = set([u'/LAU2', u'/LAU3'])


class PlaceCandidate(object):

    def __init__(self, name, id=None, type=None, fathers=[]):
        self.name = name
        self.id = id
        self.type = type
        self.fathers = fathers
        self.score = 0.0
        self.match = False

    def set_type_from_candidates(self, place_candidates):
        types = set(type_ for type_, id_ in place_candidates)
        if '/LAU2' in types:
            place_type = '/LAU2'
        else:
            place_type = '/LAU3'

        self.type = place_type
        return self.type

    def set_id_from_candidates(self, place_candidates, place_type):
        logger.debug(place_candidates)
        logger.debug(place_type)
        self.id = [id_ for type_, id_ in place_candidates if type_ == place_type][0]

    def set_match(self):
        self.match = True

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return 'PlaceCandidate<(name={name}, score={score}, match={match}, type={type}, fathers={fathers})>'.format(
               name=repr(self.name),
               score=repr(self.score),
               match=repr(self.match),
               type=repr(self.type),
               fathers=repr(self.fathers))


class PlaceCandidateWithFeatures(PlaceCandidate):

    def __init__(self, name, id, type, fathers, features):
        super(PlaceCandidateWithFeatures, self).__init__(name, id, type, fathers)
        self.features = features

    def __repr__(self):
        return 'PlaceCandidateWithFeatures<(name={name}, score={score}, match={match}, type={type}, features={features}, fathers={fathers})>'.format(
               name=repr(self.name),
               score=repr(self.score),
               match=repr(self.match),
               type=repr(self.type),
               features=repr(self.features),
               fathers=repr(self.fathers))


if __name__ == "__main__":
    print
    print
