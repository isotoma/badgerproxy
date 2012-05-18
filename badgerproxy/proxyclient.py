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

from twisted.application import service
from twisted.python import usage
from twisted.internet import reactorfu
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.web import http
from twisted.web.proxy import Proxy, ProxyRequest, ProxyClientFactory, ProxyClient
from twisted.web.proxy import ReverseProxy

from twisted.application import internet
from twisted.application import strports
from twisted.python import log

from StringIO import StringIO
import os
import urlparse

from .error import ForbiddenResponse

banner = """
<style>
HTML {
 padding-top: %(height)s;
 background: url('%(bannerurl)s') 0 0 repeat-x !important;
}
</style>
</head>
"""


def sibpath(asset):
    path = os.path.dirname(__file__)
    return os.path.join(path, asset)

class RewritingProxyClient(ProxyClient):
    def __init__(self, *args, **kwargs):
        ProxyClient.__init__(self, *args, **kwargs)
        self.rewrite = False
        self.length = None
        self.buffer = ''

    def sendHeader(self, name, value):
        log.msg(">>> %s: %s" % (name, value))
        if name.lower() == "accept-encoding":
            value = "identity"
        ProxyClient.sendHeader(self, name, value)

    def handleHeader(self, key, value):
        log.msg("<<< %s: %s" % (key, value))
        if key.lower() == "content-type":
            if value.startswith("text/html"):
                self.rewrite = True
            ProxyClient.handleHeader(self, key, value)
        elif key.lower() == "content-length":
            self.length = value
        else:
            ProxyClient.handleHeader(self, key, value)

    def handleEndHeaders(self):
        if not self.rewrite:
            if self.length:
                ProxyClient.handleHeader(self, "Content-Length", self.length)
            ProxyClient.handleEndHeaders(self)

    def handleResponsePart(self, buffer):
        if self.rewrite:
            self.buffer += buffer
        else:
            ProxyClient.handleResponsePart(self, buffer)

    def handleResponseEnd(self):
        log.msg("handleResponseEnd")
        if self.rewrite:
            banner2 = banner % dict(
                height = self.config['height'],
                bannerurl = self.config['bannerurl'],
                )
            buffer = self.buffer.replace("</head>", banner2)
            ProxyClient.handleHeader(self, "Content-Length", str(len(buffer)))
            ProxyClient.handleEndHeaders(self)
            ProxyClient.handleResponsePart(self, buffer)
            self.rewrite = False
        ProxyClient.handleResponseEnd(self)


class RewritingProxyClientFactory(ProxyClientFactory):
    protocol = RewritingProxyClient

    def buildProtocol(self, addr):
        log.msg("RewritingProxyClientFactory.buildProtocol")
        try:
            module, cls = self.root.config['rewriter']['cls'].split(":")
            protocol = getattr(__import__(module, fromlist=['blah']), cls)
        except KeyError:
            protocol = ProxyClient

        p = protocol(self.command, self.rest, self.version,
	            self.headers, self.data, self.father)

        p.factory = self
        p.root = self.root
        p.config = self.root.config['rewriter']

        return p


class Proxier(object):

    def __init__(self, root, host, port):
        self.root = root

        self.host = host
        self.port = port
        self.ip = root.parent.resolver.lookup(host)

    def permitted(self):
        return self.ip != None

    def get_client_factory(self, method, uri, clientproto, headers, data, response):
        clientFactory = self.protocol(method, uri, clientproto, headers, data, response)
        clientFactory.root = self.root
        clientFactory.proxier = self
        return clientFactory

    def proxy_ssl(self, method, uri, clientproto, headers, data, response):
        cf = self.get_client_factory(method, uri, clientproto, headers, data, response)
        self.reactor.connectSSL(self.ip, self.port, cf, ssl.ClientContextFactory())

    def proxy(self, method, uri, clientproto, headers, data, response):
        cf = self.get_client_factory(method, uri, clientproto, headers, data, response)
        self.reactor.connectTCP(self.ip, self.port, clientFactory)


