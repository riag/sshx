# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.


import socket
import os
import sys
from paramiko.py3compat import u

# windows does not have termios...
try:
    import termios
    import tty
    from getch import getch, getche

    has_termios = True
except ImportError:
    import colorama
    from msvcrt import getch, getche

    has_termios = False

ENTER = 0x0D


def interactive_shell(chan):
    if has_termios:
        posix_shell(chan)
    else:
        colorama.init()
        windows_shell(chan)
        colorama.deinit()

        import win32api
        win32api.keybd_event(ENTER, 0, 0, 0)


def posix_shell(chan):
    import select

    oldtty = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        chan.settimeout(0.0)

        while True:
            r, w, e = select.select([chan, sys.stdin], [], [])
            if chan in r:
                try:
                    x = chan.recv(1024)
                    if len(x) == 0:
                        #sys.stdout.write("\r\n*** EOF\r\n")
                        break
                    
                    sys.stdout.write(x.decode('utf-8'))
                    sys.stdout.flush()
                except socket.timeout:
                    pass
            if sys.stdin in r:
                x = sys.stdin.read(1)
                if len(x) == 0:
                    break
                chan.send(x)
        
                # There will be a '\x1b[44;17R' before every new line.
                # I don't know what it is. Just throw it.
                if x == '\x1b':
                    x = sys.stdin.read(7)
                    #print(x)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)


# thanks to Mike Looijmans for this code
def windows_shell(chan):
    import threading

    sys.stdout.write(
        "Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n"
    )

    def sending(sock):
        try:
            while True:
                d = getch()
                getch()
                if not d:
                    break
                chan.send(d)
        except (EOFError, OSError):
            # connection closed
            pass

    def receiving(sock):
        while True:
            data = sock.recv(256)
            if not data:
                sys.stdout.flush()
                break
            sys.stdout.write(data.decode('utf-8'))
            sys.stdout.flush()

    worker = threading.Thread(target=sending, args=(chan,))
    worker.start()

    receiving(chan)