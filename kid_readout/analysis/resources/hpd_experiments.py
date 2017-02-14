from kid_readout.utils.time_tools import date_to_unix_time

by_unix_time_table = [
    dict(date='2017-02-10',
         description='Stanford OneLayerNb01-0403 niobium v1 CPW medley chip in holder H6 and lid L6 (taped) with new mu-metal magnetic shield.',
         optical_state='dark',
         chip_id='OneLayerNb01-0403 '
         ),
    dict(date='2016-10-11',
         description='Stanford OneLayerAlStep01-0403 aluminum v1 CPW medley chip in holder H2 and lid L2, taped.',
         optical_state='dark',
         chip_id='OneLayerAlStep01-0403 '
         ),
    dict(date='2016-08-03',
         description='Stanford TwoLayer02-0304 v1 CPW medley chip in holder H1 and lid L1, taped.',
         optical_state='dark',
         chip_id='TwoLayer02-0304'
         ),
    dict(date='2016-07-05',
         description='Stanford TwoLayer01-0202 v1 CPW medley chip in holder H1 and lid L1, taped.',
         optical_state='dark',
         chip_id='TwoLayer01-0202'
         ),
    dict(date='2016-06-21',
         description='Stanford TwoLayer01-0306 v1 CPW medley chip in holder H1 and lid L1, taped and mounted normal to ambient magnetic field.',
         optical_state='dark',
         chip_id='TwoLayer01-0306'
         ),
    dict(date='2016-06-09',
         description='Stanford TwoLayer01-0306 v1 CPW medley chip in holder H1 and lid L1, taped.',
         optical_state='dark',
         chip_id='TwoLayer01-0306'
         ),
    dict(date='2016-04-20',
         description='Stanford Demo05AlMn-0506 v1 CPW coupling chip in holder H1 and lid L1, not taped.',
         optical_state='dark',
         chip_id='Demo05AlMn-0506'
         ),
    dict(date='2016-04-08',
         description='Stanford Demo02AlMn-0506 v1 CPW coupling chip in holder H1 and lid L1, not taped.',
         optical_state='dark',
         chip_id='Demo02AlMn-0506'
         ),
    dict(date='2016-03-04',
         description='STAR Cryo 160105 v1 (almost) CPW coupling chip in holder H3 and lid L3.',
         optical_state='dark',
         chip_id='160105 v1 (almost) CPW coupling chip'
         ),
    # Lots of missing cooldowns here.
    dict(date='2015-07-09',
         description='STAR Cryo 150509 2015-04 nevins dual pol test chip Al horn package, AR chip, aluminum tape over '
                     'horns. 1550 nm LED illumination via fiber.',
         optical_state='light',
         chip_id='150509 2015-04 nevins',
    ),
    dict(date='2015-06-29',
         description='STAR Cryo 150509 2015-04 nevins dual pol test chip Al horn package, AR chip, aluminum tape over '
                     'horns',
         optical_state='dark',
         chip_id='150509 2015-04 nevins',
    ),
    dict(date='2015-06-15',
         description='ASU-1 2015-04 nevins dual pol test chip Al horn package, AR chip, aluminum tape over '
                     'horns',
         optical_state='dark',
         chip_id='ASU-1 2015-04 nevins',
    ),
    dict(date='2015-05-06',
         description='JPL 5x4 array in Al horn package in superdark tamale with magnetic field test coil',
         optical_state='dark',
         chip_id='JPL 5x4',
    ),
    dict(date='2015-04-29',
         description='JPL 5x4 array with Stycast filter and blackbody load',
         optical_state='light',
         chip_id='JPL 5x4',
    ),
    dict(date='2015-02-27',
         description='YBCO 141217-3 4 element frontside illuminated with LEDs',
         optical_state='light',
         chip_id='YBCO 141217-3 4 element',
    ),
    dict(date='2015-01-30',
         description='YBCO 141217-3 9 element frontside illuminated with LEDs',
         optical_state='light',
         chip_id='YBCO 141217-3 9 element',
    ),
    dict(date='2015-01-13',
         description='YBCO 141217-3 9 element backside illuminated with LEDs',
         optical_state='light',
         chip_id='YBCO 141217-3 9 element',
    ),
    dict(date='2014-12-11',
         description='STAR Cryo 4x5 130919 0813f12 ASU Al horn package, AR chip, aluminum tape over horns, '
                     'copper shield soldered shut around package, steelcast coax filters, small hole in copper and '
                     'aluminum shields to let in 1550 nm and red LED light',
         optical_state='light',
         chip_id='130919 0813f12',
    ),
    dict(date='2014-12-01',
         description='STAR Cryo 4x5 130919 0813f12 ASU Al horn package, AR chip, aluminum tape over horns, '
                     'copper shield soldered shut around package, steelcast coax filters',
         optical_state='dark',
         chip_id='130919 0813f12',
    ),
    dict(date='2014-08-11',
         description='STAR Cryo 3x3 140423 0813f4 JPL window package, Al tape with hole for red LED',
         optical_state='dark',
         chip_id='140423 0813f4'),
    dict(date='2014-07-28',
         description='STAR Cryo 5x4 130919 0813f12 Aluminum package, taped horns',
         optical_state='dark',
         chip_id='130919 0813f12'),
    dict(date='2014-04-14',
         description='STAR Cryo 3x3 0813f5 JPL window package, Al tape cover, encased in copper tamale',
         optical_state='dark',
         chip_id='130919 0813f5'),
    dict(date='2014-02-21',
         description='STAR Cryo 3x3 0813f5 JPL window package, Al tape cover part 2',
         optical_state='dark',
         chip_id='130919 0813f5'),
    dict(date='2014-02-10',
         description='STAR Cryo 3x3 0813f5 JPL window package, Al tape cover',
         optical_state='dark',
         chip_id='130919 0813f5'),
    ]

by_unix_time_table.sort(key=lambda x: date_to_unix_time(x['date']))
_unix_time_index = [date_to_unix_time(x['date']) for x in by_unix_time_table]
