#!/usr/bin/env python
from __future__ import division, print_function

import signature
import symbolic

import sys
import os
from copy import deepcopy
from collections import defaultdict


class GUI(object):
    def __init__(self):
        self.rootpath = ".."
        if os.path.split(os.getcwd())[1] == "src":
            self.rootpath = os.path.join("..", "..")

        self.samplers_init()
        self.signatures_init()
        self.state_init()
        self.UI_init()
        self.UI_setall()
        self.UI_start()

    # state access attributes
    @property
    def calls(self):
        return self.state["calls"]

    @calls.setter
    def calls(self, value):
        self.state["calls"] = value

    # utility
    def log(self, *args):
        print(*args)

    def alert(self, *args):
        print(*args, file=sys.stderr)

    # initializers
    def samplers_init(self):
        self.samplers = {}
        samplerpath = os.path.join(self.rootpath, "Sampler", "build")
        for path, dirs, files in os.walk(samplerpath, followlinks=True):
            if "info.py" in files and "sampler.x" in files:
                with open(os.path.join(path, "info.py")) as fin:
                    system = eval(fin.read())
                system["sampler"] = os.path.join(path, "sampler.x")
                self.samplers[system["name"]] = system
        self.log("loaded", len(self.samplers), "samplers")

    def signatures_init(self):
        self.signatures = {}
        signaturepath = os.path.join(self.rootpath, "GUI", "signatures")
        for path, dirs, files in os.walk(signaturepath, followlinks=True):
            for filename in files:
                if filename[0] == ".":
                    continue
                sig = signature.Signature(file=os.path.join(path, filename))
                self.signatures[str(sig[0])] = sig
        self.log("loaded", len(self.signatures), "signatures")

    def state_init(self):
        self.statefile = os.path.join(self.rootpath, "GUI", ".state.py")
        try:
            with open(self.statefile) as fin:
                self.state = eval(fin.read()) + 1
        except:
            sampler = self.samplers[min(self.samplers)]
            self.state = {
                "sampler": sampler["name"],
                "nt": 1,
                "nrep": 10,
                "usepapi": False,
                "useld": False,
                "usevary": False,
                "userange": False,
                "rangevar": "n",
                "range": (8, 1000, 32),
                "counters": sampler["papi_counters_max"] * [None],
                "samplename": "",
                "calls": [("",)],
                "datascale": 100,
            }
            if "dgemm_" in sampler["kernels"]:
                self.calls[0] = ("dgemm_", "N", "N", 1000, 1000, 1000,
                                 1, "A", 1000, "B", 1000, 1, "C", 1000)
        for callid, call in enumerate(self.calls):
            if call[0] in self.signatures:
                self.calls[callid] = self.signatures[call[0]](*call[1:])
        self.connections_update()
        self.data_update()
        self.state_write()

    # utility type routines
    def state_write(self):
        callobjects = self.calls
        self.calls = map(list, self.calls)
        with open(self.statefile, "w") as fout:
            try:
                import pprint
                print(pprint.pformat(self.state, 4), file=fout)
            except:
                print(repr(self.state), file=fout)
        self.calls = callobjects

    def get_infostr(self):
        sampler = self.samplers[self.state["sampler"]]
        info = "System:\t%s\n" % sampler["system_name"]
        if sampler["backend"] != "local":
            info += "  (via %s(\n" % sampler["backend"]
        info += "  %s\n" % sampler["cpu_model"]
        info += "  %.2f MHz\n" % (sampler["frequency"] / 1e6)
        info += "\nBLAS:\t%s\n" % sampler["blas_name"]
        return info

    def range_eval(self, expr):
        if isinstance(expr, symbolic.Expression):
            rangevar = self.state["rangevar"]
            return [expr(**{rangevar: value})
                    for value in range(*self.state["range"])]
        return [expr]

    # simple data operations
    def data_maxdim(self):
        result = 0
        for data in self.data.itervalues():
            sym = data["sym"]
            if isinstance(sym, symbolic.Prod):
                result = max(result, max(max(self.range_eval(value))
                                         for value in sym[1:]))
            else:
                result = max(result, max(self.range_eval(sym)))
        return result

    # inference system
    def infer_lds(self, callid=None):
        if callid is None:
            for callid in range(len(self.calls)):
                self.infer_lds(callid)
            return
        call = self.calls[callid]
        call2 = call.copy()
        for i, arg in enumerate(call2.sig):
            if isinstance(arg, (signature.Ld, signature.Inc)):
                call2[i] = None
        call2.complete()
        for i, arg in enumerate(call2.sig):
            if isinstance(arg, (signature.Ld, signature.Inc)):
                if self.state["useld"] and not isinstance(call2[i],
                                                          symbolc.Expression):
                    call[i] = max(call2[i], call[i])
                else:
                    call[i] = call2[i]

    def data_update(self, callid=None):
        if callid is None:
            self.data = {}
            for callid in range(len(self.calls)):
                self.data_update(callid)
            return
        call = self.calls[callid]
        compcall = call.copy()
        mincall = call.copy()
        symcall = call.copy()
        for argid, arg in enumerate(call.sig):
            if isinstance(arg, signature.Data):
                compcall[argid] = None
                mincall[argid] = None
                symcall[argid] = None
            elif isinstance(arg, (signature.Ld, signature.Inc)):
                mincall[argid] = None
                symcall[argid] = None
            elif isinstance(arg, signature.Dim):
                symcall[argid] = symbolic.Symbol("." + arg.name)
        compcall.complete()
        mincall.complete()
        symcall.complete()
        argdict = {"." + arg.name: value for arg, value in zip(call.sig, call)}
        argnamedict = {"." + arg.name: symbolic.Symbol(arg.name)
                       for arg in call.sig}
        for argid in call.sig.dataargs():
            if call[argid] is None:
                continue
            self.data[call[argid]] = {
                "comp": compcall[argid],
                "min": mincall[argid],
                "sym": symcall[argid].substitute(**argdict),
                "symnames": symcall[argid].substitute(**argnamedict)
            }
        # TODO: attributes (upper, lower, ...)

    def connections_update(self):
        # compute symbolic sizes for all calls
        sizes = defaultdict(list)
        for callid, call in enumerate(self.calls):
            symcall = call.copy()
            for argid, arg in enumerate(call.sig):
                if isinstance(arg, signature.Dim):
                    symcall[argid] = symbolic.Symbol((callid, argid))
                elif isinstance(arg, (signature.Ld, signature.Inc,
                                      signature.Data)):
                    symcall[argid] = None
            symcall.complete()
            for argid in call.sig.dataargs():
                datasize = symcall[argid]
                if isinstance(datasize, symbolic.Prod):
                    datasize = datasize[1:]
                elif isinstance(datasize, symbolic.Symbol):
                    datasize = [datasize]
                else:
                    self.alert("don't know how to handle datasize for",
                               call.sig[argid], "in", call.sig, ":", datasize)
                datasize = [size.name for size in datasize]
                sizes[call[argid]].append(datasize)
        # deduce connections from symbolic sizes for each dataname
        connections = {
            (callid, argid): set([(callid, argid)])
            for callid, call in enumerate(self.calls)
            for argid in range(len(call))
        }
        # combine connections for each data item
        for datasizes in sizes.values():
            for idlist in zip(*datasizes):
                baseid = idlist[0]
                for callargid in idlist[1:]:
                    connections[baseid] |= connections[callargid]
                    for callargid2 in connections[callargid]:
                        connections[callargid2] = connections[baseid]
        # TODO: lds as connections?
        self.connections = connections

    def connections_apply(self, callid, argid=None):
        if argid is None:
            argids = range(len(self.calls[callid]))
        else:
            argids = [argid]
        for argid in argids:
            value = self.calls[callid][argid]
            for callid2, argid2 in self.connections[(callid, argid)]:
                self.calls[callid2][argid2] = value

    # treat changes for the calls
    def sampler_set(self, samplername):
        self.state["sampler"] = samplername
        sampler = self.samplers[samplername]
        self.state["nt"] = max(self.state["nt"], sampler["nt_max"])

        # update countes (kill unavailable, adjust length)
        papi_counters_max = sampler["papi_counters_max"]
        self.state["usepapi"] &= papi_counters_max > 0
        counters = []
        for counter in self.state["counters"]:
            if counter in sampler["papi_counters_avail"]:
                counters.append(counter)
        counters = counternames[:papi_counters_max]
        counters += (papi_counters_max - len(counternames)) * [None]
        self.state["counters"] = counternames

        # remove unavailable calls
        # TODO

        # update UI
        self.UI_nt_setmax()
        self.UI_nt_set()
        self.UI_usepapi_setenabled()
        self.UI_usepapi_set()
        self.UI_counters_setoptions()
        self.UI_counters_set()
        self.UI_calls_init()

    def routine_set(self, callid, value):
        if value in self.signatures:
            # TODO: default argument values
            call = self.signatures[value]()
            for i, arg in enumerate(call.sig):
                if isinstance(arg, signature.Dim):
                    call[i] = 1000
                elif isinstance(arg, signature.Data):
                    for name in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        if name not in self.data:
                            call[i] = name
                            self.data[name] = None
                            break
            self.calls[callid] = call
            self.infer_lds(callid)
            self.data_update()
        else:
            self.calls[callid] = [value]
        self.UI_call_set(callid, 0)
        self.state_write()

    def arg_set(self, callid, argid, value):
        call = self.calls[callid]
        arg = call.sig[argid]
        if isinstance(arg, signature.Flag):
            call[argid] = value
            self.connections_update()
            self.connections_apply(callid)
            self.UI_calls_set(callid, argid)
            self.UI_data_viz()
        elif isinstance(arg, signature.Scalar):
            if isinstance(arg, (signature.sScalar, signature.dScalar)):
                try:
                    call[argid] = float(value)
                except:
                    call[argid] = None
            else:
                try:
                    call[argid] = complex(value)
                except:
                    call[argid] = None
        elif isinstance(arg, signature.Dim):
            # evaluate value
            try:
                if self.state["userange"]:
                    var = self.state["rangevar"]
                    value = eval(value, {}, {var: symbolic.Symbol(var)})
                else:
                    value = int(eval(value, {}, {}))
            except:
                value = None
            call[argid] = value
            self.connections_apply(callid, argid)
            self.infer_lds()
            self.data_update()
            self.UI_calls_set(callid, argid)
            self.UI_data_viz()
        elif isinstance(arg, signature.Data):
            if not value:
                value = None
            if value in self.data:
                # resolve potential conflicts
                self.data_override(callid, argid, value)
            else:
                call[argid] = value
                self.connections_update()
                self.data_update()
                self.UI_call_set(callid, argid)
        elif isinstance(arg, (signature.Ld, signature.Inc)):
            # TODO: proper ld treatment
            call[argid] = int(value) if value else None
            self.data_update()
        self.state_write()

    # catch and handle data conflicts
    def data_override(self, callid, argid, value):
        call = self.calls[callid]
        oldvalue = call[argid]  # backup
        # apply change and check consistency
        call[argid] = value
        self.connections_update()
        for argid2, value2 in enumerate(call):
            if not all(value2 == self.calls[callid3][argid3] for callid3,
                       argid3 in self.connections[(callid, argid2)]):
                # inconsistency: restore backup and query override
                call[argid] = oldvalue
                self.connections_update()
                self.UI_choose_data_override(callid, argid, value)
                return

    def data_override_ok(self, callid, argid, value):
        self.calls[callid][argid] = value
        self.connections_update()
        for callid2 in range(len(self.calls)):
            if callid2 != callid:
                self.connections_apply(callid2)
        self.connections_apply(callid)
        self.infer_lds()
        self.UI_calls_set()

    def data_override_cancel(self, callid, argid, value):
        self.UI_call_set(callid)

    # user interface
    def UI_init(self):
        self.alert("GUI needs to be subclassed")

    def UI_setall(self):
        self.UI_sampler_set()
        self.UI_nt_setmax()
        self.UI_nt_set()
        self.UI_nrep_set()
        self.UI_info_set(self.get_infostr())
        self.UI_usepapi_setenabled()
        self.UI_usepapi_set()
        self.UI_useld_set()
        self.UI_usevary_set()
        self.UI_userange_set()
        self.UI_counters_setvisible()
        self.UI_counters_setoptions()
        self.UI_counters_set()
        self.UI_range_setvisible()
        self.UI_rangevar_set()
        self.UI_range_set()
        self.UI_calls_init()
        self.UI_samplename_set()

    # event handlers
    def UI_sampler_change(self, samplername):
        # TODO: check for missing call routine conflicts
        self.sampler_set(samplername)

    def UI_nt_change(self, nt):
        self.state["nt"] = nt
        self.state_write()

    def UI_nrep_change(self, nrep):
        self.state["nrep"] = nrep
        self.state_write()

    def UI_usepapi_change(self, state):
        self.state["usepapi"] = state
        self.UI_counters_setvisible()
        self.state_write()

    def UI_useld_change(self, state):
        self.state["useld"] = state
        self.UI_useld_apply()
        self.state_write()

    def UI_usevary_change(self, state):
        self.state["usevary"] = state
        self.state_write()
        # TODO

    def UI_counters_change(self, counters):
        self.state["counters"] = counters
        self.state_write()

    def UI_userange_change(self, state):
        self.state["userange"] = state
        self.UI_range_setvisible()
        self.state_write()

    def UI_rangevar_change(self, varname):
        self.state["rangevar"] = varname
        self.state_write()

    def UI_range_change(self, range):
        self.state["range"] = range
        self.state_write()

    def UI_call_add(self):
        self.calls.append([""])
        self.state_write()
        self.UI_calls_init()

    def UI_call_remove(self, callid):
        del self.calls[callid]
        self.connections_update()
        self.state_write()
        self.UI_calls_init()

    def UI_call_moveup(self, callid):
        calls = self.calls
        calls[callid], calls[callid - 1] = calls[callid - 1], calls[callid]
        self.connections_update()
        self.state_write()
        self.UI_calls_init()

    def UI_call_movedown(self, callid):
        calls = self.calls
        calls[callid + 1], calls[callid] = calls[callid], calls[callid + 1]
        self.connections_update()
        self.state_write()
        self.UI_calls_init()

    def UI_arg_change(self, callid, argid, value):
        if argid == 0:
            self.routine_set(callid, value)
        else:
            self.arg_set(callid, argid, value)

    def UI_samplename_change(self, samplename):
        self.state["samplename"] = samplename
        self.state_write()

    def UI_submit_click(self):
        self.alert("submit_click")
