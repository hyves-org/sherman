from shermanfeature import ShermanFeature

import re


class Feature(ShermanFeature):

    @ShermanFeature.priority(90)
    def sourcesLoaded(self, locale, moduleName, modulePath):
        module = self.currentBuild.files[locale][moduleName]
        namespace = module["__manifest__"]["namespace"]

        varReplacer = re.compile(r"^(?:var )?([a-zA-Z0-9.\[\]\"']+) = ", flags = re.MULTILINE)
        functionReplacer = re.compile(r"^function ([a-zA-Z0-9]+)\(", flags = re.MULTILINE)

        for source in module["__manifest__"]["sources"]:
            if "excludeFromNamespace" in source and source["excludeFromNamespace"] == True:
                continue

            path = self.projectBuilder.resolveFile(source["path"], modulePath + "/js")

            js = module[path]
            js = varReplacer.sub(r"%s.\1 = " % namespace, js)
            if js.find("%s.%s." % (namespace, namespace)) != -1:
                continue # abort! abort! processing the same file twice now...
            js = functionReplacer.sub(r"%s.\1 = function \1(" % namespace, js)
            module[path] = js

    @ShermanFeature.priority(80)
    def sourcesConcatenated(self, locale, moduleName, modulePath):
        if moduleName == "inline":
            return

        module = self.currentBuild.files[locale][moduleName]

        bootNs = self.currentBuild.files[locale]["boot"]["__manifest__"]["namespace"]
        moduleNs = module["__manifest__"]["namespace"]

        js = module["__concat__"]

        if moduleName == "boot" or bootNs != moduleNs:
            if bootNs != moduleNs and "modules" in self.projectBuilder.features:
                moduleReplacer = re.compile(r"^ *Modules\.", flags = re.MULTILINE)
                js = moduleReplacer.sub("%sModules." % (bootNs + "."), js)
            js = ("var %s = %s || {};\n"
                  "%s.NS = %s;\n"
                  "with (%s) {\n%s\n}\n" % (moduleNs, moduleNs, moduleNs, moduleNs, moduleNs, js))
        else:
            js = ("with (%s) {\n"
                  "%s\n}\n" % (moduleNs, js))

        module["__concat__"] = js

    @ShermanFeature.priority(90)
    def generateBootstrapCode(self, locale, bootstrapCode):
        bootNs = self.currentBuild.files[locale]["boot"]["__manifest__"]["namespace"]
        if "core" in self.currentBuild.files[locale]:
            coreNs = self.currentBuild.files[locale]["core"]["__manifest__"]["namespace"]
            if bootNs == coreNs:
                coreNsPrefix = ""
            else:
                coreNsPrefix = coreNs + "."
        else:
            # there is no core module, so assume we can
            # fit it all into a single boot module
            coreNs = bootNs
            coreNsPrefix = ""

        bootstrapCode["head"] = (
            "var %(bootNs)s=%(bootNs)s||{};"
            "with(%(bootNs)s){"
            "%(head)s"
        ) % {
            "bootNs": bootNs,
            "head": bootstrapCode["head"]
        }

        bootstrapCode["body"] = (
            "with(%(bootNs)s){"
            "%(body)s"
            "}"
        ) % {
            "bootNs": bootNs,
            "body": bootstrapCode["body"].replace("Application", coreNsPrefix + "Application")
        }

        bootstrapCode["tail"] = (
            "%(tail)s"
            "}"
        ) % {
            "tail": bootstrapCode["tail"]
        }
