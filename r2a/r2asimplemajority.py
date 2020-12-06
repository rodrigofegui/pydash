from collections import Counter
from re import search
from time import perf_counter

from matplotlib import pyplot

from base.configuration_parser import ConfigurationParser
from player.parser import parse_mpd
from r2a.ir2a import IR2A


class R2ASimpleMajority(IR2A):
    """ABR algorithm based on throughput comparison votes by simple majority."""
    def __init__(self, id):
        super().__init__(id)

        # Throuhput buffer size bounderies
        self.MIN_THROUGHPUT_BUFFER_SZ = 1
        self.MAX_THROUGHPUT_BUFFER_SZ = 5

        # Throughput start point
        self.INITIAL_QI_ID = .5

        # Stability margin controls
        self.STABILITY_UP = .7
        self.STABILITY_DOWN = 0

        # Available directions
        self.DECREASE_BPS = -1
        self.KEEP_BPS = 0
        self.INCREASE_BPS = 1

        # Throughput qualities store
        self.qi = []
        self.qi_id = None

        # Intermediate to calculate the current throughput
        self.elapsed_time = None

        # Throughput buffer control
        self.throughput_buffer_size = 0
        self.throughput_buffer = []

        # History
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

        self._performance_analyses(msg.bit_length)

        self._set_next_qi_id()

        self.send_up(msg)

    def initialize(self):
        """Calculating the buffer size, based on segment periods"""
        settings = ConfigurationParser.get_instance()
        period = int(search(r'(\d+)sec', settings.get_parameter('url_mpd')).groups()[0])

        self.throughput_buffer_size = max(self.MIN_THROUGHPUT_BUFFER_SZ, self.MAX_THROUGHPUT_BUFFER_SZ // period)

    def finalization(self):
        """History plots"""
        self._plot(
            [(self.throughputs, 'real')],
            'throughput_v2',
            'Throughput',
            'throught',
        )
        self._plot(
            [(self.comp_throughputs, 'comparativo')],
            'comp_throughput',
            'Comparação Throughput',
            'throughput_v2',
        )

    def _performance_analyses(self, bit_length):
        """Calculating the current throughput and checking its proportion
        to the current quality bitrate as follow:

        - If proportion is lower than `STABILITY_DOWN`: `DECREASE_BPS`
        - If proportion is higher than `STABILITY_UP`: `INCREASE_BPS`
        - Otherwise: `KEEP_BPS`

        Args:
        - `int:bit_lenght`: Response lenght in bits
        """
        c_throughput = bit_length // self.elapsed_time
        self.throughputs.append(c_throughput)
        c_throughput = round(c_throughput / self.qi[self.qi_id], 3)
        self.comp_throughputs.append(c_throughput)

        if c_throughput < 1 - self.STABILITY_DOWN:
            self.throughput_buffer.append(self.DECREASE_BPS)
        elif c_throughput > 1 + self.STABILITY_UP:
            self.throughput_buffer.append(self.INCREASE_BPS)
        else:
            self.throughput_buffer.append(self.KEEP_BPS)

    def _set_next_qi_id(self):
        """Selecting the next quality bitrate, only when the buffer is full."""
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
        """Getting the most common vote.

        Args:
        - `list:distribution`: Comparison throughput vote distribution

        Return:
        - Suggested direction
        """
        return distribution[0][0]

    def _plot(self, data, file_name, title, y_label, x_label='histórico'):
        """Plotting data into a .PNG image."""
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
        pyplot.savefig(f'./results/{self.__class__.__name__}_{file_name}.png')
        pyplot.clf()
        pyplot.cla()
        pyplot.close()
