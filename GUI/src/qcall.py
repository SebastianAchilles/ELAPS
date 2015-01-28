#!/usr/bin/env python
from __future__ import division, print_function

import signature
from qdataarg import QDataArg

from PyQt4 import QtCore, QtGui


class QCall(QtGui.QListWidgetItem):
    def __init__(self, viewer, callid):
        QtGui.QGroupBox.__init__(self)
        self.viewer = viewer
        self.callid = callid
        self.sig = None

        self.UI_init()

    def UI_init(self):
        routines = list(self.viewer.sampler["kernels"])

        # layout
        self.widget = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        self.widget.setLayout(layout)
        # layout.setContentsMargins(5, 5, 5, 5)
        layout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)

        # routine
        routine = QtGui.QLineEdit()
        layout.addWidget(routine, 1, 0)
        routine.callid = self.callid
        routine.argid = 0
        routine.setProperty("invalid", True)
        routine.textChanged.connect(self.arg_change)
        completer = QtGui.QCompleter(routines, routine)
        routine.setCompleter(completer)

        # spaces
        layout.setColumnStretch(100, 1)

        self.Qt_remove = QtGui.QToolButton()
        layout.addWidget(self.Qt_remove, 1, 101)
        icon = self.widget.style().standardIcon(
            QtGui.QStyle.SP_DialogCloseButton
        )
        self.Qt_remove.setIcon(icon)
        self.Qt_remove.clicked.connect(self.remove_click)

        # attributes
        self.Qt_args = [routine]
        self.Qt_arglabels = [None]
        self.sig = None

    def update_size(self):
        argheight = 0
        labelheight = 0
        layout = self.widget.layout()
        for i, Qarg in enumerate(self.Qt_args):
            item = layout.itemAtPosition(0, i)
            if item:
                labelheight = max(labelheight,
                                  item.widget().sizeHint().height())
            argheight = max(argheight, Qarg.size().height())
        margins = layout.contentsMargins()
        top = margins.top()
        bottom = margins.bottom()
        spacing = layout.spacing()
        height = top + labelheight + spacing + argheight + bottom
        size = self.widget.sizeHint()
        size.setHeight(height)
        self.setSizeHint(size)

    def args_init(self):
        call = self.viewer.calls[self.callid]
        self.Qt_args[0].setProperty("invalid", False)
        if isinstance(call, signature.Call):
            self.sig = call.sig
        else:
            minsig = self.viewer.sampler["kernels"][call[0]]
            self.sig = None
            if not self.viewer.nosigwarning_shown:
                self.viewer.UI_alert("No signature found for %r!\n" % call[0] +
                                     "Hover arguments for input syntax.")
                self.viewer.nosigwarning_shown = True
        for argid in range(len(call))[1:]:
            tooltip = None
            if self.sig:
                argname = self.sig[argid].name
            else:
                argname = minsig[argid].replace("*", " *")
                if "char" in argname:
                    tooltip = "Any string"
                elif argname in ("int *", "float *", "double *"):
                    tooltip = ("Scalar:\tvalue\t\te.g. 1, -0.5\n"
                               "Array:\t[#elements]"
                               "\te.g. [10000] for a 100x100 matrix")
            Qarglabel = QtGui.QLabel(argname)
            if tooltip:
                Qarglabel.setToolTip(tooltip)
            self.widget.layout().addWidget(Qarglabel, 0, argid)
            self.Qt_arglabels.append(Qarglabel)
            Qarglabel.setAlignment(QtCore.Qt.AlignCenter)
            if self.sig:
                arg = self.sig[argid]
                if isinstance(arg, signature.Flag):
                    Qarg = QtGui.QComboBox()
                    Qarg.addItems(arg.flags)
                    Qarg.currentIndexChanged.connect(self.arg_change)
                elif isinstance(arg, (signature.Dim, signature.Scalar,
                                      signature.Ld, signature.Inc,
                                      signature.Info)):
                    Qarg = QtGui.QLineEdit()
                    Qarg.textChanged.connect(self.arg_change)
                elif isinstance(arg, signature.Data):
                    Qarg = QDataArg(self)
            else:
                Qarg = QtGui.QLineEdit()
                Qarg.textChanged.connect(self.arg_change)
                if tooltip:
                    Qarg.setToolTip(tooltip)
            Qarg.argid = argid
            Qarg.setProperty("invalid", True)
            self.widget.layout().addWidget(Qarg, 1, argid)
            self.Qt_args.append(Qarg)
        if self.sig:
            self.showargs_apply()
            self.usevary_apply()

    def args_clear(self):
        self.Qt_args[0].setProperty("invalid", True)
        for Qarg in self.Qt_args[1:]:
            Qarg.deleteLater()
        self.Qt_args = self.Qt_args[:1]
        for Qarglabel in self.Qt_arglabels[1:]:
            Qarglabel.deleteLater()
        self.Qt_arglabels = self.Qt_arglabels[:1]
        self.update_size()
        self.sig = None

    def showargs_apply(self):
        if not self.sig:
            return
        for argid, arg in enumerate(self.sig):
            for name, classes in (
                ("flags", signature.Flag),
                ("scalars", signature.Scalar),
                ("lds", (signature.Ld, signature.Inc)),
                ("infos", signature.Info)
            ):
                if isinstance(arg, classes):
                    showing = self.viewer.showargs[name]
                    self.Qt_arglabels[argid].setVisible(showing)
                    self.Qt_args[argid].setVisible(showing)

    def usevary_apply(self):
        if not self.sig:
            return
        for Qarg in self.Qt_args:
            if isinstance(Qarg, QDataArg):
                Qarg.usevary_apply()

    def args_set(self, fromargid=None):
        call = self.viewer.calls[self.callid]
        # set widgets
        if call[0] not in self.viewer.sampler["kernels"]:
            self.args_clear()
            return
        if isinstance(call, signature.Call):
            if call.sig != self.sig:
                self.args_clear()
                self.args_init()
        else:
            if len(self.Qt_args) != len(call):
                self.args_clear()
                self.args_init()
        # set values
        for argid, val in enumerate(call):
            Qarg = self.Qt_args[argid]
            Qarg.setProperty("invalid", val is None)
            Qarg.style().unpolish(Qarg)
            Qarg.style().polish(Qarg)
            Qarg.update()
            if Qarg.argid == fromargid:
                continue
            val = "" if val is None else str(val)
            if isinstance(Qarg, QtGui.QLineEdit):
                Qarg.setText(val)
            elif isinstance(Qarg, QtGui.QComboBox):
                Qarg.setCurrentIndex(Qarg.findText(val))
            elif isinstance(Qarg, QDataArg):
                Qarg.set()
        self.update_size()

    def data_viz(self):
        if not self.sig:
            return
        for argid in self.viewer.calls[self.callid].sig.dataargs():
            self.Qt_args[argid].viz()
        self.update_size()

    # event handlers
    def remove_click(self):
        self.viewer.UI_call_remove(self.callid)

    def arg_change(self):
        sender = self.viewer.app.sender()
        if isinstance(sender, QtGui.QLineEdit):
            # adjust widt no matter where the change came from
            val = str(sender.text())
            if sender.argid != 0:
                width = sender.fontMetrics().width(val)
                width += sender.minimumSizeHint().width()
                height = sender.sizeHint().height()
                sender.setFixedSize(max(height, width), height)
        if self.viewer.Qt_setting:
            return
        if isinstance(sender, QtGui.QComboBox):
            val = str(sender.currentText())
        if not val:
            val = None
        self.viewer.UI_arg_change(self.callid, sender.argid, val)
