import sys
import time
from threading import Thread


class Spinner(Thread):
    #Set the screen position of the spinner (chars from the left).
    spin_screen_pos = 1
    #Set the current index position in the spinner character list.
    char_index_pos = 0
    #Set the time between character changes in the spinner.
    sleep_time = 1
    #Set the spinner type: 0-3
    spin_type = 2

    def __init__(self, type=spin_type):
        Thread.__init__(self)
        self.setDaemon(True)
        self.stop_spinner = False
        self.stopped = False
        if type == 0:
            self.char = ['O', 'o', '-', 'o', '0']
        elif type == 1:
            self.char = ['.', 'o', 'O', 'o', '.']
        elif type == 2:
            self.char = ['|', '/', '-', '\\', '-']
        else:
            self.char = ['*', '#', '@', '%', '+']
        self.len = len(self.char)

    def Print(self, crnt):
        str, crnt = self.curr(crnt)
        sys.stdout.write("\b \b%s" % str)
        sys.stdout.flush()  # Flush stdout to get output before sleeping!
        time.sleep(self.sleep_time)
        return crnt

    def curr(self, crnt):
        """
        Iterator for the character list position
        """
        if crnt == 4:
            return self.char[4], 0
        elif crnt == 0:
            return self.char[0], 1
        else:
            test = crnt
            crnt += 1
        return self.char[test], crnt

    def done(self):
        sys.stdout.write("\b \b\n")

    def stop(self):
        self.stop_spinner = True
        while not self.stopped:
            time.sleep(0.5)  # give time for run to get the message

    def run(self):
        # the comma keeps print from ending with a newline.
        print " " * self.spin_screen_pos,
        while True:
            if self.stop_spinner:
                self.done()
                self.stopped = True
                return
            self.char_index_pos = self.Print(self.char_index_pos)

    def test(self, sleep=3.4):
        print 'Waiting for process...',
        self.start()
        time.sleep(sleep)
        self.stop()
        print 'Process is finished...'

if __name__ == "__main__":
    for i in range(0, 10):
        s = Spinner()
        s.test(sleep=float('3.' + str(i)))
