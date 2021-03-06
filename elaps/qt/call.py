#!/usr/bin/env python
"""Representation of calls in ELAPS:PlayMat."""
from __future__ import division, print_function

from .. import signature
from .. import io as elapsio
from .dataarg import QDataArg

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSlot


class QCall(QtGui.QListWidgetItem):

    """Representation of a call in ELAPS:PlayMat."""

    def __init__(self, playmat, callid):
        """Initialize the call representation."""
        QtGui.QListWidgetItem.__init__(self)
        self.playmat = playmat
        self.sig = None

        self.UI_init()

    @property
    def callid(self):
        """Get the callid."""
        return self.playmat.UI_calls.row(self)

    @property
    def call(self):
        """Get the associated Call (or BasicCall)."""
        return self.playmat.experiment.calls[self.callid]

    def UI_init(self):
        """Initialize the GUI elements."""
        routines = list(self.playmat.experiment.sampler["kernels"])

        # layout
        self.widget = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        self.widget.setLayout(layout)

        # routine label
        routinelabel = QtGui.QLabel()
        layout.addWidget(routinelabel, 0, 0)

        # routine
        routine = QtGui.QLineEdit(textChanged=self.on_arg_change)
        layout.addWidget(routine, 1, 0)
        routine.argid = 0
        completer = QtGui.QCompleter(routines, routine)
        routine.setCompleter(completer)

        # spaces
        layout.setColumnStretch(100, 1)

        # shortcuts

        # attributes
        self.UI_args = [routine]
        self.UI_arglabels = [routinelabel]

    def update_size(self):
        """Update the size of the call item from its widget."""
        def update():
            """Update the size (asynchronous callback)."""
            try:
                self.setSizeHint(self.widget.sizeHint())
            except:
                pass
        QtCore.QTimer.singleShot(0, update)

    def UI_args_set(self, force=False):
        """Set all arguments."""
        for argid in range(len(self.call)):
            self.UI_arg_set(argid, force)

    def UI_arg_set(self, argid=None, force=False):
        """Set an argument."""
        value = self.call[argid]
        UI_arg = self.UI_args[argid]
        UI_arglabel = self.UI_arglabels[argid]
        if force or not UI_arg.hasFocus():
            if isinstance(UI_arg, QtGui.QLineEdit):
                if type(value) is list:
                    UI_arg.setText("[%s]" % value[0])
                else:
                    UI_arg.setText(str(value))
            elif isinstance(UI_arg, QtGui.QComboBox):
                UI_arg.setCurrentIndex(UI_arg.findText(str(value)))

        if isinstance(self.call, signature.BasicCall):
            self.playmat.UI_set_invalid(UI_arg, False)

        if isinstance(self.call, signature.Call):
            # apply hideargs
            show = not isinstance(
                self.sig[argid], tuple(self.playmat.hideargs) + (type(None),)
            )
            UI_arg.setVisible(show)
            UI_arglabel.setVisible(show)

            # viz
            if isinstance(self.sig[argid], signature.Data):
                UI_arg.viz()

        # validity
        if argid > 0:
            try:
                self.playmat.experiment.set_arg(self.callid, argid, value,
                                                check_only=True)
                self.playmat.UI_set_invalid(UI_arg, False)
            except:
                self.playmat.UI_set_invalid(UI_arg)
        self.update_size()

    def setall(self, force=False):
        """Set all UI elements."""
        self.playmat.UI_setting += 1
        self.fixcallid = self.callid
        if isinstance(self.call, signature.BasicCall):
            if self.sig != self.call.sig:
                self.args_clear()
                self.args_init()
                self.sig = self.call.sig
        else:
            if self.sig:
                self.args_clear()
                self.sig = None
        self.setToolTip(
            "<tt>calls[%d]</tt>: Call number %d to be measured" %
            (self.fixcallid, self.fixcallid)
        )

        self.UI_args_set(force)
        self.playmat.UI_setting -= 1

    def args_init(self):
        """Initialize the arguments."""
        Qroutine = self.UI_args[0]
        assert(isinstance(self.call, signature.BasicCall))
        sig = self.call.sig
        try:
            doc = elapsio.load_doc(self.call[0])
        except:
            doc = None
        if doc:
            Qroutine.setToolTip(doc[0][1])
        for argid, arg in enumerate(sig):
            if argid == 0:
                continue
            tooltip = ""
            if isinstance(sig, signature.Signature):
                argname = sig[argid].name
                if doc and argid < len(doc):
                    tooltip = doc[argid][1]
            else:
                argname = sig[argid].replace("*", " *")
                if doc and argid < len(doc):
                    argname += doc[argid][0]
                    tooltip = doc[argid][1]
                if argname in ("int *", "float *", "double *"):
                    if doc:
                        tooltip += "\n\n*Format*:\n"
                    tooltip += ("Scalar:\tvalue\t\te.g. 1, -0.5\n"
                                "Array:\t[#elements]"
                                "\te.g. [10000] for a 100x100 matrix")
            # arglabel
            UI_arglabel = QtGui.QLabel(
                argname, toolTip=tooltip, alignment=QtCore.Qt.AlignCenter
            )
            self.UI_arglabels.append(UI_arglabel)
            self.widget.layout().addWidget(UI_arglabel, 0, argid)
            # arg
            if isinstance(sig, signature.Signature):
                arg = sig[argid]
                if isinstance(arg, signature.Flag):
                    UI_arg = QtGui.QComboBox()
                    UI_arg.addItems(map(str, arg.flags))
                    UI_arg.currentIndexChanged[str].connect(self.on_arg_change)
                elif isinstance(arg, signature.Data):
                    UI_arg = QDataArg(
                        self,
                        editingFinished=self.on_dataarg_focusout
                    )
                else:
                    UI_arg = QtGui.QLineEdit(
                        textChanged=self.on_arg_change,
                        editingFinished=self.on_arg_focusout
                    )
            else:
                UI_arg = QtGui.QLineEdit("", textChanged=self.on_arg_change)
            UI_arg.pyqtConfigure(
                toolTip=tooltip,
                contextMenuPolicy=QtCore.Qt.CustomContextMenu,
                customContextMenuRequested=self.on_arg_rightclick
            )
            UI_arg.argid = argid
            self.UI_args.append(UI_arg)
            self.widget.layout().addWidget(UI_arg, 1, argid,
                                           QtCore.Qt.AlignCenter)

    def args_clear(self):
        """Clear the arguments."""
        for UI_arg in self.UI_args[1:]:
            UI_arg.deleteLater()
        self.UI_args = [self.UI_args[0]]
        for UI_arglabel in self.UI_arglabels[1:]:
            UI_arglabel.deleteLater()
        self.UI_arglabels = [self.UI_arglabels[0]]
        self.UI_args[0].setToolTip("")

    def viz(self):
        """Visualize all operands."""
        if not isinstance(self.call, signature.Call):
            return
        for argid in self.call.sig.dataargs():
            self.UI_args[argid].viz()
        self.update_size()

    # event handlers
    # @pyqtSlot(str)  # sender() pyqt bug
    def on_arg_change(self, value):
        """Event: Changed an argument."""
        sender = self.playmat.Qapp.sender()
        value = str(value)
        argid = sender.argid
        if isinstance(sender, QtGui.QLineEdit) and not isinstance(sender,
                                                                  QDataArg):
            # adjust width no matter where the change came from
            self.playmat.UI_edit_autowidth(sender, 1 + (argid == 0))
        if self.playmat.UI_setting:
            return
        self.playmat.on_arg_set(self.callid, argid, value)

    def on_dataarg_focusout(self):
        """Event: Changed a data argument."""
        sender = self.playmat.Qapp.sender()
        value = sender.text()
        self.on_arg_change(value)
        self.on_arg_focusout()

    # @pyqtSlot(QtCore.QPoint)  # sender() pyqt bug
    def on_arg_rightclick(self, pos):
        """Event: right click on arg."""
        if self.playmat.UI_setting:
            return
        sender = self.playmat.Qapp.sender()
        globalpos = sender.mapToGlobal(pos)
        menu = sender.createStandardContextMenu()
        if isinstance(self.call, signature.Call):
            actions = menu.actions()
            if actions[-1].text() == "Insert Unicode control character":
                actions[-1].setVisible(False)
            argid = sender.argid
            if isinstance(self.call.sig[argid], signature.Ld):
                inferld = QtGui.QAction("Infer leading dimension", sender,
                                        triggered=self.on_inferld)
                inferld.argid = argid
                menu.insertAction(actions[0], inferld)
            elif isinstance(self.call.sig[argid], signature.Lwork):
                inferlwork = QtGui.QAction("Infer workspace size", sender,
                                           triggered=self.on_inferlwork)
                inferlwork.argid = argid
                menu.insertAction(actions[0], inferlwork)
            if isinstance(self.call.sig[argid], signature.Data):
                for action in self.playmat.UI_varyactions(self.call[argid]):
                    if action:
                        menu.insertAction(actions[0], action)
                    else:
                        menu.insertSeparator(actions[0])
            if len(menu.actions()) > len(actions):
                menu.insertSeparator(actions[0])
        menu.exec_(globalpos)

    # @pyqtSlot()  # sender() pyqt bug
    def on_inferld(self):
        """Event: infer ld."""
        if self.playmat.UI_setting:
            return
        argid = self.playmat.Qapp.sender().argid
        self.UI_args[argid].clearFocus()
        self.playmat.on_infer_ld(self.callid, argid)

    # @pyqtSlot()  # sender() pyqt bug
    def on_inferlwork(self):
        """Event: infer ld."""
        if self.playmat.UI_setting:
            return
        argid = self.playmat.Qapp.sender().argid
        self.UI_args[argid].clearFocus()
        self.playmat.on_infer_lwork(self.callid, argid)

    @pyqtSlot()
    def on_arg_focusout(self):
        """Argument looses focus."""
        if self.playmat.UI_setting:
            return
        if self.playmat.Qapp.activeModalWidget():
            return
        self.playmat.UI_calls_set()
