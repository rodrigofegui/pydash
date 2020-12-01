from collections import Counter

from r2a.r2ablockedthroughput import R2ABlockedTroughput


class R2ASemiBlockedThroughput(R2ABlockedTroughput):
    def _set_next_qi_id(self):
        if len(self.throughput_buffer) < self.throughput_buffer_size:
            return

        direction = Counter(self.throughput_buffer).most_common()

        if self.whiteboard.get_amount_video_to_play() <=  self.throughput_buffer_size:
            direction = self.DECREASE_BPS
        elif len(direction) == 1:
            direction = direction[0][0]
        elif abs(direction[0][0] - direction[1][0]) > 1:
            direction = self.KEEP_BPS
        else:
            if direction[0][1] >= len(self.throughput_buffer) // 2:
                direction = direction[0][0]
            else:
                direction = self.KEEP_BPS

        self.throughput_buffer.clear()

        if direction == self.KEEP_BPS:
            return

        if ((direction == self.DECREASE_BPS and self.qi_id > 0) or
                (direction == self.INCREASE_BPS and self.qi_id < len(self.qi) - 1)):
            self.qi_id += direction
