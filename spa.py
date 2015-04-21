#!/usr/bin/env python

import os
import sys
import getopt
import pycurl
import math

from stat import *
from datetime import date, datetime, timedelta

import xml.dom.minidom

from StringIO import StringIO

def usage(msg = None):
  if msg is not None: print msg
  print "usage: spa.py -i ~/.identity [--list|--validate|--hint|--update]"
  print "  -u --update      Update current hours."
  print "                   *may take a minute -- SpringAhead's API is slow..."
  print "  -l --list      List current hours."
  print "  -h --hint      Give an hourly hint."
  print "  -v --validate  Validate the current time card against listed."
  sys.exit(1)

def timeStamp(method):
  start = int(datetime.now().strftime("%s"))
  method()
  stop = int(datetime.now().strftime("%s"))

  return stop - start


# Load/store charge codes.
class ChargeCode:
  def __init__(self, line):
    csv = line.strip().split(',')
    self.code = csv[0]
    self.hours = float(csv[1])
    self.activate = datetime.strptime(csv[2], "%Y-%m-%d")
    self.expire = datetime.strptime(csv[3], "%Y-%m-%d")
    self.hint = (int(csv[4]) != 0)

    self.hours_used = 0.0
    self.hours_remaining = self.hours
    self.timecards = []

  def __getitem__(self, l):
    return self.activate

  @staticmethod
  def sort_codes(left, right):
    if left.hours_remaining <= 0.0:
      return 1
    if right.hours_remaining <= 0.0:
      return -1

    time = (left.expire - right.expire).total_seconds()
    if time > 0:
      return int(left.hours_remaining - right.hours_remaining)
    
    if time < 0.0:
      return -1
    if time > 0.0:
      return 1
    return 0

  def add_timecard(self, tc):
    self.timecards.append(tc)
    tc.set_chargecode(self)

    # Accumulate!!
    hours = float(tc.hours_node.text)
    self.hours_used += hours
    self.hours_remaining -= hours

  @staticmethod
  def load(path):
    codes = []

    with open(path, "r") as handle:
      while True:
        x = handle.readline()
        if not x: break

        codes.append(ChargeCode(x))

    return sorted(codes, key = lambda student: student[2])

  def print_code(self, remaining = False):
    active = self.activate.date().isoformat()
    expire = self.expire.date().isoformat()

    if remaining:
      hours_remaining = self.hours_remaining
      print "%s\t%s\t%s\t%s\t%s" % (self.code, self.hours, hours_remaining,
        active, expire)
    else:
      print "%s\t%s\t%s\t%s" % (self.code, self.hours, active, expire)


class Timecard:
  def __init__(self, card):
    self.first_name_node = Node(card, 'FirstName', 'User')
    self.last_name_node = Node(card, 'LastName', 'User')

    self.hours_node = Node(card, 'HoursDay', 'Timecard')
    self.timecard_date_node = Node(card, 'TimecardDate', 'Timecard')
    self.charge_code_node = Node(card, 'ShortName', 'Project')

    self.submit_date_node = Node(card, 'SubmitDate', 'Timecard')
    self.created_date_node = Node(card, 'CreatedDate', 'Timecard')
    self.modified_date_node = Node(card, 'ModifiedDate', 'Timecard')

  def get_chargecode(self):
    return self.charge_code

  def set_chargecode(self, cc):
    self.charge_code = cc


class Node:
  def __init__(self, root, name, parent):
    if root is None:
      self.valid = False
      return

    self.node = None
    for node in root.getElementsByTagName(name):
      if node.ELEMENT_NODE == node.nodeType:
        if node.parentNode.localName == parent:
          self.node = node

    self.valid = (self.node != None)

    if self.valid:
      if len(self.node.childNodes):
        self.text = self.node.childNodes[0].data
      else:
        self.text = None

      self.name = self.node.localName
      self.parent = self.node.parentNode
      self.parent_name = parent

  def is_valid(self):
    return self.valid


# Handle SA API calls.
class SpringAheadAPI:
  def __init__(self, user_file, codes):
    self.codes = []

    self.load_codes(codes)
    self.load_identity(user_file)

    self.timecard_cache = '%s/.timecards.xml' % os.environ['HOME']
    self.api_url = 'https://api.springahead.com/v1'

  def load_identity(self, user_file):
    if not os.path.isfile(user_file):
      print "User credential file does not exist!"
      print "Default: $HOME/.identity"
      return

    with open(user_file, "r") as handle:
      cred_data = handle.read()
      creds = cred_data.strip('\n').split(':')

      if len(creds) != 2:
        print "Invalid credential file!"
        print "It should be of the format 'company\user:password'."
        print "It should also be 700, so that other users can't access it."
        print "File: %s" % user_file
        sys.exit(1)

      if os.stat(user_file).st_mode & (S_IRWXG | S_IRWXO):
        print "!!! Your identity file should be set to mode 700 !!!"
        sys.exit(1)

      self.user = creds[0]
      self.passwd = creds[1]

  def load_codes(self, codes):
    if not os.path.isfile(codes):
      print "No charge code file is sound!"
      return

    self.codes = ChargeCode.load(codes)

  def get_code(self, ccode):
    for code in codes:

      if ccode == code.code:
        return ccode

    return None

  def request(self, request):
    buffer = StringIO()

    c = pycurl.Curl()

    url = '%s/%s' % (self.api_url, request)

    c.setopt(c.URL, url)

    c.setopt(c.USERPWD, '%s:%s' % (self.user, self.passwd))
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    return buffer.getvalue()


  def update(self):
    if len(self.codes) == 0:
      print "No charge codes are loaded!"
      return

    latest = date.today().isoformat()
    oldest = self.codes[0].activate.date().isoformat()

    print "Request timecard information from %s to %s" % (oldest, latest)

    start = int(datetime.now().strftime("%s"))
    xml = self.request('mytimecard/range/%s/%s' % (oldest, latest))
    stop = int(datetime.now().strftime("%s"))

    duration = stop - start
    print "Time elapsed: %s" % str(timedelta(seconds=duration))

    with open(self.timecard_cache, 'w') as handle: handle.write(xml)


  def populate_timecards(self):
    with open(self.timecard_cache, 'r') as handle: buff = handle.read()

    xxml = xml.dom.minidom.parseString(buff)
    self.timecards_dom = xxml.getElementsByTagName('Timecard')
    self.timecards = []
    self.undefined_codes = set([])

    for card in self.timecards_dom:
      tc = Timecard(card)

      # Find the first matching chargecode and use it.
      text = tc.charge_code_node.text
      code = None

      for ca in self.codes:
        if text.endswith(ca.code):
          ca.add_timecard(tc)
          code = ca
          break

      if code is None:
        self.undefined_codes.add(text)

      self.timecards.append(tc)

  def list_codes(self):
    self.populate_timecards()

    print "Current Charge Codes:"
    print "Code\tHours\tRemains\tActivate\tExpire"
    for code in self.codes: code.print_code(remaining = True)

  def list_cached_codes(self):
    self.populate_timecards()

    print "Cached Charge Codes:"
    print "{0:20}\t{1}".format('Code','Hours Used')
    for code in self.codes:
      print "{0:20}\t{1}".format(code.timecards[0].charge_code_node.text,
        code.hours_used)

  def validate_codes(self):
    self.populate_timecards()

    negs = []
    for cc in self.codes:
      if cc.hours_remaining < 0: negs.append(cc)

    if len(negs) > 0:
      print "Invalid charge codes:"
      print "Charge Code\tRemaining\tActivate\tExpire"
      for cc in negs:
        print "%s\t\t%s\t\t%s\t%s" % (cc.code, cc.hours_remaining,
          cc.activate.date().isoformat(), cc.expire.date().isoformat())
    else:
      print "All timesheet records are valid."

    if len(self.undefined_codes) > 0:
      print "Undefined Codes:"
      for code in self.undefined_codes:
        print "  %s" % code

  def hint_codes(self):
    self.populate_timecards()

    if len(self.codes) == 0:
      print "No charge codes found."
      return

    codes = sorted([c for c in self.codes if c.hint and c.hours_remaining > 0],
      cmp = ChargeCode.sort_codes)

    print "Use chargecode(s):"
    print "  %s\t- %s hours remaining."  % (codes[0].code,
      codes[0].hours_remaining)

    if len(codes) > 1:
      print "  %s\t- %s hours remaining."  % (codes[1].code,
        codes[1].hours_remaining)

def main(argv):
  if len(argv) == 0:
    usage()

  try:
    opts, args = getopt.getopt(argv, 'lcvhui?',
      ['identity=', 'list', 'validate', 'hint', 'update', 'list-cache'])
  except getopt.GetoptError as err:
    usage(str(err))

  operation = None
  userfile = None
  codefile = None
  addcode = []

  for o, a in opts:
    if o in ('-i', '--identity'):
      userfile = a

    elif o in ('-c', '--codefile'):
      codefile = a

    elif o == '-?':
      usage()

    # elif o in ('-a', '--addcode'):
    #   addcode.append(a)


  if userfile is None:
    userfile = "%s/.identity" % os.environ['HOME']

  if codefile is None:
    codefile = "%s/.codes" % os.environ['HOME']

  spa = SpringAheadAPI(userfile, codefile)

  # if len(addcode) > 0:
  #   spa.add_codes(addcode)

  for o, a in opts:
    if o in ('-l', '--list'):
      spa.list_codes()

    elif o in ('-u', '--update'):
      spa.update()

    elif o in ('-v', '--validate'):
      spa.validate_codes()

    elif o in ('-c', '--list-cache'):
      spa.list_cached_codes()

    elif o in ('-h', '--hint'):
      spa.hint_codes()

    else:
      usage("No option specified.")


if '__main__' == __name__:
  main(sys.argv[1:])


