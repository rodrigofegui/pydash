from collections import Counter
from datetime import datetime
from re import search
from time import perf_counter

from matplotlib import pyplot

from base.configuration_parser import ConfigurationParser
from player.parser import parse_mpd
from r2a.ir2a import IR2A


class R2ASimpleMajority(IR2A):
    def __init__(self, id):
        super().__init__(id)

        self.MIN_throughput_buffer_SZ = 1
        self.MAX_throughput_buffer_SZ = 5

        self.STABILITY_UP = .7
        self.STABILITY_DOWN = 0
        self.INITIAL_QI_ID = .5

        self.DECREASE_BPS = -1
        self.KEEP_BPS = 0
        self.INCREASE_BPS = 1

        self.qi = []
        self.qi_id = None
        self.elapsed_time = None
        self.throughput_buffer_size = 0
        self.throughput_buffer = []

        self.throughputs = []
        self.comp_throughputs = []

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
        self.log_time = datetime.now().isoformat()
        self._plot(
            [(self.throughputs, 'real')],
            'throughput',
            'Throughput',
            'throught',
        )
        self._plot(
            [(self.comp_throughputs, 'comparativo')],
            'comp_throughput',
            'Comparação Throughput',
            'throught',
        )

    def _performance_analyses(self, bit_length):
        # print()
        c_throughput = bit_length // self.elapsed_time
        # print('c_throughput', c_throughput)
        self.throughputs.append(c_throughput)
        c_throughput = round(c_throughput / self.qi[self.qi_id], 3)
        self.comp_throughputs.append(c_throughput)
        # print('c_bandwidth', self.qi[self.qi_id])
        # print('c_throughput', c_throughput)

        if c_throughput < 1 - self.STABILITY_DOWN:
            # print('diminuindo')
            self.throughput_buffer.append(self.DECREASE_BPS)
        elif c_throughput > 1 + self.STABILITY_UP:
            # print('aumentando')
            self.throughput_buffer.append(self.INCREASE_BPS)
        else:
            self.throughput_buffer.append(self.KEEP_BPS)
            # print('mantendo')

        # print()
        # input('ENTER')

    def _set_next_qi_id(self):
        if len(self.throughput_buffer) < self.throughput_buffer_size:
            return

        direction = self._directions_analyses(Counter(self.throughput_buffer).most_common())

        self.throughput_buffer.clear()

        if direction == self.KEEP_BPS:
            return

        if ((direction == self.DECREASE_BPS and self.qi_id > 0) or
                (direction == self.INCREASE_BPS and self.qi_id < len(self.qi) - 1)):
            self.qi_id += direction

    def _directions_analyses(self, distribution):
        return distribution[0][0]

    def _plot(self, data, file_name, title, y_label, x_label='histórico'):
        for axis, label in data:
            x_axis, y_axis = [], []

            for i, value in enumerate(axis):
                x_axis.append(i)
                y_axis.append(value)

            pyplot.plot(x_axis, y_axis, label=label)
            pyplot.xlabel(x_label)
            pyplot.ylabel(y_label)

        pyplot.legend()
        pyplot.title(title)
        pyplot.savefig(f'./results/{file_name}_{self.log_time}.png')
        pyplot.clf()
        pyplot.cla()
        pyplot.close()
