from collections import Counter
from r2a.r2asimplemajority import R2ASimpleMajority


class R2ADemocraticAndBufferSize(R2ASimpleMajority):
    """ABR algorithm based on throughput comparison votes by weightable democratic votes and playback buffer size"""
    def _directions_analyses(self, distribution):
        """Getting the best direction as follow:

        - If playback buffer is lower than current throughput buffer: There is an emergency
        - Otherwise: Inherited behavior from R2ADemocratic

        Args:
        - `list:distribution`: Comparison throughput vote distribution

        Return:
        - Suggested direction
        """
        if self.whiteboard.get_amount_video_to_play() <= self.throughput_buffer_size:
            direction = self.DECREASE_BPS
        elif len(distribution) == 1:
            direction = distribution[0][0]
        elif abs(distribution[0][0] - distribution[1][0]) > 1:
            direction = self.KEEP_BPS
        elif distribution[0][1] >= len(self.throughput_buffer) // 2:
            direction = distribution[0][0]
        else:
            direction = self.KEEP_BPS

        return direction

    def _set_next_qi_id(self):
        """Selecting the next quality bitrate, only when at least half buffer is fulfill."""
        history = Counter(self.throughput_buffer).most_common()

        if len(self.throughput_buffer) < self.throughput_buffer_size // 2:
            return
        elif len(history) == 1:
            direction = history[0][0]
        else:
            direction = self._directions_analyses(history)

        self.throughput_buffer.clear()

        if direction == self.KEEP_BPS:
            return

        if ((direction == self.DECREASE_BPS and self.qi_id > 0) or
                (direction == self.INCREASE_BPS and self.qi_id < len(self.qi) - 1)):
            self.qi_id += direction
