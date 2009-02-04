#!/usr/bin/python

from threading import Thread
import sys, time

class Spinner(Thread):
    spin_screen_pos = 0     #Set the screen position of the spinner (chars from the left).
    char_index_pos = 0      #Set the current index position in the spinner character list.
    sleep_time = 1       #Set the time between character changes in the spinner.
    spin_type = 2          #Set the spinner type: 0-3

    def __init__(self, type=spin_type):
        Thread.__init__(self)
        self.stop = False
        if type == 0:
            self.char = ['O', 'o', '-', 'o','0']
        elif type == 1:
            self.char = ['.', 'o', 'O', 'o','.']
        elif type == 2:
            self.char = ['|', '/', '-', '\\', '-']
        else:
            self.char = ['*','#','@','%','+']
            self.len  = len(self.char)

    def Print(self,crnt):
        str, crnt = self.curr(crnt)
        sys.stdout.write("\b \b%s" % str)
        sys.stdout.flush() #Flush stdout to get output before sleeping!
        time.sleep(self.sleep_time)
        return crnt

    def curr(self,crnt): #Iterator for the character list position
        if crnt == 4:
            return self.char[4], 0
        elif crnt == 0:
            return self.char[0], 1
        else:
            test = crnt
            crnt += 1
        return self.char[test], crnt

    def done(self):
        sys.stdout.write("\b \b")
    
    def run(self):
        print " " * self.spin_screen_pos, #the comma keeps print from ending with a newline.
        while True:
            if self.stop:
                self.done()
                break
            self.char_index_pos = self.Print(self.char_index_pos)

if __name__ == "__main__":
    s = Spinner()
    print 'Waiting for cluster...',
    s.start()
    time.sleep(3)
    s.stop = True
