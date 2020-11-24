from re import search
from time import process_time

from base.configuration_parser import ConfigurationParser
from player.parser import parse_mpd
from r2a.ir2a import IR2A
from collections import Counter


class R2ABandwidth(IR2A):
    def __init__(self, id):
        super().__init__(id)

        self.MIN_EVAL_BUFFER_SZ = 1
        self.MAX_EVAL_BUFFER_SZ = 5

        self.STABILITY_PERC = .2
        self.INITIAL_QI_ID = .65

        self.DECREASE_BPS = -1
        self.KEEP_BPS = 0
        self.INCREASE_BPS = 1

        self.qi = []
        self.qi_id = None
        self.elapsed_time = None
        self.eval_buffer_size = 0
        self.eval_buffer = []
        self.cnt = 0

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.qi = parse_mpd(msg.get_payload()).get_qi()
        self.qi_id = int(len(self.qi) * self.INITIAL_QI_ID)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        msg.add_quality_id(self.qi[self.qi_id])

        self.elapsed_time = process_time()

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.cnt += 1
        self.elapsed_time = process_time() - self.elapsed_time

        self._performance_analyses(msg.bit_length)

        self._set_next_qi_id()

        self.send_up(msg)

    def initialize(self):
        settings = ConfigurationParser.get_instance()
        period = int(search(r'(\d+)sec', settings.get_parameter('url_mpd')).groups()[0])

        self.eval_buffer_size = max(self.MIN_EVAL_BUFFER_SZ, self.MAX_EVAL_BUFFER_SZ // period)


    def finalization(self):
        print('finalizando!...')

    def _performance_analyses(self, bit_length):
        print()
        network_performance = bit_length // self.elapsed_time
        network_performance = bit_length // 1
        print('network_performance', network_performance)
        # print('elapsed_time', 1 / self.elapsed_time)
        network_performance = round(network_performance / self.qi[self.qi_id], 3)
        print('c_bandwidth', self.qi[self.qi_id])
        print('network_performance', network_performance)

        if network_performance < 1 - self.STABILITY_PERC:
            print('diminuindo')
            self.eval_buffer.append(self.DECREASE_BPS)
        elif network_performance > 1 + self.STABILITY_PERC:
            print('aumentando')
            self.eval_buffer.append(self.INCREASE_BPS)
        else:
            self.eval_buffer.append(self.KEEP_BPS)
            print('mantendo')

        print()

    def _set_next_qi_id(self):
        if len(self.eval_buffer) < self.eval_buffer_size:
            return


        print()
        print('eval_buffer', self.eval_buffer)
        direction = Counter(self.eval_buffer).most_common()

        if len(direction) == 1:
            direction = direction[0][0]
        elif abs(direction[0][0] - direction[1][0]) > 1:
            direction = self.KEEP_BPS
        else:
            if direction[0][1] >= len(self.eval_buffer) // 2:
                direction = direction[0][0]
            else:
                direction = self.KEEP_BPS

        self.eval_buffer.clear()

        print('DIRECTION', direction)
        # print('whiteboard', self.whiteboard, self.whiteboard.__dict__)
        # input()
        # print(0/0)

        if direction == self.KEEP_BPS:
            return

        if ((direction == self.DECREASE_BPS and self.qi_id > 0) or
                (direction == self.INCREASE_BPS and self.qi_id < len(self.qi) - 1)):
            self.qi_id += direction
