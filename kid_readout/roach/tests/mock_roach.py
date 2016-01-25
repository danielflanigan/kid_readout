__author__ = 'gjones'

class MockRoach(object):
    def __init__(self, host, port=7147, tb_limit=20, timeout=10.0, logger=None,
                 _fpga_clk=256.0):
        self._fpga_clk = _fpga_clk
        self._is_prgorammed = False
        self._boffile_list = []
    def is_connected(self):
        return True
    def listdev(self):
        if not self._is_prgorammed:
            raise RuntimeError('Request listdev failed.\n  Request: ?listdev\n  Reply: !listdev fail program.')
        return []
    def listbof(self):
        return []
    def progdev(self,boffile):
        if boffile == '':
            self._is_prgorammed = False
            return 'ok'
        if boffile in self._boffile_list:
            self._boffile = boffile
            self._is_programmed = True
            return 'ok'
        else:
            raise ValueError("Unknown boffile")
    def read(self,device_name,size,offsest=0):
        return
    def write(self,device_name,offset=0):
        pass
    def read_int(self,device_name,offset=0):
        return 0
    def write_int(self,device_name,integer,blindwrite=False, offset=0):
        pass
    def snapshot_get(self,dev_name,man_trig=False,man_valid=False,wait_period=1,offset=-1,circular_capture=False,
                     get_extra_val=False):
        pass

    def est_brd_clk(self):
        return self._fpga_clk