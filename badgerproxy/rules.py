
from collections import namedtuple
import ipaddr
from twisted.python import log


class Rule(object):

    def __init__(self, conditions, action):
        self.conditions = conditions
        self.action = action

    def _get_list(self, key):
        value = self.conditions.get(key, [])
        if not isinstance(value, list):
            value = [value]
        return value

    def _compare_network(self, ip, network):
        ip = ipaddr.IPAddress(ip)
        try:
            return ip in ipaddr.IPNetwork(network)
        except ipaddr.AddressValueError:
            try:
                return ip == ipaddr.IPAddress(network)
            except:
                log.err()
        except:
            log.err()

        return False

    def check_source(self, source):
        if not "source" in self.conditions:
            return True

        for n in self._get_list("source"):
            if self._compare_network(source, n):
                return True

        return False

    def check_destination(self, destination):
        if not "destination" in self.conditions:
            return True

        for n in self._get_list("destination"):
            if self._compare_network(destination, n):
                return True

        return False

    def check_port(self, port):
        if not "port" in self.conditions:
            return True

        for p in self._get_list("port"):
            if isinstance(p, int):
                if port == p:
                    return True
                continue

            for rng in p.split(","):
                rng = rng.strip()
                if "-" in rng:
                    start, end = rng.split("-")
                    start, end = int(start.strip()), int(end.strip())
                    if start <= port and port <= end:
                        return True
                else:
                    if port == int(p.strip()):
                        return True

        return False

    def check_method(self, method):
        if not "method" in self.conditions:
            return True

        for m in self._get_list("method"):
            if m.lower() == method.lower():
                return True

        return False

    def check(self, source, destination, port, method):
        log.msg("Checking access: %s %s %s %s" % (source,destination,port,method))
        if not self.check_source(source):
            log.msg(" and source is not allowed")
            return False
        if not self.check_destination(destination):
            log.msg(" and destination is not allowed")
            return False
        if not self.check_port(port):
            log.msg(" and port is not allowed")
            return False
        if not self.check_method(method):
            log.msg(" and method is not allowed")
            return False
        return True


class Rules(object):

    def __init__(self, rules):
        self._rules = []
        for r in rules:
            conditions = r.get("match", {})
            action = r.get("action", "deny")
            self._rules.append(Rule(conditions, action))

    def check(self, source, destination, port, method):
        for i, rule in enumerate(self._rules):
            if rule.check(source, destination, port, method):
                return rule.action
        return "deny"

