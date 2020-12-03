from r2a.r2asimplemajority import R2ASimpleMajority


class R2ADemocraticAndBufferSize(R2ASimpleMajority):
    def _directions_analyses(self, distribution):
        direction = self.DECREASE_BPS

        if self.whiteboard.get_amount_video_to_play() <= self.throughput_buffer_size:
            direction = self.DECREASE_BPS
        elif len(distribution) == 1:
            direction = distribution[0][0]
        elif abs(distribution[0][0] - distribution[1][0]) > 1:
            direction = self.KEEP_BPS
        else:
            if distribution[0][1] >= len(self.throughput_buffer) // 2:
                direction = distribution[0][0]
            else:
                direction = self.KEEP_BPS

        return direction
