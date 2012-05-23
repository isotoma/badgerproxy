# Copyright 2012 Isotoma Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os

from twisted.internet import reactor, defer
from optparse import OptionParser
from twisted.spread import pb
from twisted.cred.credentials import UsernamePassword

from ..config import load_config

@defer.inlineCallbacks
def _run(config, args):
    factory = pb.PBClientFactory()
    reactor.connectUNIX(config.socket, factory)
    try:
        perspective = yield factory.login(UsernamePassword("guest", "guest"))
        yield perspective.callRemote('add_dns', args[0], args[1], int(args[2]))
        print "Record added"
    except Exception as e:
        print "Error: ", str(e)

    reactor.stop()

def run(configfile=''):
    p = OptionParser("%prog [options] [command]")
    p.add_option("-c", "--config", default=configfile, help="Config file")
    options, args = p.parse_args()

    config = load_config(configfile)

    if not os.path.exists(config.socket):
        print "socket not found - proxy not running?"
        return

    if len(args) != 3:
        print "expected 3 args"
        return

    _run(config, args)
    reactor.run()

