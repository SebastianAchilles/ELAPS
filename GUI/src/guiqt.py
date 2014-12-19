#!/usr/bin/env python
from __future__ import division, print_function

from gui import GUI

import sys

from PyQt4 import QtCore, QtGui


class GUI_Qt(GUI, QtGui.QApplication):
    def __init__(self):
        QtGui.QApplication.__init__(self, sys.argv)
        self.setting = False
        GUI.__init__(self)

    def UI_init(self):
        # window
        self.Qt_window = QtGui.QWidget()
        windowL = QtGui.QVBoxLayout()
        self.Qt_window.setLayout(windowL)

        # window > top
        topL = QtGui.QHBoxLayout()
        windowL.addLayout(topL)

        # window > top > setup
        setupL = QtGui.QGridLayout()
        topL.addLayout(setupL)

        # window > top > setup > sampler
        setupL.addWidget(QtGui.QLabel("Sampler:"), 0, 0)
        self.Qt_sampler = QtGui.QComboBox()
        setupL.addWidget(self.Qt_sampler, 0, 1)
        self.Qt_sampler.addItems(sorted(self.samplers.keys()))
        self.Qt_sampler.currentIndexChanged.connect(self.Qt_sampler_change)

        # window > top > setup > nt
        label = QtGui.QLabel("#threads:")
        setupL.addWidget(label, 1, 0)
        self.Qt_nt = QtGui.QComboBox()
        setupL.addWidget(self.Qt_nt, 1, 1)
        self.Qt_nt.currentIndexChanged.connect(self.Qt_nt_change)

        # window > top > setup > nrep
        setupL.addWidget(QtGui.QLabel("repetitions:"), 2, 0)
        self.Qt_nrep = QtGui.QLineEdit()
        setupL.addWidget(self.Qt_nrep, 2, 1)
        self.Qt_nrep.textChanged.connect(self.Qt_nrep_change)
        validator = QtGui.QIntValidator()
        self.Qt_nrep.setValidator(validator)
        validator.setBottom(0)

        # window > top > setup
        setupL.setRowStretch(3, 1)

        # window > top > info
        info = QtGui.QGroupBox()
        topL.addWidget(info)
        infoL = QtGui.QVBoxLayout()
        info.setLayout(infoL)
        self.Qt_info = QtGui.QLabel()
        infoL.addWidget(self.Qt_info)
        self.Qt_info.setWordWrap(True)
        infoL.addStretch(1)

        # window > top > advanced
        advanced = QtGui.QGroupBox("advanced")
        topL.addWidget(advanced)
        advancedL = QtGui.QVBoxLayout()
        advanced.setLayout(advancedL)

        # window > top > advanced > usepapi
        self.Qt_usepapi = QtGui.QCheckBox("use PAPI")
        advancedL.addWidget(self.Qt_usepapi)
        self.Qt_usepapi.stateChanged.connect(self.Qt_usepapi_change)

        # window > top > advanced > useld
        self.Qt_useld = QtGui.QCheckBox("show leading dimensions")
        advancedL.addWidget(self.Qt_useld)
        self.Qt_useld.stateChanged.connect(self.Qt_useld_change)

        # window > top > advanced > usevary
        self.Qt_usevary = QtGui.QCheckBox("change matrices across reps")
        advancedL.addWidget(self.Qt_usevary)
        self.Qt_usevary.stateChanged.connect(self.Qt_usevary_change)

        # window > top > advanced
        advancedL.addStretch(1)

        # window > top > counters
        self.Qt_counters = QtGui.QGroupBox("PAPI counters")
        topL.addWidget(self.Qt_counters)
        countersL = QtGui.QVBoxLayout()
        self.Qt_counters.setLayout(countersL)

        # window > top
        topL.addStretch(1)

        # window > range
        rangeL = QtGui.QHBoxLayout()
        windowL.addLayout(rangeL)

        # window > range > userange
        self.Qt_userange = QtGui.QCheckBox("range")
        self.Qt_userange.stateChanged.connect(self.Qt_userange_change)
        rangeL.addWidget(self.Qt_userange)

        # window > range > rangevar
        # self.Qt_rangevar = QtGui.QLineEdit()
        # rangeL.addWidget(self.Qt_rangevar)
        # self.Qt_rangevar.textChanged.connect(self.Qt_rangevar_change)
        # self.Qt_rangevar.setFixedWidth(30)
        # regexp = QtCore.QRegExp("[a-zA-Z]+")
        # validator = QtGui.QRegExpValidator(regexp, self)
        # self.Qt_rangevar.setValidator(validator)
        # self.Qt_rangevar.hide()

        # window > range > "n ="
        self.Qt_rangelabel = QtGui.QLabel("n =")
        rangeL.addWidget(self.Qt_rangelabel)

        # window > range > range
        self.Qt_range = QtGui.QLineEdit()
        rangeL.addWidget(self.Qt_range)
        self.Qt_range.textChanged.connect(self.Qt_range_change)
        regexp = QtCore.QRegExp("(?:-?\d+)?:(?:(?:-?\d+)?:)?(-?\d+)?")
        validator = QtGui.QRegExpValidator(regexp, self)
        self.Qt_range.setValidator(validator)

        # window > range
        rangeL.addStretch(1)

        # window > calls
        self.Qt_calls = QtGui.QScrollArea()
        windowL.addWidget(self.Qt_calls)
        callsL = QtGui.QVBoxLayout()
        self.Qt_calls.setLayout(callsL)
        windowL.setStretch(2, 1)
        self.Qt_callFs = []

        # window > calls > add
        add = QtGui.QPushButton("+")
        callsL.addWidget(add)
        add.clicked.connect(self.Qt_call_add)

        # window > calls
        callsL.addStretch(1)

        # window > bottom
        bottomL = QtGui.QHBoxLayout()
        windowL.addLayout(bottomL)
        bottomL.addStretch(1)

        # window > bottom > samplename
        bottomL.addWidget(QtGui.QLabel("sample name:"))
        self.Qt_samplename = QtGui.QLineEdit()
        bottomL.addWidget(self.Qt_samplename)
        self.Qt_samplename.textChanged.connect(self.Qt_samplename_change)

        # window > bottom > submit
        submit = QtGui.QPushButton("submit")
        bottomL.addWidget(submit)
        submit.clicked.connect(self.Qt_submit_click)

        # window
        self.Qt_window.show()

    def UI_start(self):
        sys.exit(self.exec_())

    # setters
    def UI_sampler_set(self):
        self.setting = True
        self.Qt_sampler.setCurrentIndex(
            self.Qt_sampler.findText(self.state["sampler"]))
        self.setting = False

    def UI_nt_setmax(self):
        self.setting = True
        self.Qt_nt.clear()
        sampler = self.samplers[self.state["sampler"]]
        self.Qt_nt.addItems(map(str, range(1, sampler["nt_max"] + 1)))
        self.setting = False

    def UI_nt_set(self):
        self.setting = True
        self.Qt_nt.setCurrentIndex(self.state["nt"] - 1)
        self.setting = False

    def UI_nrep_set(self):
        self.setting = True
        self.Qt_nrep.setText(str(self.state["nrep"]))
        self.setting = False

    def UI_info_set(self, text):
        self.Qt_info.setText(text)

    def UI_usepapi_setenabled(self):
        sampler = self.samplers[self.state["sampler"]]
        self.Qt_usepapi.setEnabled(sampler["papi_counters_max"] > 0)

    def UI_usepapi_set(self):
        self.setting = True
        self.Qt_usepapi.setChecked(self.state["usepapi"])
        self.setting = False

    def UI_useld_set(self):
        self.setting = True
        self.Qt_useld.setChecked(self.state["useld"])
        self.setting = False

    def UI_usevary_set(self):
        self.setting = True
        self.Qt_usevary.setChecked(self.state["usevary"])
        self.setting = False

    def UI_counters_setvisible(self):
        if self.state["usepapi"]:
            self.Qt_counters.show()
        else:
            self.Qt_counters.hide()

    def UI_counters_setoptions(self):
        # delete old
        Qcounters = self.Qt_counters.children()[1:]
        for Qcounter in Qcounters:
            Qcounter.deleteLater()
        # add new
        sampler = self.samplers[self.state["sampler"]]
        QcountersL = self.Qt_counters.layout()
        for _ in range(sampler["papi_counters_max"]):
            Qcounter = QtGui.QComboBox()
            QcountersL.addWidget(Qcounter)
            Qcounter.addItems([""] + sampler["papi_counters_avail"])
            Qcounter.currentIndexChanged.connect(self.Qt_counter_change)

    def UI_counters_set(self):
        self.setting = True
        Qcounters = self.Qt_counters.children()[1:]
        for Qcounter, countername in zip(Qcounters, self.state["counters"]):
            if not countername:
                countername = ""
            Qcounter.setCurrentIndex(Qcounter.findText(countername))
        self.setting = False

    def UI_userange_set(self):
        self.setting = True
        self.Qt_userange.setChecked(self.state["userange"])
        self.setting = False

    def UI_range_setvisible(self):
        if self.state["userange"]:
            # self.Qt_rangevar.show()
            self.Qt_rangelabel.show()
            self.Qt_range.show()
        else:
            # self.Qt_rangevar.hide()
            self.Qt_rangelabel.hide()
            self.Qt_range.hide()

    # def UI_rangevar_set(self):
    #     self.setting = True
    #     self.Qt_rangevar.setText(self.state["rangevar"])
    #     self.setting = False

    def UI_range_set(self):
        self.setting = True
        lower, step, upper = self.state["range"]
        if step:
            self.Qt_range.setText("%d:%d:%d" % (lower, step, upper))
        else:
            self.Qt_range.setText("%d:%d" % (lower, upper))
        self.setting = False

    def UI_calls_set(self):
        # delete old
        for Qcall in self.Qt_callFs:
            Qcall.deleteLater()
        self.Qt_callFs = []
        # add new
        QcallsL = self.Qt_calls.layout()
        for callid in range(len(self.state["calls"])):
            QcallF = QtGui.QFrame()
            QcallsL.insertWidget(callid, QcallF)
            self.Qt_callFs.append(QcallF)
            QcallL = QtGui.QGridLayout()
            self.Qt_callFs.append(QcallL)
            QcallF.setLayout(QcallL)
            self.UI_call_init(callid)

    def UI_call_init(self, callid):
        routines = [r for r in self.signatures.keys()
                    if r in self.samplers[self.state["sampler"]]["kernels"]]
        callF = self.Qt_callFs[callid]
        callL = callF.layout()

        callF.callid = callid

        # buttons
        buttonsL = QtGui.QHBoxLayout()
        callL.addLayout(buttonsL, 0, 0)

        # buttons > remove
        callL.removeS = QtGui.QStackedWidget()
        buttonsL.addWidget(callL.removeS)
        remove = QtGui.QToolButton()
        callL.removeS.addWidget(remove)
        icon = self.style().standardIcon(QtGui.QStyle.SP_DialogDiscardButton)
        remove.setIcon(icon)
        remove.clicked.connect(self.Qt_call_remove)
        callL.removeS.addWidget(QtGui.QWidget())

        # buttons > down
        callL.downS = QtGui.QStackedWidget()
        buttonsL.addWidget(callL.downS)
        down = QtGui.QToolButton()
        down.setArrowType(QtCore.Qt.DownArrow)
        callL.downS.addWidget(down)
        down.clicked.connect(self.Qt_call_movedown)
        callL.downS.addWidget(QtGui.QWidget())

        # buttons > up
        callL.upS = QtGui.QStackedWidget()
        buttonsL.addWidget(callL.upS)
        up = QtGui.QToolButton()
        up.setArrowType(QtCore.Qt.UpArrow)
        callL.upS.addWidget(up)
        up.clicked.connect(self.Qt_call_moveup)
        callL.upS.addWidget(QtGui.QWidget())

        # buttons
        buttonsL.addStretch(1)

        # routine
        routine = QtGui.QLineEdit(self.state["calls"][callid][0])
        callL.addWidget(routine, 1, 0)
        routine.textChanged.connect(self.Qt_routine_change)
        completer = QtGui.QCompleter(routines, routine)
        routine.setCompleter(completer)

        # args
        callL.args = [routine]

        self.UI_call_update(callid)

    def UI_call_update(self, callid):
        pass

    def UI_arg_set(self):
        pass

    def UI_samplename_set(self):
        self.setting = True
        self.Qt_samplename.setText(self.state["samplename"])
        self.setting = False

    # event handlers
    def Qt_sampler_change(self):
        if self.setting:
            return
        self.UI_sampler_change(str(self.Qt_sampler.currentText()))

    def Qt_nt_change(self):
        if self.setting:
            return
        self.UI_nt_change(int(self.Qt_nt.currentText()))

    def Qt_nrep_change(self):
        if self.setting:
            return
        text = str(self.Qt_nrep.text())
        self.UI_nrep_change(int(text) if text else None)

    def Qt_usepapi_change(self):
        if self.setting:
            return
        self.UI_usepapi_change(self.Qt_usepapi.isChecked())

    def Qt_useld_change(self):
        if self.setting:
            return
        self.UI_useld_change(self.Qt_useld.isChecked())

    def Qt_usevary_change(self):
        if self.setting:
            return
        self.UI_usevary_change(self.Qt_usevary.isChecked())

    def Qt_counter_change(self):
        if self.setting:
            return
        counternames = []
        Qcounters = self.Qt_counters.children()[1:]
        for Qcounter in Qcounters:
            countername = str(Qcounter.currentText())
            counternames.append(countername if countername else None)
        self.UI_counters_change(counternames)

    def Qt_userange_change(self):
        if self.setting:
            return
        self.UI_userange_change(self.Qt_userange.isChecked())

    # def Qt_rangevar_change(self):
    #     if self.setting:
    #         return
    #     self.UI_rangevar_change(str(self.Qt_rangevar.text()))

    def Qt_range_change(self):
        if self.setting:
            return
        parts = str(self.Qt_range.text()).split(":")
        lower = int(parts[0]) if len(parts) >= 1 and parts[0] else None
        step = int(parts[1]) if len(parts) == 3 and parts[1] else 1
        upper = int(parts[-1]) if len(parts) >= 2 and parts[-1] else None
        self.UI_range_change((lower, step, upper))

    def Qt_call_add(self):
        self.UI_call_add()

    def Qt_call_remove(self):
        self.UI_call_remove(self.sender().parent().parent().callid)

    def Qt_call_moveup(self):
        self.UI_call_moveup(self.sender().parent().parent().callid)

    def Qt_call_movedown(self):
        self.UI_call_movedown(self.sender().parent().parent().callid)

    def Qt_routine_change(self):
        pass

    def Qt_arg_change(self):
        pass

    def Qt_samplename_change(self):
        if self.setting:
            return
        self.UI_samplename_change(str(self.Qt_samplename.text()))

    def Qt_submit_click(self):
        self.UI_submit_click()


def main():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    GUI_Qt()


if __name__ == "__main__":
    main()
