#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import wikipedia_template_parser as wtp

from nuts import NutsRecon
from places import Place, ALLOWEDTYPES

# globals
TEMPLATES_TO_ANALYZE_IT = {
    u'edificio_religioso': [u'città'],
    u'rifugio': [u'localita'],
    u'edificio_civile': [u'città', u'cittàlink'],
    u'area_protetta': [u'comuni']
}

NR = NutsRecon()

# logging
logger = logging.getLogger('nuts4nuts.template')


class TemplateAnalyzer(object):

    def __init__(self, lang='it'):
        self.abstract = None
        self.lang = lang

    def _treat(self, name):
        if isinstance(name, unicode):
            return name.lower().replace(' ', '_')
        if isinstance(name, str):
            return name.lower().replace(' ', '_').decode()

    def _normalize(name):
        if 'http:':
            return name.lower().replace(' ', '_')
        if isinstance(name, str):
            return name.lower().replace(' ', '_').decode()

    def analyze_templates(self, page):
        logger.debug(page)
        finalplaces = list()
        types = list()
        try:
            templates = wtp.data_from_templates(page, self.lang)
        except ValueError:
            templates = []

        logger.debug(templates)

        for t in templates:
            name = self._treat(t['name'])
            if name in TEMPLATES_TO_ANALYZE_IT.keys():
                attributes = TEMPLATES_TO_ANALYZE_IT[name]
                tdata = {self._treat(k): v for k, v in t['data'].iteritems()}
                locations = [tdata[attr] for attr in attributes if tdata[attr] != '']
                for place in locations:
                    reconres = NR.query(query=place)
                    for r in reconres:
                        # logger.debug('place: name={name}, r={r}'.format(name=place['name'], r=r))
                        types.append((r['type'][0]['id'], r['id']))

                    logger.debug('place: name={name}, types={types}'.format(
                                 name=place,
                                 types=types))

                    if set(lau for lau, id_ in types).intersection(ALLOWEDTYPES):
                        place = Place(name=place)
                        place_type = place.set_type_from_candidates(types)
                        place.set_id_from_candidates(types, place_type)
                        finalplaces.append(place)

        return finalplaces


if __name__ == '__main__':
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

    ta = TemplateAnalyzer(lang='it')
    print
    print ta.analyze_templates('Duomo_di_Milano')
    print
    print
    print ta.analyze_templates('Grattacielo Pirelli')
    print
    print ta.analyze_templates('Palazzo Vecchio')
    print
    print ta.analyze_templates('akfjkldsghjahgn')
