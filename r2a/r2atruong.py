from datetime import datetime
from math import exp
from time import perf_counter

from matplotlib import pyplot
from numpy import abs, asarray

from player.parser import parse_mpd
from r2a.ir2a import IR2A


class R2ATruong(IR2A):
    """
    Based on: Adaptive Streaming of Audiovisual Content using MPEG DASH
    Authors: Truong Cong Thang, Member, IEEE, Quang-Dung Ho, Jung Won Kang,
    Anh T. Pham, Senior Member, IEEE
    """
    def __init__(self, id):
        super().__init__(id)

        self.INITIAL_QI_ID = .65

        self.LOGISTIC_GROWTH_RATE = 21
        self.LOGISTIC_MIDPOINT = .2

        self.SAFETY_MARGIN = .1

        self.elapsed_time = 0

        self.qi = []
        self.qi_id = 0

        self.throughputs = []
        self.estimated_throughputs = []

        self.smoother = 0
        self.normalizer = 0

        self.log_time = 0

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.qi = parse_mpd(msg.get_payload()).get_qi()

        self.qi_id = int(len(self.qi) * self.INITIAL_QI_ID)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        msg.add_quality_id(self.qi[self.qi_id])

        self._feature_extraction()

        self.elapsed_time = perf_counter()

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.elapsed_time = perf_counter() - self.elapsed_time

        self._controller(msg.bit_length)

        self._throughput_estimation()

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        self.log_time = datetime.now().isoformat()
        self._plot(
            [(self.throughputs, 'real'), (self.estimated_throughputs, 'estimado')],
            'comparacao_throughput',
            'Comparação Throughput',
            'throught_v3',
        )

    def _feature_extraction(self):
        if not self.throughputs:
            return

        self.normalizer = abs(self.throughputs[-1]  - self.estimated_throughputs[-1]) / self.estimated_throughputs[-1]

        self.smoother = 1 / (1 + exp(-(self.LOGISTIC_GROWTH_RATE * (self.normalizer - self.LOGISTIC_MIDPOINT))))

    def _controller(self, bit_length):
        self.throughputs.append(bit_length // self.elapsed_time)

        throughput_buffer_sz = len(self.throughputs)

        if throughput_buffer_sz == 1:
            self.estimated_throughputs.append(self.throughputs[-1])
        elif throughput_buffer_sz <= 3:
            self.estimated_throughputs.append(self.throughputs[-2])
        else:
            self.estimated_throughputs.append(
                ((1 - self.smoother) * self.estimated_throughputs[-2]) + (self.smoother * self.throughputs[-2])
            )

    def _throughput_estimation(self):
        bitrate = (1 - self.SAFETY_MARGIN) * self.estimated_throughputs[-1]

        self.qi_id = self._nth_closest(bitrate)

    def _nth_closest(self, bitrate):
        return abs(asarray(self.qi) - bitrate).argmin()

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
