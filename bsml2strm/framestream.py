import Queue
import collections
import itertools
import struct

import numpy as np


BYTE_ORDER_MARK   = u'\uFEFF'
BYTE_ORDER_TEXT   = '%8g' % ord(BYTE_ORDER_MARK)
BYTE_ORDER_BINARY = struct.pack('f', ord(BYTE_ORDER_MARK))

format_text   = np.frompyfunc(lambda x: '%8g' % x, 1, 1)
format_binary = np.frompyfunc(lambda x: struct.pack('f', x), 1, 1)


class DataBuffer(object):
#========================

  def __init__(self, binary=False):
  #--------------------------------
    self._binary = binary
    self._queue = Queue.Queue()
    self._data = [ ]
    self._datalen = 0
    self._pos = 0

  def put(self, data):
  #-------------------
    self._queue.put(data)

  def __iter__(self):
  #------------------
    while True:
      while self._pos >= self._datalen:
        data = self._queue.get()
        if data is None: raise StopIteration
        self._data = format_binary(data) if self._binary else format_text(data)
        self._datalen = len(data)
        self._pos = 0
      self._pos += 1
      d = self._data[self._pos - 1]
      ## Data could be a 2-D (or higher?) array.
      if self._binary:
        yield d if not isinstance(d, np.ndarray) else ''.join(d.flatten().tolist())
      else:
        yield d if isinstance(d, str) else ' '.join(d.flatten().tolist())


class TextBuffer(object):
#========================

  def __init__(self, binary=False):
  #--------------------------------
    self._binary = binary
    self._queue = collections.deque()  # We don't need a Queue() since we never
    self._data = [ ]                   # wait if no text to send.
    self._pos = 0

  def put(self, text):
  #-------------------
    self._queue.append(text)

  def __iter__(self):
  #------------------
    while True:
      d = None
      while len(self._data) == 0:
        if len(self._queue) == 0:
          d = BYTE_ORDER_BINARY if self._binary else BYTE_ORDER_TEXT
          break
        text = self._queue.popleft()
        if text is None: raise StopIteration
        if self._binary:
          self._data = [ ord(c) for c in text ]
        else:
          self._data = [ '%8g' % ord(c) for c in text ]
        self._pos = 0
      if d is None:
        self._pos += 1
        c = self._data[self._pos - 1]
        d = struct.pack('f', c) if self._binary else c
      yield d


class FrameCounter(object):
#==========================

  def __init__(self):
  #------------------
    self._count = 0

  def __iter__(self):
  #------------------
    while True:
      yield str(self._count)
      self._count += 1


class FrameStream(object):
#=========================

  def __init__(self, channels, no_text=False, binary=False):
  #---------------------------------------------------------
    self._databuf = tuple(DataBuffer(binary) for n in xrange(channels))
    self._textbuf = None if no_text else TextBuffer(binary)
    self._binary = binary

  def put_data(self, channel, data):
  #---------------------------------
    self._databuf[channel].put(data)

  def put_text(self, text):
  #------------------------
    if self._textbuf is not None:
      self._textbuf.put(text)

  def frames(self):
  #----------------
    framecount = FrameCounter()
    try:
      if self._binary:
        if self._textbuf is not None:
          line = itertools.izip(*(self._databuf + (self._textbuf,)))
        else:
          line = itertools.izip(*self._databuf)
        for l in line: yield ''.join(l)
      else:
        if self._textbuf is not None:
          line = itertools.izip(framecount, *(self._databuf + (self._textbuf,)))
        else:
          line = itertools.izip(framecount, *self._databuf)
        for l in line: yield ' '.join(l)
    except StopIteration:
      pass


if __name__ == '__main__':
#=========================

  op = FrameStream(3)
  op.put_data(0, [  1,  2,  3,  4,  5, 6, 7 ])
  op.put_data(1, [ 11, 12, 13, 14, 15 ])
  op.put_data(2, [ 21, 22, 23 ])
  op.put_data(0, [  1,  2,  3,  4,  5, 6, 7 ])
  op.put_data(1, [  1,  2,  3,  4,  5, 6, 7 ])
  op.put_data(2, [  1,  2,  3,  4,  5, 6, 7 ])
  op.put_text('123A')
  op.put_text('123A')
  op.put_data(2, [ 4, 5 ])

  op.put_data(0, None)
  op.put_data(1, None)
  op.put_data(2, None)

  for f in op.frames():
    print f
