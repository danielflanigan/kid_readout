"""
Scan a large frequency range at a given frequency resolution.

At each LO frequency, scan using positive baseband frequencies and save one SweepArray.
"""
from __future__ import division
import time

import numpy as np

from kid_readout.roach import analog, hardware_tools, tools
from kid_readout.measurement import acquire, basic, core
from kid_readout.equipment import hardware, starcryo_temps

acquire.show_settings()
acquire.show_git_status()
logger = acquire.get_script_logger(__file__)


# Parameters
suffix = 'scan'
attenuations = [0]
df_baseband_target = 60e3
f_start = 1600e6
f_stop = 4000e6
overlap_fraction = 0.5
f_baseband_minimum = 10e6  # Keep the tones above the LO by at least this frequency
f_baseband_maximum = 180e6  # Keep the tones below this frequency
length_seconds = 0.01  # The length of each stream
filterbank_bin_separation = 16  # The number of PFB bins that separate tones; the minimum is 2
f_lo_resolution = 2.5e3  # The minimum is 2.5e3
num_tones_maximum = 128  # Tha maximum is 128, imposed by the data streaming rate
fft_gain = None  # If None, optimize using the tones at the first LO frequency

# Hardware
temperature = starcryo_temps.Temperature()
conditioner = analog.HeterodyneMarkII()
hw = hardware.Hardware(temperature, conditioner)
ri = hardware_tools.r2h14_with_mk2(initialize=True, use_config=False)
ri.set_modulation_output('high')
ri.adc_valon.set_ref_select(0)
assert np.all(ri.adc_valon.get_phase_locks())

# Calculate sweep parameters, LO and baseband sweep frequencies
ri_state = ri.state
# The tone sample exponent (and thus the number of tone samples) are set so that the actual frequency spacing
# is less than the target frequency spacing.
tone_sample_exponent = int(np.ceil(np.log2(ri_state.adc_sample_rate / df_baseband_target)))
df_baseband = ri_state.adc_sample_rate / 2 ** tone_sample_exponent
logger.info("Baseband resolution is {:.0f} Hz using 2^{:d} samples".format(df_baseband, tone_sample_exponent))
df_filterbank = ri_state.adc_sample_rate / ri_state.num_filterbank_channels
df_tone_minimum = df_filterbank * filterbank_bin_separation  # The minimum distance between tones

df_tone = max([df_tone_minimum])
logger.info("Separating tones by {:d} filterbank bins, or {:.3f} MHz".format(
        filterbank_bin_separation, 1e-6 * df_tone))
num_waveforms = filterbank_bin_separation * 2 ** tone_sample_exponent // ri_state.num_filterbank_channels
num_tones = min([num_tones_maximum,
                 2 ** int(np.log2((f_baseband_maximum - f_baseband_minimum) / df_tone))])
df_sweep = df_tone * num_tones
logger.info("Each sweep consists of {:d} waveforms of {:d} tones and spans {:.1f} MHz".format(
    num_waveforms, num_tones, 1e-6 * df_sweep))
df_lo = (1 - overlap_fraction) * df_sweep
logger.info("With {:.2f} fractional overlap, LO frequencies are separated by {:.1f} MHz".format(
    overlap_fraction, 1e-6 * df_lo))
num_sweeps = int(np.ceil((f_stop - f_start) / df_lo))
logger.info("The {:d} sweeps span {:.1f} MHz to {:.1f} MHz".format(
    num_sweeps, 1e-6 * f_start, 1e-6 * (f_start + df_lo * num_sweeps)))
f_baseband_all = (f_baseband_minimum +
                  df_baseband * np.arange(num_waveforms * num_tones).reshape((num_waveforms, num_tones), order='F'))
f_lo_all = f_start - f_baseband_minimum + df_lo * np.arange(num_sweeps)

# Run
npd = acquire.new_npy_directory(suffix=suffix)
tic = time.time()
try:
    for attenuation_index, attenuation in enumerate(attenuations):
        state = hw.state()
        state['attenuation_index'] = attenuation_index
        scan = basic.Scan(sweep_arrays=core.IOList(), state=state)
        npd.write(scan)
        ri.set_dac_attenuator(attenuation)
        for lo_index, f_lo in enumerate(f_lo_all):
            assert np.all(ri.adc_valon.get_phase_locks())
            tools.set_and_attempt_external_phase_lock(ri=ri, f_lo=1e-6 * f_lo, f_lo_spacing=1e-6 * f_lo_resolution)
            if lo_index == 0:
                ri.set_tone_baseband_freqs(freqs=1e-6 * f_baseband_all[0, :],
                                           nsamp=2 ** tone_sample_exponent)
                ri.select_fft_bins(readout_selection=np.arange(ri.tone_bins.shape[1]))
                time.sleep(1)
                if fft_gain is None:
                    tools.optimize_fft_gain(ri)
                else:
                    ri.set_fft_gain(fft_gain)
            state = hw.state()
            state['lo_index'] = lo_index
            scan.sweep_arrays.append(acquire.run_sweep(ri=ri, tone_banks=1e-6 * (f_lo + f_baseband_all),
                                                       num_tone_samples=2 ** tone_sample_exponent,
                                                       length_seconds=length_seconds, state=state))
            npd.write(ri.get_adc_measurement())
finally:
    npd.close()
    print("Wrote {}".format(npd.root_path))
    print("Elapsed time {:.0f} minutes.".format((time.time() - tic) / 60))
