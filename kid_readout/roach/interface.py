import os
import sys
import time
import numpy as np
import borph_utils
import udp_catcher

__author__ = 'gjones'

CONFIG_FILE_NAME = '/data/readout/roach_config.npz'

class RoachInterface(object):
    """
    Base class for readout systems.

    These methods define an abstract interface that can be relied on to be consistent between the baseband and
    heterodyne readout systems.
    """

    def __init__(self):
        raise NotImplementedError("Abstract class, instantiate a subclass instead of this class")

    # FPGA Functions
    def _update_bof_pid(self):
        if self.bof_pid:
            return
        try:
            self.bof_pid = borph_utils.get_bof_pid()
        except Exception, e:
            self.bof_pid = None
            raise e

    def get_raw_adc(self):
        """
        Grab raw ADC samples

        returns: s0,s1
        s0 and s1 are the samples from adc 0 and adc 1 respectively
        Each sample is a 12 bit signed integer (cast to a numpy float)
        """
        self.r.write_int('i0_ctrl', 0)
        self.r.write_int('q0_ctrl', 0)
        self.r.write_int('i0_ctrl', 5)
        self.r.write_int('q0_ctrl', 5)
        s0 = (np.fromstring(self.r.read('i0_bram', self.raw_adc_ns * 2), dtype='>i2')) / 16.0
        s1 = (np.fromstring(self.r.read('q0_bram', self.raw_adc_ns * 2), dtype='>i2')) / 16.0
        return s0, s1

    def auto_level_adc(self, goal=-2.0, max_tries=3):
        if self.adc_atten < 0:
            self.set_adc_attenuator(31.5)
        n = 0
        while n < max_tries:
            x, y = self.get_raw_adc()
            dbfs = 20 * np.log10(x.ptp() / 4096.0)  # fraction of full scale
            if np.abs(dbfs - goal) < 1.0:
                print "success at: %.1f dB" % self.adc_atten
                break
            newatten = self.adc_atten + (dbfs - goal)
            print "at: %.1f dBFS, current atten: %.1f dB, next trying: %.1f dB" % (dbfs, self.adc_atten, newatten)
            self.set_adc_attenuator(newatten)
            n += 1

    def set_fft_gain(self, gain):
        """
        Set the gain in the FFT

        At each stage of the FFT there is the option to downshift (divide by 2) the data, reducing the overall
        voltage gain by a factor of 2. Therefore, the FFT gain can only be of the form 2^k for k nonnegative

        gain: the number of stages to not divide on. The final gain will be 2^gain
        """
        fftshift = (2 ** 20 - 1) - (2 ** gain - 1)  # this expression puts downsifts at the earliest stages of the FFT
        self.fft_gain = gain
        self.r.write_int('fftshift', fftshift)
        self.save_state()

    # TODO: this should raise a RoachError or return None if no bank is selected or the Roach isn't programmed.
    def get_current_bank(self):
        """
        Determine what tone bank the ROACH is currently set to use
        """
        try:
            bank_reg = self.r.read_int('dram_bank')
            mask_reg = self.r.read_int('dram_mask')
        except RuntimeError:
            self.bank = 0  # this catches the case that the ROACH is not yet programmed
        if mask_reg == 0:
            self.bank = 0  # if mask is not set, bank is undefined, so call it 0
        self.bank = bank_reg / (mask_reg + 1)

    def select_bank(self, bank):
        dram_addr_per_bank = self.tone_nsamp / 2  # number of dram addresses per bank
        mask_reg = dram_addr_per_bank - 1
        bank_reg = dram_addr_per_bank * bank
        self._pause_dram()
        self.r.write_int('dram_bank', bank_reg)
        self.r.write_int('dram_mask', mask_reg)
        self._unpause_dram()
        self.bank = bank
        try:
            self.select_fft_bins(self.readout_selection)
        except AttributeError:
            self.select_fft_bins(np.arange(self.tone_bins.shape[1]))


    def set_modulation_output(self, rate='low'):
        """
        rate: can be 'high', 'low', 1-8.
            modulation output signal switching state. 'high' and 'low' set the TTL output to a constant level.
            Integers 1-8 set the switching rate to cycle every 2**k spectra
        returns: float, switching rate in Hz.
        """
        rate_register = 'gpiob'
        if str.lower(str(rate)) == 'low':
            self.r.write_int(rate_register, 0)
            self.modulation_rate = 0
            self.modulation_output = 0
            self.save_state()
            return 0.0
        if str.lower(str(rate)) == 'high':
            self.r.write_int(rate_register, 1)
            self.modulation_rate = 0
            self.modulation_output = 1
            self.save_state()
            return 0.0
        if rate >= 1 and rate <= 8:
            self.r.write_int(rate_register, 10 - rate)
            self.modulation_rate = rate
            self.modulation_output = 2
            self.save_state()
            return self.get_modulation_rate_hz()
        else:
            raise ValueError('Invalid value for rate: got %s, expected one of "high", "low", or 1-8' % str(rate))

    def get_modulation_rate_hz(self):
        if self.modulation_rate == 0:
            return 0.0
        else:
            rate_in_hz = (self.fs * 1e6 / (2 * self.nfft)) / (2 ** self.modulation_rate)
            return rate_in_hz

    def save_state(self):
        np.savez(CONFIG_FILE_NAME,
                 boffile=self.boffile,
                 adc_atten=self.adc_atten,
                 dac_atten=self.dac_atten,
                 bof_pid=self.bof_pid,
                 fft_bins=self.fft_bins,
                 fft_gain=self.fft_gain,
                 tone_nsamp=self.tone_nsamp,
                 tone_bins=self.tone_bins,
                 phases=self.phases,
                 modulation_rate=self.modulation_rate,
                 modulation_output=self.modulation_output,
                 lo_frequency=self.lo_frequency)
        try:
            os.chmod(CONFIG_FILE_NAME, 0777)
        except:
            pass

    def initialize(self, fs=512.0, start_udp=True, use_config=True):
        """
        Reprogram the ROACH and get things running

        fs: float
            Sampling frequency in MHz
        """
        if use_config:
            try:
                state = np.load(CONFIG_FILE_NAME)
                print "Loaded ROACH state from", CONFIG_FILE_NAME
            except IOError:
                print "Could not load previous state"
                state = None
        else:
            state = None
        if state is not None:
            try:
                self._update_bof_pid()
            except Exception:
                self.bof_pid = None
            if self.bof_pid is None or self.bof_pid != state['bof_pid']:
                print "ROACH configuration does not match saved state"
                state = None
        if state is None or state['boffile'] != self.boffile:
            print "Reinitializing system"
            print "Deprogramming"
            self._set_fs(fs)
            self.r.progdev('')
            print "Programming", self.boffile
            self.r.progdev(self.boffile)
            self.bof_pid = None
            self._update_bof_pid()
            self.set_fft_gain(4)
            self.r.write_int('dacctrl', 0)
            self.r.write_int('dacctrl', 1)
            estfs = self.measure_fs()
            if np.abs(fs - estfs) > 2.0:
                print "Warning! FPGA clock may not be locked to sampling clock!"
            print "Requested sampling rate %.1f MHz. Estimated sampling rate %.1f MHz" % (fs, estfs)
            if start_udp:
                print "starting udp server process on PPC"
                borph_utils.start_server(self.bof_pid)
            self.adc_atten = 31.5
            self.dac_atten = np.nan
            self.fft_bins = None
            self.tone_nsamp = None
            self.tone_bins = None
            self.phases = None
            self.modulation_output = 0
            self.modulation_rate = 0
            self.save_state()
        else:
            self.adc_atten = state['adc_atten'][()]
            self.dac_atten = state['dac_atten'][()]
            self.fft_bins = state['fft_bins']
            self.fft_gain = state['fft_gain'][()]
            self.tone_nsamp = state['tone_nsamp'][()]
            self.tone_bins = state['tone_bins']
            self.phases = state['phases']
            self.modulation_output = state['modulation_output'][()]
            self.modulation_rate = state['modulation_rate'][()]
            self.lo_frequency = state['lo_frequency'][()]

    def measure_fs(self):
        """
        Estimate the sampling rate

        This takes about 2 seconds to run
        returns: fs, the approximate sampling rate in MHz
        """
        return 2 * self.r.est_brd_clk()

        # ### Add back in these abstract methods once the interface stablilizes

    #    def select_fft_bins(self,bins):
    #        raise NotImplementedError("Abstract base class")
    #
    #    def set_channel(self,ch,dphi=None,amp=-3):
    #        raise NotImplementedError("Abstract base class")
    #    def get_data(self,nread=10):
    #        raise NotImplementedError("Abstract base class")
    #    def set_tone(self,f0,dphi=None,amp=-3):
    #        raise NotImplementedError("Abstract base class")
    #    def select_bin(self,ibin):
    #        raise NotImplementedError("Abstract base class")

    def _pause_dram(self):
        self.r.write_int('dram_rst', 0)

    def _unpause_dram(self):
        self.r.write_int('dram_rst', 2)

    # TODO: This should raise a RoachError if data is too large to fit in memory.
    def _load_dram(self, data, start_offset=0, fast=True):
        if fast:
            load_dram = self._load_dram_ssh
        else:
            load_dram = self._load_dram_katcp
        nbytes = data.nbytes
        # PPC can only access 64MB at a time, so need to break the data into chunks of this size
        bank_size = (64 * 2 ** 20)
        nbanks, rem = divmod(nbytes, bank_size)
        if rem:
            nbanks += 1
        if nbanks == 0:
            nbanks = 1
        bank_size_units = bank_size / data.itemsize  # calculate how many entries in the data array fit in one 64 MB bank

        start_offset_bytes = start_offset * data.itemsize
        bank_offset = start_offset_bytes // bank_size
        start_offset_bytes = start_offset_bytes - bank_size * bank_offset
        print "bank_offset=", bank_offset, "start_offset=", start_offset, "start_offset_bytes=", start_offset_bytes
        for bank in range(nbanks):
            print "writing DRAM bank", (bank + bank_offset)
            self.r.write_int('dram_controller', bank + bank_offset)
            load_dram(data[bank * bank_size_units:(bank + 1) * bank_size_units], offset_bytes=start_offset_bytes)

    def _load_dram_katcp(self, data, tries=2):
        while tries > 0:
            try:
                self._pause_dram()
                self.r.write_dram(data.tostring())
                self._unpause_dram()
                return
            except Exception, e:
                print "failure writing to dram, trying again"
            #                print e
            tries = tries - 1
        raise Exception("Writing to dram failed!")

    def _load_dram_ssh(self, data, offset_bytes=0, roach_root='/srv/roach_boot/etch', datafile='boffiles/dram.bin'):
        offset_blocks = offset_bytes / 512  #dd uses blocks of 512 bytes by default
        self._update_bof_pid()
        self._pause_dram()
        data.tofile(os.path.join(roach_root, datafile))
        dram_file = '/proc/%d/hw/ioreg/dram_memory' % self.bof_pid
        datafile = '/' + datafile
        result = borph_utils.check_output(
            ('ssh root@%s "dd seek=%d if=%s of=%s"' % (self.roachip, offset_blocks, datafile, dram_file)), shell=True)
        print result
        self._unpause_dram()

    # TODO: call from the functions that require it so we can stop calling it externally.
    def _sync(self):
        self.r.write_int('sync', 0)
        self.r.write_int('sync', 1)
        self.r.write_int('sync', 0)

    ### Other hardware functions (attenuator, valon)
    def set_attenuator(self, attendb, gpio_reg='gpioa', data_bit=0x08, clk_bit=0x04, le_bit=0x02):
        atten = int(attendb * 2)
        try:
            self.r.write_int(gpio_reg, 0x00)
        except RuntimeError:
            print "ROACH not programmed, cannot set attenuators"
            return
        mask = 0x20
        for j in range(6):
            if atten & mask:
                data = data_bit
            else:
                data = 0x00
            mask = mask >> 1
            self.r.write_int(gpio_reg, data)
            self.r.write_int(gpio_reg, data | clk_bit)
            self.r.write_int(gpio_reg, data)
        self.r.write_int(gpio_reg, le_bit)
        self.r.write_int(gpio_reg, 0x00)

    def set_adc_attenuator(self, attendb):
        print "Warning! ADC attenuator is no longer adjustable. Value will be fixed at 31.5 dB"
        self.adc_atten = 31.5

    #        if attendb <0 or attendb > 31.5:
    #            raise ValueError("ADC Attenuator must be between 0 and 31.5 dB. Value given was: %s" % str(attendb))
    #        self.set_attenuator(attendb,le_bit=0x02)
    #        self.adc_atten = int(attendb*2)/2.0

    def set_dac_attenuator(self, attendb):
        if attendb < 0 or attendb > 63:
            raise ValueError("DAC Attenuator must be between 0 and 63 dB. Value given was: %s" % str(attendb))

        if attendb > 31.5:
            attena = 31.5
            attenb = attendb - attena
        else:
            attena = attendb
            attenb = 0
        self.set_attenuator(attena, le_bit=0x01)
        self.set_attenuator(attenb, le_bit=0x02)
        self.dac_atten = int(attendb * 2) / 2.0
        self.save_state()

    def set_dac_atten(self, attendb):
        """ Alias for set_dac_attenuator """
        return self.set_dac_attenuator(attendb)

    def _set_fs(self, fs):
        """
        Set sampling frequency in MHz
        """
        raise NotImplementedError()

    def _window_response(self, fr):
        res = np.interp(np.abs(fr) * 2 ** 7, np.arange(2 ** 7), self._window_mag)
        res = 1 / res
        return res

    def get_data_udp(self, nread=2, demod=True):
        chan_offset = 1
        nch = self.fpga_fft_readout_indexes.shape[0]
        data, seqnos = udp_catcher.get_udp_data(self, npkts=nread * 16 * nch, streamid=1,
                                                chans=self.fpga_fft_readout_indexes + chan_offset,
                                                nfft=self.nfft, addr=(self.host_ip, 12345))  # , stream_reg, addr)
        if demod:
            data = self.demodulate_data(data)
        return data, seqnos

    ### Tried and true readout function
    def _read_data(self, nread, bufname, verbose=False):
        """
        Low level data reading loop, common to both readouts
        """
        regname = '%s_addr' % bufname
        chanreg = '%s_chan' % bufname
        a = self.r.read_uint(regname) & 0x1000
        addr = self.r.read_uint(regname)
        b = addr & 0x1000
        while a == b:
            addr = self.r.read_uint(regname)
            b = addr & 0x1000
        data = []
        addrs = []
        chans = []
        tic = time.time()
        idle = 0
        try:
            for n in range(nread):
                a = b
                if a:
                    bram = '%s_a' % bufname
                else:
                    bram = '%s_b' % bufname
                data.append(self.r.read(bram, 4 * 2 ** 12))
                addrs.append(addr)
                chans.append(self.r.read_int(chanreg))

                addr = self.r.read_uint(regname)
                b = addr & 0x1000
                while a == b:
                    addr = self.r.read_uint(regname)
                    b = addr & 0x1000
                    idle += 1
                if verbose:
                    print ("\r got %d" % n),
                sys.stdout.flush()
        except Exception, e:
            print "read only partway because of error:"
            print e
            print "\n"
        tot = time.time() - tic
        print "\rread %d in %.1f seconds, %.2f samples per second, idle %.2f per read" % (
        nread, tot, (nread * 2 ** 12 / tot), idle / (nread * 1.0))
        dout = np.concatenate(([np.fromstring(x, dtype='>i2').astype('float').view('complex') for x in data]))
        addrs = np.array(addrs)
        chans = np.array(chans)
        return dout, addrs, chans

    def _cont_read_data(self, callback, bufname, verbose=False):
        """
        Low level data reading continuous loop, common to both readouts
        calls "callback" each time a chunk of data is ready
        """
        regname = '%s_addr' % bufname
        chanreg = '%s_chan' % bufname
        a = self.r.read_uint(regname) & 0x1000
        addr = self.r.read_uint(regname)
        b = addr & 0x1000
        while a == b:
            addr = self.r.read_uint(regname)
            b = addr & 0x1000
        tic = time.time()
        idle = 0
        n = 0
        try:
            while True:
                try:
                    a = b
                    if a:
                        bram = '%s_a' % bufname
                    else:
                        bram = '%s_b' % bufname
                    data = self.r.read(bram, 4 * 2 ** 12)
                    addrs = addr
                    chans = self.r.read_int(chanreg)
                    res = callback(data, addrs, chans)
                except Exception, e:
                    print "read only partway because of error:"
                    print e
                    print "\n"
                    res = False
                n += 1
                if res:
                    break
                addr = self.r.read_uint(regname)
                b = addr & 0x1000
                while a == b:
                    addr = self.r.read_uint(regname)
                    b = addr & 0x1000
                    idle += 1
                if verbose:
                    print ("\r got %d" % n),
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass
        tot = time.time() - tic
        print "\rread %d in %.1f seconds, %.2f samples per second, idle %.2f per read" % (
        n, tot, (n * 2 ** 12 / tot), idle / (n * 1.0))


class RoachError(Exception):
    """
    This class is raised on Roach-specific errors.
    """
    pass