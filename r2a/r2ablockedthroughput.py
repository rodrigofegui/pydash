from collections import Counter
from re import search
from time import perf_counter

from base.configuration_parser import ConfigurationParser
from player.parser import parse_mpd
from r2a.ir2a import IR2A


class R2ABlockedThroughput(IR2A):
    def __init__(self, id):
        super().__init__(id)

        self.MIN_throughput_buffer_SZ = 1
        self.MAX_throughput_buffer_SZ = 5

        self.STABILITY_PERC = .2
        self.INITIAL_QI_ID = .5

        self.DECREASE_BPS = -1
        self.KEEP_BPS = 0
        self.INCREASE_BPS = 1

        self.qi = []
        self.qi_id = None
        self.elapsed_time = None
        self.throughput_buffer_size = 0
        self.throughput_buffer = []

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.qi = parse_mpd(msg.get_payload()).get_qi()
        self.qi_id = int(len(self.qi) * self.INITIAL_QI_ID)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        msg.add_quality_id(self.qi[self.qi_id])

        self.elapsed_time = perf_counter()

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.elapsed_time = perf_counter() - self.elapsed_time
        # print('-' * 20)
        # print('elapsed_time', self.elapsed_time)
        # print('-' * 20)

        self._performance_analyses(msg.bit_length)

        self._set_next_qi_id()

        self.send_up(msg)

    def initialize(self):
        settings = ConfigurationParser.get_instance()
        period = int(search(r'(\d+)sec', settings.get_parameter('url_mpd')).groups()[0])

        self.throughput_buffer_size = max(self.MIN_throughput_buffer_SZ, self.MAX_throughput_buffer_SZ // period)

    def finalization(self):
        pass

    def _performance_analyses(self, bit_length):
        # print()
        c_throughput = bit_length // self.elapsed_time
        # print('c_throughput', c_throughput)
        # print('elapsed_time', 1 / self.elapsed_time)
        c_throughput = round(c_throughput / self.qi[self.qi_id], 3)
        # print('c_bandwidth', self.qi[self.qi_id])
        # print('c_throughput', c_throughput)

        if c_throughput < 1 - self.STABILITY_PERC:
            # print('diminuindo')
            self.throughput_buffer.append(self.DECREASE_BPS)
        elif c_throughput > 1 + self.STABILITY_PERC:
            # print('aumentando')
            self.throughput_buffer.append(self.INCREASE_BPS)
        else:
            self.throughput_buffer.append(self.KEEP_BPS)
            # print('mantendo')

        # print()

    def _set_next_qi_id(self):
        if len(self.throughput_buffer) < self.throughput_buffer_size:
            return

        # print()
        # print('throughput_buffer', self.throughput_buffer)

        direction = Counter(self.throughput_buffer).most_common()

        # if self.whiteboard.get_amount_video_to_play() <=  self.throughput_buffer_size:
        #     direction = self.DECREASE_BPS
        # el
        if len(direction) == 1:
            direction = direction[0][0]
        elif abs(direction[0][0] - direction[1][0]) > 1:
            direction = self.KEEP_BPS
        else:
            if direction[0][1] >= len(self.throughput_buffer) // 2:
                direction = direction[0][0]
            else:
                direction = self.KEEP_BPS

        self.throughput_buffer.clear()

        # print('DIRECTION', direction)
        # print()
        # print('whiteboard', self.whiteboard, self.whiteboard.__dict__)
        # input()
        # print(0/0)

        if direction == self.KEEP_BPS:
            return

        if ((direction == self.DECREASE_BPS and self.qi_id > 0) or
                (direction == self.INCREASE_BPS and self.qi_id < len(self.qi) - 1)):
            self.qi_id += direction
