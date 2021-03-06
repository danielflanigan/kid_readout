import matplotlib

from kid_readout.roach import baseband

matplotlib.use('agg')
import numpy as np
import time
import sys
from kid_readout.utils import data_file,sweeps
from kid_readout.analysis.resonator import fit_best_resonator

ri = baseband.RoachBaseband()
ri.initialize()
#ri.set_fft_gain(6)
f0s = np.load('/home/gjones/readout/kid_readout/apps/ybco_4_element_2015-03-01.npy')
f0s.sort()
#f0s = f0s*(0.9995)

suffix = "power"

nf = len(f0s)
atonce = 2
if nf % atonce > 0:
    print "extending list of resonators to make a multiple of ",atonce
    f0s = np.concatenate((f0s,np.arange(1,1+atonce-(nf%atonce))+f0s.max()))


nsamp = 2**18
step = 1
nstep = 80
f0binned = np.round(f0s*nsamp/512.0)*512.0/nsamp
offset_bins = np.arange(-(nstep+1),(nstep+1))*step

offsets = offset_bins*512.0/nsamp
offsets = np.concatenate(([offsets.min()-20e-3,],offsets,[offsets.max()+20e-3]))

print f0s
print offsets*1e6
print len(f0s)


if False:
    from kid_readout.equipment.parse_srs import get_all_temperature_data
    while True:
        temp = get_all_temperature_data()[1][-1]
        print "mk stage at", temp
        if temp > 0.348:
            break
        time.sleep(300)
    time.sleep(600)
start = time.time()

use_fmin = True
attenlist = np.linspace(33,63,10)
#attenlist = [44.0]
#attenlist = attenlist[:4]
for atten in attenlist:
    print "setting attenuator to",atten
    ri.set_dac_attenuator(atten)
    measured_freqs = sweeps.prepare_sweep(ri,f0binned,offsets,nsamp=nsamp)
    print "loaded waveforms in", (time.time()-start),"seconds"
    
    sweep_data = sweeps.do_prepared_sweep(ri, nchan_per_step=atonce, reads_per_step=8)
    orig_sweep_data = sweep_data
    meas_cfs = []
    idxs = []
    delays = []
    for m in range(len(f0s)):
        fr,s21,errors = sweep_data.select_by_freq(f0s[m])
        thiscf = f0s[m]
        res = fit_best_resonator(fr[1:-1],s21[1:-1],errors=errors[1:-1]) #Resonator(fr,s21,errors=errors)
        delay = res.delay
        delays.append(delay)
        s21 = s21*np.exp(2j*np.pi*res.delay*fr)
        res = fit_best_resonator(fr,s21,errors=errors)
        fmin = fr[np.abs(s21).argmin()]
        print "s21 fmin", fmin, "original guess",thiscf,"this fit", res.f_0, "delay",delay,"resid delay",res.delay
        if use_fmin:
            meas_cfs.append(fmin)
        else:
            if abs(res.f_0 - thiscf) > 0.1:
                if abs(fmin - thiscf) > 0.1:
                    print "using original guess"
                    meas_cfs.append(thiscf)
                else:
                    print "using fmin"
                    meas_cfs.append(fmin)
            else:
                print "using this fit"
                meas_cfs.append(res.f_0)
        idx = np.unravel_index(abs(measured_freqs - meas_cfs[-1]).argmin(),measured_freqs.shape)
        idxs.append(idx)
    
    delay = np.median(delays)
    print "median delay is ",delay
    nsamp = 2**20
    step = 1
    f0binned = np.round(f0s*nsamp/512.0)*512.0/nsamp
    offset_bins = np.array([-8,-4,-2,-1,0,1,2,4])#np.arange(-4,4)*step
    
    offset_bins = np.concatenate(([-40,-20],offset_bins,[20,40]))
    offsets = offset_bins*512.0/nsamp
    
    meas_cfs = np.array(meas_cfs)
    f0binned = np.round(meas_cfs*nsamp/512.0)*512.0/nsamp
    f0s = f0binned 
    measured_freqs = sweeps.prepare_sweep(ri,f0binned,offsets,nsamp=nsamp)
    print "loaded updated waveforms in", (time.time()-start),"seconds"
    
    
    
    sys.stdout.flush()
    time.sleep(1)
    

    df = data_file.DataFile(suffix=suffix)
    df.log_hw_state(ri)
    sweep_data = sweeps.do_prepared_sweep(ri, nchan_per_step=atonce, reads_per_step=8, sweep_data=orig_sweep_data)
    df.add_sweep(sweep_data)
    meas_cfs = []
    idxs = []
    for m in range(len(f0s)):
        fr,s21,errors = sweep_data.select_by_freq(f0s[m])
        thiscf = f0s[m]
        s21 = s21*np.exp(2j*np.pi*delay*fr)
        res = fit_best_resonator(fr,s21,errors=errors) #Resonator(fr,s21,errors=errors)
        fmin = fr[np.abs(s21).argmin()]
        print "s21 fmin", fmin, "original guess",thiscf,"this fit", res.f_0
        if use_fmin:
            meas_cfs.append(fmin)
        else:
            if abs(res.f_0 - thiscf) > 0.1:
                if abs(fmin - thiscf) > 0.1:
                    print "using original guess"
                    meas_cfs.append(thiscf)
                else:
                    print "using fmin"
                    meas_cfs.append(fmin)
            else:
                print "using this fit"
                meas_cfs.append(res.f_0)
        idx = np.unravel_index(abs(measured_freqs - meas_cfs[-1]).argmin(),measured_freqs.shape)
        idxs.append(idx)
    print meas_cfs
    ri.add_tone_freqs(np.array(meas_cfs))
    ri.select_bank(ri.tone_bins.shape[0]-1)
    ri._sync()
    time.sleep(0.5)
    
    
    #raw_input("turn on LED take data")
    
    
    df.log_hw_state(ri)
    nsets = len(meas_cfs)/atonce
    tsg = None
    for iset in range(nsets):
        selection = range(len(meas_cfs))[iset::nsets]
        ri.select_fft_bins(selection)
        ri._sync()
        time.sleep(0.2)
        t0 = time.time()
        dmod,addr = ri.get_data_seconds(30,demod=True)
        print nsets,iset,tsg
        tsg = df.add_timestream_data(dmod, ri, t0, tsg=tsg)
    df.sync()
    
    df.nc.close()
    
print "completed in",((time.time()-start)/60.0),"minutes"
