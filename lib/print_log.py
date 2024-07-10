class PrintLog:
    # ANSI escape codes for colors
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    @classmethod
    def warn(cls, log):
        print(f"{cls.YELLOW}WARNING:{cls.RESET} {log}")