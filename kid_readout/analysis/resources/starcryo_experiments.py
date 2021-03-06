from kid_readout.utils.time_tools import date_to_unix_time
DIODE_1_TEMP = 1
DIODE_2_TEMP = 2
DIODE_3_TEMP = 3
DIODE_4_TEMP = 4
ROX_1_TEMP = 9
ROX_2_TEMP = 11
ROX_3_TEMP = 13
thermometry_2017_11_13 = dict(package=7, load=3, stepper=5)
thermometry_2016_11_14 = dict(package=ROX_1_TEMP, secondary_package=ROX_2_TEMP, load=DIODE_1_TEMP)
thermometry_2016_09_09 = dict(package=ROX_2_TEMP, load=DIODE_1_TEMP)
thermometry_2016_08_10 = dict(package=9, load=1)
thermometry_2016_07_08 = dict(package=9, load=1)
thermometry_2015_10_28 = dict(package=9, load=11, waveguide=1)
thermometry_2015_06_26 = dict(package=9, load=11, waveguide=1)
thermometry_2015_06_12 = dict(package=9, load=11, waveguide=1)
thermometry_2015_05_29 = dict(package=9, load=11, waveguide=1)
thermometry_2015_04_17 = dict(package=9, load=11, waveguide=1)
thermometry_2015_03_27 = dict(package=9, optics_box=11, waveguide=1)
thermometry_2015_02_25 = dict(package=9, load=11, waveguide=1)
thermometry_2014_11_14 = dict(package=9, secondary_package=11, ternary_package=13, load=1)
thermometry_2014_10_20 = dict(package=9, null=1, load=11, waveguide=2)
thermometry_2014_10_10 = dict(package=9, load=1, stage=11, waveguide=2)
thermometry_2014_03_19 = dict(package=11, load=2, stage=13, copper=1)

by_unix_time_table = [
    dict(date='2017-11-23',
         description='Stanford MKIDArray02-0001 multichroic 23-pixel Al-under-Nb array on SOI',
         optical_state='light',
         thermometry_config=thermometry_2017_11_13,
         chip_id='MKIDArray02-0001'),

    dict(date='2017-11-13',
         description='Stanford MKIDArray02-0001 multichroic 23-pixel Al-under-Nb array on SOI',
         optical_state='light',
         thermometry_config=thermometry_2017_11_13,
         chip_id='MKIDArray02-0001'),

    dict(date='2016-11-18',
         description='Stanford AlMn LEKID',
         optical_state='dark',
         thermometry_config=thermometry_2016_11_14,
         chip_id='Stanford-AlMn-0304'),

    dict(date='2016-09-30',
         description='JPL LF-2 dual pol 8x8 array in prototype Cardiff horn package LB-P LL-P',
         optical_state='light',
         thermometry_config=thermometry_2016_09_09,
         chip_id='JPL-LF-2'),

    dict(date='2016-09-09',
         description='JPL HF-1 dual pol 8x8 array in dark package DKL-1,DKB-1',
         optical_state='dark',
         thermometry_config=thermometry_2016_09_09,
         chip_id='JPL-HF-1'),

    dict(date='2016-08-10',
         description='Stanford TwoLayer02-0303 hybrid Al-Nb eight-LEKID chip in dark package H3+L3, taped.',
         optical_state='dark',
         thermometry_config=thermometry_2016_08_10,
         chip_id='TwoLayer02-0303'),

    dict(date='2016-07-08',
         description='STAR Cryo 150509 WSPEC MT chip in dark package; absorber tied to 3 K.',
         optical_state='dark',
         thermometry_config=thermometry_2016_07_08,
         chip_id='2015-10 WSPEC MT'),

    dict(date='2016-01-06',
         description='JPL 2015-10 park-1 dual pol 160 um. Package 160-1B/-1H. LPF, waveguide with teflon spacer and 90 '
                     'degree twist, absorber tied to 1K, horns open',
         optical_state='light',
         thermometry_config=thermometry_2015_10_28,
         chip_id='2015-10 park JPL-1'),

    dict(date='2015-10-28',
         description='STAR Cryo dual pol 2015-04 nevins Al horn package, LPF, waveguide with teflon spacer and 90 '
                     'deg twist, absorber tied to 1 K, all horns open',
         optical_state='light',
         thermometry_config=thermometry_2015_10_28,
         chip_id='2015-04 nevins'),

    dict(date='2015-06-26',
         description='STAR Cryo 4x5 140825 0813f8 BEC Al horn package 1, AR chip, LPF, copper shield, waveguide with teflon spacer, absorber tied to 1 K, all horns taped over, waveguide 90 degree twist',
         optical_state='light',
         thermometry_config=thermometry_2015_06_26,
         chip_id='140825 0813f8'),

    dict(date='2015-06-12',
         description='STAR Cryo 4x5 140825 0813f8 BEC Al horn package 1, AR chip, LPF, copper shield, waveguide with teflon spacer, absorber tied to 1 K, all horns but one taped over, waveguide 90 degree twist',
         optical_state='light',
         thermometry_config=thermometry_2015_06_12,
         chip_id='140825 0813f8'),

    dict(date='2015-05-29',
         description='STAR Cryo 4x5 140825 0813f8 BEC Al horn package 1, AR chip, LPF, copper shield, waveguide with teflon spacer, absorber tied to 1 K, all horns but one taped over, waveguide 90 degree twist',
         optical_state='light',
         thermometry_config=thermometry_2015_05_29,
         chip_id='140825 0813f8'),

    dict(date='2015-04-17',
         description='STAR Cryo 4x5 140825 0813f8 BEC Al horn package 1, AR chip, LPF, copper shield, waveguide with teflon spacer, absorber tied to 1 K, six horns taped over, waveguide 90 degree twist',
         optical_state='light',
         thermometry_config=thermometry_2015_04_17,
         chip_id='140825 0813f8'),

    dict(date='2015-03-27',
         description='STAR Cryo 4x5 140825 0813f8 BEC Al horn package 1, AR chip, LPF, copper shield, waveguide with teflon spacer, no absorber, six horns taped over',
         optical_state='light',
         thermometry_config=thermometry_2015_03_27,
         chip_id='140825 0813f8'),

    dict(date='2015-02-25',
         description='STAR Cryo 4x5 140825 0813f8 BEC Al horn package 1, AR chip, LPF, copper shield, waveguide with teflon spacer, absorber tied to 1 K, six horns taped over',
         optical_state='light',
         thermometry_config=thermometry_2015_02_25,
         chip_id='140825 0813f8'),
    
    dict(date='2014-11-14',
         description='STAR Cryo 4x5 140825 0813f8 BEC Al horn package 1, AR chip, LPF, copper shield, waveguide with teflon spacer, absorber tied to 3 K, six horns taped over',
         optical_state='light',
         thermometry_config=thermometry_2014_11_14,
         chip_id='140825 0813f8'),
    
    dict(date='2014-10-20',
         description='STAR Cryo 4x5 130919 0813f12 ASU Al horn package, AR chip, LPF, copper shield, waveguide with teflon spacer, absorber tied to 1 K',
         optical_state='light',
         thermometry_config=thermometry_2014_10_20,
         chip_id='130919 0813f12',
    ),

    dict(date='2014-10-10',
         description='STAR Cryo 4x5 130919 0813f12 ASU Al horn package, AR chip, LPF, copper shield, waveguide with air spacer, absorber tied to 1 K',
         optical_state='light',
         thermometry_config=thermometry_2014_10_10,
         chip_id='130919 0813f12',
    ),

    dict(date='2014-09-11',
         description='STAR Cryo 4x5 130919 0813f12 ASU Al horn package, AR chip, LPF, copper shield, waveguide with air spacer',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),

    dict(date='2014-08-26',
         description='STAR Cryo 4x5 130919 0813f12 ASU Al horn package, AR chip, LPF, copper shield, waveguide with Stycast spacer',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-08-18',
         description='STAR Cryo 4x5 130919 0813f12 ASU Al horn package, AR chip, no LPF, copper shield, IR LED fiber',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-08-12',
         description='STAR Cryo 4x5 140423 0813f12 Al horn package, AR chip, LPF, copper shield, IR LED fiber',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='140423 0813f12',
    ),
    dict(date='2014-07-30',
         description='STAR Cryo 4x5 140423 0813f9 Al horn package, AR chip, LPF, copper shield, IR LED fiber',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='140423 0813f9',
    ),
    dict(date='2014-07-03',
         description='STAR Cryo 4x5 130919 0813f12 Al horn package, AR chip, LPF, copper shield, IR LED fiber',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-04-28',
         description='STAR Cryo 4x5 130919 0813f12 Al horn package, AR chip, LPF, copper shield',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-04-16',
         description='STAR Cryo 4x5 130919 0813f12 Al horn package, AR chip, fully taped',
         optical_state='dark',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-04-10',
         description='STAR Cryo 4x5 130919 0813f12 Al horn package, AR chip, Al tape over horns, copper shield',
         optical_state='dark',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-04-04',
         description='STAR Cryo 4x5 130919 0813f12 Al horn package, AR chip, LPF, Al tape over horns',
         optical_state='dark',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-03-28',
         description='STAR Cryo 4x5 130919 0813f12 Al horn package, AR chip, LPF, Al tape over a few horns',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-03-19',
         description='STAR Cryo 4x5 130919 0813f12 Al horn package, AR chip, LPF, broken connection',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-02-27',
         description='STAR Cryo 4x5 130919 0813f10 Cu horn package, LPF',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
    dict(date='2014-01-28',
         description='STAR Cryo 4x5 130919 0813f10 Cu horn package, no LPF',
         optical_state='light',
         thermometry_config=thermometry_2014_03_19,
         chip_id='130919 0813f12',
    ),
]

by_unix_time_table.sort(key=lambda x: date_to_unix_time(x['date']))
_unix_time_index = [date_to_unix_time(x['date']) for x in by_unix_time_table]

