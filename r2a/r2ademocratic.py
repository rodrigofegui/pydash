from r2a.r2asimplemajority import R2ASimpleMajority


class R2ADemocratic(R2ASimpleMajority):
    """ABR algorithm based on throughput comparison votes by weightable democratic votes"""
    def _directions_analyses(self, distribution):
        """Getting the democratic vote as follow:

        - If there was a unanimity: No questions asking
        - If increasing and decreasing bitrate were the top two: Keeping the bitrate  is the answer
        - If there was a majority: Majority is the answer
        - Otherwise: Keeping the bitrate is the answer

        Args:
        - `list:distribution`: Comparison throughput vote distribution

        Return:
        - Suggested direction
        """
        if len(distribution) == 1:
            direction = distribution[0][0]
        elif abs(distribution[0][0] - distribution[1][0]) > 1:
            direction = self.KEEP_BPS
        elif distribution[0][1] >= len(self.throughput_buffer) // 2:
            direction = distribution[0][0]
        else:
            direction = self.KEEP_BPS

        return direction
