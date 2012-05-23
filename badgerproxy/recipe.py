
import os
import sys
import shutil

import missingbits
from zc.buildout import easy_install


class Recipe(object):

    def __init__(self, buildout, name, options):
        self.name = name
        self.options = options
        self.buildout = buildout

        self.parts_directory = os.path.join(self.buildout['buildout']['parts-directory'], self.name)
        self.var_directory = os.path.join(self.buildout['buildout']['directory'], 'var')

        self.options.setdefault('userconf', os.path.abspath(os.path.join(self.parts_directory, "user.conf")))
        self.options.setdefault('systemconf', os.path.abspath(os.path.join(self.parts_directory, "system.conf")))

    def install(self):
        if not os.path.exists(self.parts_directory):
            os.mkdir(self.parts_directory)
        self.options.created(self.parts_directory)

        shutil.copyfile(self.options["template"], self.options["userconf"])
        self.options.created(self.options["userconf"])

        pprefix = os.path.join(self.var_directory, self.name)

        with open(self.options['systemconf'], "w") as fp:
            fp.write(
                "socket: %(pprefix)s.socket\n"
                "pidfile: %(pprefix)s.pid\n"
                "logfile: %(pprefix)s.log\n"
                "resolver_cache: %(pprefix)s.dns\n"
                "\n"
                ".include:\n"
                "  - user.conf\n" % dict(pprefix=pprefix)
                )
        self.options.created(self.options["systemconf"])

        self.wrapper("", "badgerproxy", "run")
        self.wrapper("ctl", "badgerproxyctl", "run")
        return self.options.created()

    def wrapper(self, postfix, module, call):
        scriptname = self.name + postfix
        bin_directory = self.buildout['buildout']['bin-directory']

        egg_paths = [
            self.buildout["buildout"]["develop-eggs-directory"],
            self.buildout["buildout"]["eggs-directory"],
            ]

        module = "badgerproxy.scripts." + module

        working_set = easy_install.working_set(["badgerproxy"], sys.executable, egg_paths)

        arguments = "'%s'" % self.options['systemconf']

        easy_install.scripts(
            [(scriptname, module, call)],
            working_set,
            sys.executable,
            bin_directory,
            arguments=arguments)

        self.options.created(os.path.join(bin_directory, scriptname))

    update = install

