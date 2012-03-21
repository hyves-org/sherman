from shermanfeature import ShermanFeature

import os
import re
import types


class Feature(ShermanFeature):

    substitutions = {}

    @ShermanFeature.priority(80)
    def sourcesLoaded(self, locale, moduleName, modulePath):
        if moduleName != "boot":
            return

        UA = self.options["UA"]

        module = self.currentBuild.files[locale][moduleName]

        userAgentJsPath = self.projectBuilder.resolveFile("useragent.js", modulePath + "/js")
        userAgentJs = module[userAgentJsPath]

        if "type" in UA:
            userAgentJs = self.removeMethod("isMobileDevice", userAgentJs)
            userAgentJs = self.removeMethod("isDesktopBrowser", userAgentJs)
            userAgentJs = self.removeMethod("isBot", userAgentJs)
            userAgentJs = self.optimize("isMobileDevice", (UA["type"] == "mobile"), userAgentJs, internal = True)
            userAgentJs = self.optimize("isDesktopBrowser", (UA["type"] == "desktop"), userAgentJs, internal = True)
            userAgentJs = self.optimize("isBot", False, userAgentJs, internal = True)
            userAgentJs = self.stripUAMap("type", UA["type"], userAgentJs)
            self.substitutions["isMobileDevice"] = (UA["type"] == "mobile")
            self.substitutions["isDesktopBrowser"] = (UA["type"] == "desktop")
            self.substitutions["isBot"] = False
        if "platform" in UA:
            userAgentJs = self.removeMethod("isPlatform", userAgentJs)
            userAgentJs = self.optimize("isPlatform", UA["platform"], userAgentJs, internal = True)
            userAgentJs = self.stripUAMap("platform", UA["platform"], userAgentJs)
            self.substitutions["isPlatform"] = UA["platform"]
        if "device" in UA:
            userAgentJs = self.removeMethod("isDevice", userAgentJs)
            userAgentJs = self.optimize("isDevice", UA["device"], userAgentJs, internal = True)
            userAgentJs = self.stripUAMap("device", UA["device"], userAgentJs)
            self.substitutions["isDevice"] = UA["device"]
        if "browser" in UA:
            userAgentJs = self.removeMethod("is", userAgentJs)
            userAgentJs = self.optimize("is", UA["browser"], userAgentJs, internal = True)
            userAgentJs = self.stripUAMap("browser", UA["browser"], userAgentJs)
            self.substitutions["is"] = UA["browser"]
        if "supports" in UA:
            for capability in UA["supports"]:
                userAgentJs = self.optimize("supports", capability, userAgentJs, internal = True)
                userAgentJs = self.stripUAMap(capability, True, userAgentJs)
                self.substitutions["supports"] = capability
        if "not-supports" in UA:
            for capability in UA["not-supports"]:
                userAgentJs = self.optimize("!supports", capability, userAgentJs, internal = True)
                userAgentJs = self.stripUAMap(capability, False, userAgentJs)
                self.substitutions["!supports"] = capability
        if "shortcuts" in UA:
            for shortcut in UA["shortcuts"]:
                value = UA["shortcuts"][shortcut]
                userAgentJs = self.removeMethod(shortcut, userAgentJs)
                userAgentJs = self.optimize(shortcut, value, userAgentJs, internal = True)
                self.substitutions[shortcut] = value

        userAgentJs = self.reduceLogicalOperators(userAgentJs)

        userAgentJs = self.reduceUtilityMethods(userAgentJs)

        userAgentJs = self.reduceLogicalOperators(userAgentJs)

        userAgentJs = self.reduceUtilityMethods(userAgentJs)

        userAgentJs = self.reduceLogicalOperators(userAgentJs)

        module[userAgentJsPath] = userAgentJs 

    def optimize(self, methodName, value, js, internal = False):
        prefix = "" if internal else r"(?:\w+\.)?UserAgent\."
        if methodName == "supports":
            js = re.compile(prefix + r"supports\(\s*[\"']%s[\"']\s*\)" % value).sub("true", js)
        elif methodName == "!supports":
            js = re.compile(prefix + r"supports\(\s*[\"']%s[\"']\s*\)" % value).sub("false", js)
        elif type(value) == types.BooleanType:
            js = re.compile(prefix + r"%s\(\)" % methodName).sub("true" if value else "false", js)
        else:
            js = re.compile(prefix + r"%s\(\s*[\"']%s[\"']\s*\)" % (methodName, value)).sub("true", js)
            js = re.compile(prefix + r"%s\(\s*[\"'][\w ]+[\"']\s*\)" % methodName).sub("false", js)

        js = re.compile(r"!\s*true").sub("false", js)
        js = re.compile(r"!\s*false").sub("true", js)

        return js

    def stripUAMap(self, property, value, js):
        start = js.index("var userAgentCapabilities = {")
        end = js.index("};", start) + 2

        newUAMap = oldUAMap = js[start:end]
        newUAMap = re.compile(r"//.*$", flags = re.MULTILINE).sub("", newUAMap)

        # remove now-redundant instances of the correct property
        if type(value) == types.BooleanType:
            newUAMap = re.compile(r"[\"']?%s[\"']?\s*:\s*(?:true|false)\s*,?" % property).sub("", newUAMap)
        else:
            newUAMap = re.compile(r"[\"']?%s[\"']?\s*:\s*[\"']%s[\"]\s*,?" % (property, value)).sub("", newUAMap)

        # clean up rules without properties
        newUAMap = re.compile(r"[\"']?[\w/ .-]+[\"']?\s*:\s*\{[\s,]*\}\s*,?").sub("", newUAMap)

        # remove rules with conflicting properties
        newUAMap = re.compile(r"^.*[\"']?[\w/ .-]+[\"']?\s*:\s*{.*[\"']?%s[\"']?\s*:.*$" % property, flags = re.MULTILINE).sub("", newUAMap)

        # clean up dangling commas
        newUAMap = re.compile(r",\s*(?=[},])").sub("", newUAMap)

        js = js.replace(oldUAMap, newUAMap)

        return js

    def removeMethod(self, methodName, js):
        js = re.compile(r"(?:/\*\*[^{]+\*/)?\s*function\s+%s\s*\(\s*(?:[\w ,]+\s*)?\)\s*\{[^}]*\}" % methodName).sub("", js)

        js = re.compile(r"[\"']%(methodName)s[\"']\s*:\s*%(methodName)s,?" % { "methodName": methodName }).sub("", js)
        js = re.compile(r",\s*(?=[},])").sub("", js)

        return js

    def reduceLogicalOperators(self, js):
        start = 0
        while True:
            match = re.search(r"(true|false|!?\w+\(\s*(?:[\"'][\w ]+[\"']\s*)?\))\s*(\|\||&&)\s*(true|false|!?\w+\(\s*(?:[\"'][\w ]+[\"']\s*)?\))", js[start:])
            if match == None:
                break

            (left, op, right) = match.group(1, 2, 3)
            if op == "||":
                if left == "true" or right == "true":
                    js = js.replace(match.group(0), "true")
                elif left == "false":
                    js = js.replace(match.group(0), right)
                elif right == "false":
                    js = js.replace(match.group(0), left)
                else:
                    start = js.find(match.group(0), start) + len(match.group(0))
            elif op == "&&":
                if left == "false" or right == "false":
                    js = js.replace(match.group(0), "false")
                elif left == "true":
                    js = js.replace(match.group(0), right)
                elif right == "true":
                    js = js.replace(match.group(0), left)
                else:
                    start = js.find(match.group(0), start) + len(match.group(0))

            js = re.compile(r"(\|\||&&)(\s*)\(\s*(true|false)\s*\)").sub(r"\1\3", js)
            js = re.compile(r"\(\s*(true|false)\s*\)(\s*)(\|\||&&)").sub(r"\1\3", js)

            js = re.compile(r"!\s*true").sub("false", js)
            js = re.compile(r"!\s*false").sub("true", js)

        return js

    def reduceUtilityMethods(self, js):
        while True:
            match = re.search(r"(?:/\*\*[^{]+\*/)?\s*function\s+(\w+)\s*\(\s*\)\s*\{\s*return\s+(true|false)\s*;?\s*\}", js)
            if match == None:
                break

            (methodName, value) = match.group(1, 2)
            self.substitutions[methodName] = (value == "true")

            js = js.replace(match.group(0), "")
            js = self.removeMethod(methodName, js)
            js = self.optimize(methodName, value == "true", js, internal = True)

        return js

    @ShermanFeature.priority(80)
    def sourcesConcatenated(self, locale, moduleName, modulePath):
        UA = self.options["UA"]

        print "    Optimizing JavaScript for %s..." % (UA["device"] if "device" in UA else UA["platform"])

        module = self.currentBuild.files[locale][moduleName]

        js = module["__concat__"]

        for methodName in self.substitutions:
            value = self.substitutions[methodName]
            js = self.optimize(methodName, value, js)

        module["__concat__"] = js 