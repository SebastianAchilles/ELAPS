#!/usr/bin/env python
from __future__ import division, print_function

import signature
import symbolic
import papi

import sys
import os
import imp
import time
import re
import random
from numbers import Number
from collections import defaultdict
from math import sqrt


class Viewer(object):
    requiresstatetime = 1423087329
    state = {}

    def __init__(self, loadstate=True):
        thispath = os.path.dirname(__file__)
        if thispath not in sys.path:
            sys.path.append(thispath)
        self.rootpath = os.path.abspath(os.path.join(thispath, "..", ".."))
        self.reportpath = os.path.join(self.rootpath, "GUI", "reports")
        self.statefile = os.path.join(self.rootpath, "GUI", ".viewerstate.py")

        self.metrics_init()
        self.stats_init()
        self.reports_init()
        self.plotdata_init()
        self.UI_init()
        self.state_init(loadstate)
        self.UI_setall()

        # load reports from command line
        for arg in sys.argv[1:]:
            if arg[-5:] == ".smpl" and os.path.isfile(arg):
                self.UI_report_load(arg)

    # state access attributes
    def __getattr__(self, name):
        if name in self.__dict__["state"]:
            return self.__dict__["state"][name]
        raise AttributeError("%r object has no attribute %r" %
                             (self.__class__, name))

    def __setattr__(self, name, value):
        if name in self.state:
            self.state[name] = value
        else:
            super(Viewer, self).__setattr__(name, value)

    def start(self):
        self.UI_start()

    # utility
    def log(self, *args):
        print(*args)

    def alert(self, *args):
        print(*args, file=sys.stderr)

    # initializers
    def metrics_init(self):
        self.metrics = {}
        self.metricnames = {}
        metricpath = os.path.join(self.rootpath, "GUI", "src", "metrics")
        for filename in os.listdir(metricpath):
            if not filename[-3:] == ".py":
                continue
            try:
                module = imp.load_source(filename[:-3],
                                         os.path.join(metricpath, filename))
                if hasattr(module, "metric") and hasattr(module, "name"):
                    self.metrics[module.name] = module.metric
                    self.metricnames[module.name] = module.name
                else:
                    self.alert(os.path.relpath(filename),
                               "did not contain a valid metric")
            except:
                self.alert("couldn't load", os.path.relpath(filename))
        self.log("loaded", len(self.metrics), "metrics:",
                 *map(repr, sorted(self.metrics)))
        if len(self.metrics) == 0:
            raise Exception("No metrics found")

    def stats_init(self):
        self.stats_desc = [
            ("med", "median"),
            ("min", "minimum"),
            ("avg", "average"),
            ("max", "maximum"),
            ("min-max", "range: minimum - maximum"),
            ("std", "standard deviation\n(requies avg to be plotted)"),
            ("all", "all data points"),
        ]
        self.stat_funs = {
            "med": lambda l: sum(sorted(l)[
                ((len(l) - 1) // 2):(len(l) // 2 + 1)
            ]) / (2 - len(l) % 2),
            "min": min,
            "avg": lambda l: sum(l) / len(l),
            "max": max,
            "min-max": lambda l: [min(l), max(l)],
            "std": lambda l: sqrt(sum(x ** 2 for x in l) / len(l)
                                  - (sum(l) / len(l)) ** 2),
            "all": lambda l: l
        }

    def reports_init(self):
        self.reports = []
        self.showplots = defaultdict(lambda: defaultdict(lambda: False))
        self.reportid_selected = None
        self.callid_selected = None

    def plotdata_init(self):
        self.plotdata = []
        self.plots_showing = set()
        self.plotrangevar = ""

    def state_init(self, load=True):
        self.state_reset()

    def state_reset(self):
        self.state = {
            "statetime": time.time(),
            "metric_selected": "time [ms]",
            "stats_showing": set(["med"])
        }

    # papi metrics
    def metrics_adddefaultmetric(self, name):
        event = papi.events[name]
        metric = lambda data, report, callid: data.get(name)
        metric.__doc__ = event["long"] + "\n\n    " + name
        self.metrics[name] = metric
        self.metricnames[name] = event["short"]

    # default colors
    def nextcolor(self, colors=[
        "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#00ffff", "#ff00ff",
        "#880000", "#008800", "#000088", "#888800", "#008888", "#880088",
    ]):
        if colors:
            return colors.pop(0)
        "#%06x" % random.randint(0, 0xffffff)

    # report handling
    def report_load(self, filename):
        name = os.path.basename(filename)[:-5]
        errfile = filename + ".err"

        # check for errors
        if os.path.isfile(errfile):
            with open(errfile) as fin:
                lines = fin.readlines()
            if len(lines) == 0:
                self.UI.alerT("report %r is not finished" % name)
            else:
                self.UI_alert("report %r produced errors" % name)
                for line in lines[:10]:
                    self.alert(line.rstrip("\n"))
                if len(lines) > 10:
                    self.alert("[%d more lines]" % (len(lines) - 10))

        fin = open(filename)

        # read header
        evaldir = symbolic.__dict__.copy()
        evaldir.update(signature.__dict__)
        try:
            report = eval(fin.readline(), evaldir)
            report["counters"] = filter(None, report["counters"])
            report["starttime"] = int(fin.readline())
            report["filename"] = filename
        except:
            raise IOError(filename, "doesn't contain a valid report")
        report["filename"] = os.path.relpath(filename)
        report["valid"] = False
        report["endtime"] = None
        report["name"] = name

        rangename_outer = report["userange"]["outer"]
        rangename_inner = report["userange"]["inner"]

        rangevals = None,
        if rangename_outer:
            rangevals = report["ranges"][rangename_outer]
        reportdata = {}
        report["data"] = reportdata
        for rangeval in rangevals:
            innervals = None,
            if rangename_inner == "sum":
                sumrange = report["ranges"]["sum"]
                if rangename_outer:
                    sumrange = sumrange(**{
                        report["rangevars"]["sum"]: rangeval
                    })
                innervals = list(sumrange)
            rangevaldata = []
            reportdata[rangeval] = rangevaldata
            for rep in range(report["nrep"] + 1):
                repdata = {}
                if rep > 0:
                    rangevaldata.append(repdata)
                for innerval in innervals:
                    innervaldata = []
                    repdata[innerval] = innervaldata
                    for call in report["calls"]:
                        try:
                            line = fin.readline()
                        except:
                            self.alert(filename, "is truncated")
                            return report
                        innervaldata.append(tuple(map(int, line.split())))
        reportdata = {key: tuple(map(tuple, val))
                      for key, val in reportdata.iteritems()}
        try:
            report["endtime"] = int(fin.readline())
        except:
            self.alert(name, "was truncated")
            return report
        extralines = fin.readlines()
        if len(extralines):
            self.alert(name, "contained extra lines")
            print(*extralines)
        else:
            report["valid"] = True
        return report

    def report_infostr_HTML(self):
        report = self.reports[self.reportid_selected]
        sampler = report["sampler"]
        result = "<table>"
        result += "<tr><td>File:</td><td>%s</td></tr>" % report["filename"]
        result += "<tr><td>CPU:</td><td>%s</td></tr>" % sampler["cpu_model"]
        if report["userange"]["outer"] == "threads":
            result += (
                "<tr><td>#threads:</td><td>%s</td></tr>"
                % report["ranges"]["threads"]
            )
        else:
            result += "<tr><td>#threads:</td><td>%d</td></tr>" % report["nt"]
        result += "<tr><td>BLAS:</td><td>%s</td></tr>" % sampler["blas_name"]
        if report["valid"]:
            date = time.strftime("%c", time.localtime(report["endtime"]))
            result += "<tr><td>Date:</td><td>%s</td></tr>" % date
        else:
            result += "<tr><td></td><td><b>Invalid Report!</b></td></tr>"
        if report["userange"]["outer"] == "range":
            result += (
                "<tr><td>For each:</td><td>%s = %s</td></tr>"
                % (report["rangevars"]["range"], report["ranges"]["range"])
            )
        if report["userange"]["inner"] == "sum":
            result += (
                "<tr><td>Sum over:</td><td>%s = %s</td></tr>"
                % (report["rangevars"]["sum"], report["ranges"]["sum"])
            )
        elif report["userange"]["inner"] == "omp":
            result += (
                "<tr><td>parallel calls:</td><td>%s = %s</td></tr>"
                % (report["rangevars"]["omp"], report["ranges"]["sum"])
            )
        elif report["options"]["omp"]:
            result += "<tr><td></td><td>Calls in parallel</td></tr>"

        def format_call(call):
            return call[0] + "(" + ", ".join(map(str, call[1:])) + ")"

        if self.callid_selected is None:
            calls = report["calls"]
        else:
            calls = [report["calls"][self.callid_selected]]
        result += "<tr><td>Call%s:</td><td>" % "s"[:len(calls) - 1]
        result += "<br>".join(map(format_call, calls))
        result += "</td></tr>"
        result += "</table>"
        return result

    def report_infostr(self):
        result = self.report_infostr_HTML()
        result = result.replace("</td><td>", "\t")
        result = result.replace("</tr>", "\n")
        result = re.sub("<.*?>", "", result)
        return result

    # data generation
    def get_metricdata(self, reportid, callid, metricname, rangeval=None):
        report = self.reports[reportid]
        # ifrangeval not given: return all
        rangename_outer = report["userange"]["outer"]
        rangename_inner = report["userange"]["inner"]
        if rangename_outer and rangeval is None:
            plotdata = []
            for rangeval in sorted(report["data"]):
                plotdata.append((rangeval, self.get_metricdata(
                    reportid, callid, metricname, rangeval)))
            plotdata = tuple((x, y) for x, y in plotdata if y is not None)
            if not plotdata:
                return None
            return plotdata

        # extract some variables
        rangevaldata = report["data"][rangeval]
        calls = report["calls"]
        metric = self.metrics[metricname]

        # if callid not given: all calls
        callids = (callid,)
        if callid is None:
            callids = range(len(calls))
        data = defaultdict(lambda: None)

        symdict = {}
        if rangename_outer:
            symdict[report["rangevars"][rangename_outer]] = rangeval

        # complexity is constant across repetitions
        if all(isinstance(calls[callid2], signature.Call)
               for callid2 in callids):
            data["complexity"] = 0
            for callid2 in callids:
                call = calls[callid2]
                for innerval in rangevaldata[0]:
                    if rangename_inner:
                        symdict[report["rangevars"][rangename_inner]] = \
                            rangeval
                    complexity = call.complexity()
                    if isinstance(complexity, symbolic.Expression):
                        data["complexity"] += complexity(**symdict)
                    elif isinstance(complexity, Number):
                        data["complexity"] += complexity
                    else:
                        data["complexity"] = None
                        break
                if data["complexity"] is None:
                    break
        else:
            data["complexity"] = None

        # generate plotdata
        plotdata = []
        for repdata in rangevaldata:
            # set up data
            data["rdtsc"] = 0
            if report["usepapi"]:
                for counter in report["counters"]:
                    data[counter] = 0
            for innervaldata in repdata.itervalues():
                data["rdtsc"] += sum(innervaldata[callid][0]
                                     for callid in callids)
                if report["usepapi"]:
                    for counterid, counter in enumerate(report["counters"]):
                        data[counter] += sum(
                            innervaldata[callid][counterid + 1]
                            for callid in callids
                        )
            # call metric
            val = metric(data, report, callid)
            if val is not None:
                plotdata.append(val)
        if not plotdata:
            return None
        plotdata = tuple(plotdata)
        if rangename_outer:
            return plotdata
        return ((None, plotdata),)

    def plotdata_update(self):
        self.plotdata = []
        self.plotcolors = {}
        rangevars = set()
        for reportid, callid in sorted(self.plots_showing):
            rawdata = self.get_metricdata(reportid, callid,
                                          self.metric_selected)
            if not rawdata:
                continue
            linedatas = {
                statname: [(x, self.stat_funs[statname](y))
                           for x, y in rawdata
                           if y is not None]
                for statname in self.stats_showing
            }

            report = self.reports[reportid]

            # rangevar
            if report["userange"]["outer"]:
                rangevars.add(report["rangevars"][report["userange"]["outer"]])

            # name
            name = report["name"]
            if callid is not None:
                name += " (%s)" % report["calls"][callid][0]

            self.plotdata.append((name, linedatas))
            self.plotcolors[name] = report["plotcolors"][callid]
        self.plotrangevar = " = ".join(rangevars)

    # user interface
    def UI_init(self):
        raise Exception("Viewer needs to be subclassed")

    def UI_setall(self):
        self.UI_metrics_update()
        self.UI_metric_set()
        self.UI_stats_set()

    # event handlers
    def UI_report_load(self, filename):
        if any(report["filename"] == filename for report in self.reports):
            self.UI_alert(filename, "already loaded")
            return
        report = self.report_load(filename)
        try:
            report = self.report_load(filename)
        except:
            self.alert("could not load", os.path.relpath(filename))
            return
        reportid = len(self.reports)
        self.reports.append(report)
        report["plotcolors"] = {None: self.nextcolor()}
        for callid in range(len(report["calls"])):
            if len(report["calls"]) == 1:
                report["plotcolors"][0] = report["plotcolors"][None]
            else:
                report["plotcolors"][callid] = self.nextcolor()
        if report["usepapi"]:
            for counter in report["counters"]:
                if counter not in self.metrics:
                    self.metrics_adddefaultmetric(counter)
            self.UI_metriclist_update()
        self.plots_showing.add((reportid, None))
        self.plotdata_update()
        self.UI_report_add()
        self.UI_plot_update()

    def UI_report_select(self, reportid, callid):
        self.reportid_selected = reportid
        self.callid_selected = callid
        self.UI_reportinfo_update()

    def UI_reportcheck_change(self, reportid, callid, state):
        if state:
            self.plots_showing.add((reportid, callid))
        else:
            self.plots_showing.discard((reportid, callid))
        self.plotdata_update()
        self.UI_plot_update()

    def UI_reportcolor_change(self, reportid, callid, color):
        self.reports[reportid]["plotcolors"][callid] = color
        self.UI_report_update(reportid)
        self.plotdata_update()
        self.UI_plot_update()

    def UI_metric_change(self, metric):
        self.metric_selected = metric
        info = self.metrics[metric].__doc__
        if isinstance(info, str):
            self.UI_metricinfo_set(info.strip())
        else:
            self.UI_metricinfo_set("[no docstring for %s]" % metric)
        self.plotdata_update()
        self.UI_plot_update()

    def UI_stat_change(self, statname, state):
        if state:
            self.stats_showing.add(statname)
        else:
            self.stats_showing.discard(statname)
        self.plotdata_update()
        self.UI_plot_update()

    def UI_export(self, filename):
        # data layout
        data = {}
        rows = set()
        cols = set()
        for name, linedatas in self.plotdata:
            for stat, linedata in linedatas.iteritems():
                for rangeval, val in linedata:
                    data[rangeval, name, stat] = val
                    rows.add(rangeval)
                cols.add((name, stat))
        lines = []

        # header
        reportline = ["#"]
        statline = ["# " + self.plotrangevar]
        for name, stat in sorted(cols):
            if name in reportline:
                reportline.append("")
            else:
                reportline.append(name)
            statline.append(stat)
        lines.append(reportline)
        lines.append(statline)

        # content
        for rangeval in sorted(rows):
            line = [str(rangeval)]
            for name, stat in sorted(cols):
                if (rangeval, name, stat) in data:
                    val = data[rangeval, name, stat]
                    if isinstance(val, list):
                        val = ",".join(map(str, val))
                    else:
                        val = str(val)
                    line.append(val)
                else:
                    line.append("NaN")
            lines.append(line)

        # alignment
        colwidths = [max(map(len, col)) for col in zip(*lines)]
        lines[0][0] = lines[0][0].ljust(colwidths[0])
        lines[1][0] = lines[1][0].ljust(colwidths[0])
        lines = [[v.rjust(w) for v, w in zip(l, colwidths)] for l in lines]

        # write file
        with open(filename, "w") as fout:
            for line in lines:
                print(*line, sep="  ", file=fout)
