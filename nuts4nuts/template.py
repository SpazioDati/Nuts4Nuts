#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import wikipedia_template_parser as wtp

from nuts import NutsRecon
from places import PlaceCandidate, ALLOWEDTYPES

# globals
TEMPLATES_TO_ANALYZE_IT = {
    u'impianto_sportivo': [u'locazione'],
    u'squadra_di_pallacanestro': [u'città'],
    u'squadra_di_calcio': [u'città'],
    u'squadra_di_pallavolo': [u'città'],
    u'teatro': [u'città'],
    u'festival_musicale': [u'sede'],
    u'azienda': [u'sede'],  # deve essere strippato, può esserci l'indirizzo completo
    u'massa_d\'acqua': [u'div_amm_3'],  # possono essere più di una
    u'stazione_metereologica': [u'div_amm_3', u'div_amm_4', u'div_amm_5'],
    u'infobox_aeroporto': [u'città'],
    u'quartiere': [u'nomecomune'],
    u'infobox_incidente_aereo': [u'luogo'],  # potrebbe essere del tutto generico
    u'infobox_stazione_della_metropolitana': [u'città'],
    u'infobox_stazione_ferroviaria': [u'localizzazione'],
    u'valle': [u'comuni'],
    u'sito_archeologico': [u'suddivisione3'],
    u'parco_divertimenti': [u'località'],
    u'infobox_conflitto': [u'luogo'],  # può essere generale come "Francia" o "Mondiale"
    u'concorso_di_bellezza': [u'sede'],
    u'incidente': [u'luogo'],
    u'ospedale': [u'comune'],
    u'valico': [u'div_amm_3'],
    u'trampolino': [u'località'],
    u'biblioteca': [u'città'],
    u'percorso_escursionistico': ['div_amm_3'],
    u'opera_d\'arte': [u'città'],
    u'edificio_religioso': [u'città'],
    u'rifugio': [u'localita'],
    u'edificio_civile': [u'città', u'cittàlink'],
    u'area_protetta': [u'comuni'],
    u'divisione_amministrativa': [u'nome'],
    u'parco': [u'città'],
    u'museo': [u'indirizzo']
}

# regexp
CAP = re.compile(r'\d{5}')
PARENTHESIS = re.compile(r'\(.*\)', re.IGNORECASE)
CURLY = re.compile(r'\{.*\}', re.IGNORECASE)
DI = re.compile(r' di ', re.IGNORECASE)
PIXELS = re.compile(r'\d+(px)?', re.IGNORECASE)
#NUMBERS = re.compile(r'\d*', re.IGNORECASE)

PLACES = ['via', 'piazza', 'corso', 'viale', 'aeroporto']

NR = NutsRecon()

# logging
logger = logging.getLogger('nuts4nuts.template')


class TemplateAnalyzer(object):

    def __init__(self, page, lang='it'):
        self.abstract = None
        self.page = page
        self.lang = lang

    def _treat(self, name):
        if isinstance(name, unicode):
            return name.lower().replace(' ', '_')
        if isinstance(name, str):
            return name.lower().replace(' ', '_').decode()

    def _normalize(self, name):
        if 'http:':
            return name.lower().replace(' ', '_')
        if isinstance(name, str):
            return name.lower().replace(' ', '_').decode()

    def _find_index(self, split):
        logger.debug(split)
        indexes =  [s[0] for s in enumerate(split) if not any([p in s[1].lower() for p in PLACES])]
        logger.debug(indexes)
        index = -1
        if indexes:
            index = indexes[-1]
        return index

    def _get_types(self, reconres):
        types = list()
        for r in reconres:
            types.append((r['type'][0]['id'], r['id']))
        return types

    def _get_fathers(self, reconres):
        fathers = list()
        for r in reconres:        
            fathers.append(r['name'].split('->')[0])
        return fathers

    def analyze_templates(self):
        logger.debug(self.page)
        finalplaces = list()
        types = list()
        fathers = list()
        try:
            templates = wtp.data_from_templates(self.page, self.lang)
        except ValueError:
            templates = []

        logger.debug(templates)

        for t in templates:
            name = self._treat(t['name'])
            if name in TEMPLATES_TO_ANALYZE_IT.keys():
                attributes = TEMPLATES_TO_ANALYZE_IT[name]
                tdata = {self._treat(k): v.lower() for k, v in t['data'].iteritems()}
                logger.debug(tdata)
                locations = [tdata[attr]
                             for attr in attributes
                             if (attr in tdata and tdata[attr] != '')]

                logger.debug(locations)
                for place in locations:
                    logger.debug(place)
                    place = place.replace('italia', '')
                    place = place.strip().strip(',')

                    if PIXELS.search(place):
                        start = PIXELS.search(place).start()
                        stop = PIXELS.search(place).end()
                        logger.debug(start)
                        logger.debug(stop)
                        place = place[stop:].strip()

                    if CAP.search(place):
                        split = CAP.split(place)
                        split = [s.strip() for s in split if s.strip() != '']
                        not_address = self._find_index(split)
                        place = split[not_address]

                    if PARENTHESIS.search(place):
                        start = PARENTHESIS.search(place).start()
                        stop = PARENTHESIS.search(place).end()
                        place = place[:start] + place[stop:]

                    if CURLY.search(place):
                        start = CURLY.search(place).start()
                        stop = CURLY.search(place).end()
                        place = place[:start] + place[stop:]

                    if ',' in place:
                        split = place.split(',')
                        split = [s.strip() for s in split if s.strip() != '']
                        not_address = self._find_index(split)
                        logger.debug(not_address)
                        place = split[not_address]

                    place = place.split(' - ')[0]

                    place = place.strip(',').strip()
                    place = place.replace('[', '').replace(']', '')
                    logger.debug(place)

                    reconres = NR.query(query=place)

                    if not reconres:
                        if DI.search(place):
                            place = DI.split(place)[-1]
                            reconres = NR.query(query=place)

                    for r in reconres:
                        types = self._get_types(reconres)
                        fathers = self._get_fathers(reconres)

                    logger.debug('place: name={name}, types={types}'.format(
                                 name=place.encode('utf-8'),
                                 types=types))

                    if set(lau for lau, id_ in types).intersection(ALLOWEDTYPES):
                        place = PlaceCandidate(name=place.encode('utf-8').title(),
                                               fathers = fathers)
                        place_type = place.set_type_from_candidates(types)
                        place.set_id_from_candidates(types, place_type)
                        finalplaces.append(place)

        for cand in finalplaces:
            cand.score = 1.0/float(len(finalplaces))

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

    # --- analyze templates ---
    # print
    # print "Analyze the templates in: 'Duomo di Milano'"
    # ta = TemplateAnalyzer('Duomo_di_Milano', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Grattacielo Pirelli'"
    # ta = TemplateAnalyzer('Grattacielo Pirelli', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Palazzo Vecchio'"
    # ta = TemplateAnalyzer('Palazzo Vecchio', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'akfjkldsghjahgn' (non existing page)"
    # ta = TemplateAnalyzer('akfjkldsghjahgn', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Juventus Stadium'"
    # ta = TemplateAnalyzer('Juventus_Stadium', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Stadio_Giuseppe_Meazza'"
    # ta = TemplateAnalyzer('Stadio Giuseppe Meazza', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Vota la voce 1997'"
    # ta = TemplateAnalyzer('Vota_la_voce_1997', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Sergio_Bonelli_Editore'"
    # ta = TemplateAnalyzer('Sergio_Bonelli_Editore', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Piaggio_%26_C.'"
    # ta = TemplateAnalyzer('Piaggio_%26_C.', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Telenorba'"
    # ta = TemplateAnalyzer('Telenorba', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Arco di Tiberio'"
    # ta = TemplateAnalyzer('Arco di Tiberio', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Montonate'"
    # ta = TemplateAnalyzer('Montonate', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Aeroporto_di_Bologna-Borgo_Panigale'"
    # ta = TemplateAnalyzer('Aeroporto_di_Bologna-Borgo_Panigale', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Colle_del_Giovo'"
    # ta = TemplateAnalyzer('Colle_del_Giovo', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Trentino_trasporti'"
    # ta = TemplateAnalyzer('Trentino_trasporti', lang='it')
    # print ta.analyze_templates()
    # print
    # print "Analyze the templates in: 'Stazione_di_Quistello'"
    # ta = TemplateAnalyzer('Stazione_di_Quistello', lang='it')
    # print ta.analyze_templates()
    print
    print "Analyze the templates in: 'Falchi_Ugento'"
    ta = TemplateAnalyzer('Falchi_Ugento', lang='it')
    print ta.analyze_templates()
    print
    print "Analyze the templates in: 'Stazione_di_Fiumicino_Aeroporto'"
    ta = TemplateAnalyzer('Stazione_di_Fiumicino_Aeroporto', lang='it')
    print ta.analyze_templates()
    print
    print "Analyze the templates in: 'Museo del Risorgimento (Castelfidardo)'"
    ta = TemplateAnalyzer('Museo del Risorgimento (Castelfidardo)', lang='it')
    print ta.analyze_templates()
