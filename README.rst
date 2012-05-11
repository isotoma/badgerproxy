badgerproxy
===========

This is a HTTP proxy that supports content rewriting of HTTP and HTTPS traffic
that passes through. Note that rewriting HTTPS obviously means SSL is stripped
and reapplied. The SSL certificate that is used to reencrypt will be invalid.

There are 2 ways to set up a development environment. You can use buildout::

    $ python bootstrap.py
    $ bin/buildout

A ``badgerproxy`` and ``badgerproxyctl`` script will be created in the bin/
directory.

You can also use virtualenv::

    $ virtualenv --no-site-packages .
    $ source ./bin/active
    $ python setup.py develop


To run a server in foreground::

    $ badgerproxy -c badger-sample start -n

``badger-sample`` is a Yay file in the root of the repository that contains a
description of which services and triggers to start with the main service. It
looks something like this::

    socket: /var/local/badgerproxy/var/badgerproxy.sock

    services:
      - listen: localhost:8084
        methods:
            allowed:
              - HEAD
              - POST
              - GET
              - CONECT

        ports:
            allowed:
              - 80
              - 443

        rewriter:
            cls: badgerproxy.rewriting.waraningbanner
            image: https://www.myhost.com/images/banner.gif

      - listen: localhost:8084
        methods:
            allowed:
              - CONNECT

        ports:
            allowed:
              - 22


To dynamically add an allowed URL::

    $ badgerproxyctl -s /var/local/badgerproxy/var/badgerproxy.sock add-dns www.wibble.com 4.4.4.4 60

