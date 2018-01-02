
import sys
import time

def make_list_strings(n):
    lst = []
    for _i in range(n):
        lst.append(' ' * 1024)
    time.sleep(0.25)
    return lst

def trim_list(lst, length):
    while len(lst) > length:
        lst.pop()
    time.sleep(0.15)
    return lst

def just_sleep(t):
    time.sleep(t)

def main():
    for _i in range(3):
        l = make_list_strings(1024 * 10)
        just_sleep(0.5)
        trim_list(l, 128)
        just_sleep(0.2)
    return 0

if __name__ == '__main__':
    sys.exit(main())
