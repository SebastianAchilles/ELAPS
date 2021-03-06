#!/usr/bin/env python
"""Job progress tracker in ELAPS:PlayMat."""
from __future__ import division, print_function

from .. import defines

import os

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import pyqtSlot


class QJobProgress(QtGui.QDockWidget):

    """Tracker for job progresses in ELAPS:PlayMat."""

    def __init__(self, playmat):
        """Initialize the progress tracker."""
        QtGui.QDockWidget.__init__(
            self, "Job Progress",
            objectName="Job Progress",
            features=(QtGui.QDockWidget.DockWidgetMovable |
                      QtGui.QDockWidget.DockWidgetFloatable),
        )
        self.playmat = playmat

        self.timer = QtCore.QTimer(
            interval=defines.jobprogress_timeout,
            timeout=self.on_timer
        )

        self.UI_init()

    def UI_init(self):
        """Initialize the GUI elements."""
        self.playmat.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self)
        self.hide()

        self.setWidget(QtGui.QTreeWidget(
            selectionMode=QtGui.QListWidget.ExtendedSelection,
            contextMenuPolicy=QtCore.Qt.CustomContextMenu,
            itemDoubleClicked=self.on_double_click,
            customContextMenuRequested=self.on_rightclick
        ))
        self.widget().keyPressEvent = self.on_keypress
        self.widget().setHeaderLabels(
            ("job", "progress", "status", "actions")
        )

    def resize_columns(self):
        """Resize all columns."""
        for colid in range(3):
            self.widget().resizeColumnToContents(colid)

    def jobs(self):
        """Get all jobs."""
        widget = self.widget()
        return [widget.topLevelItem(i).job
                for i in range(widget.topLevelItemCount())]

    def selected_jobs(self):
        """Get selected jobs."""
        try:
            return [self.playmat.sender().parent().job]
        except:
            return [item.job for item in self.widget().selectedItems()]

    def add_job(self, filebase, jobid, experiment):
        """Add a job to track."""
        job = {
            "jobid": jobid,
            "name": os.path.basename(filebase),
            "nresults": experiment.nresults(),
            "progress": 0,
            "filebase": filebase,
            "reportfile": "%s.%s" % (filebase, defines.report_extension),
            "errorfile": "%s.%s" % (filebase, defines.error_extension),
            "experiment": experiment.copy(),
            "stat": "PEND",
        }

        # item
        item = QtGui.QTreeWidgetItem(
            (job["name"], "", "pending", "")
        )
        self.widget().addTopLevelItem(item)

        job["item"] = item
        item.job = job

        # progress bar
        job["progressbar"] = QtGui.QProgressBar(
            maximum=job["nresults"], value=0
        )
        self.widget().setItemWidget(item, 1, job["progressbar"])

        # actions
        actions = {}
        job["actions"] = actions
        actionsT = QtGui.QToolBar()
        actions["kill"] = QtGui.QAction(
            self.playmat.style().standardIcon(QtGui.QStyle.SP_BrowserStop),
            "Kill", actionsT, triggered=self.on_kill
        )
        actions["rerun"] = QtGui.QAction(
            self.playmat.style().standardIcon(QtGui.QStyle.SP_BrowserReload),
            "Rerun", actionsT, triggered=self.on_rerun
        )
        actions["rerun"].setDisabled(True)
        actions["remove"] = QtGui.QAction(
            self.playmat.style().standardIcon(QtGui.QStyle.SP_TrashIcon),
            "Remove", actionsT, triggered=self.on_remove
        )
        actions["remove"].setDisabled(True)
        actionsT.job = job
        actionsT.addAction(job["actions"]["kill"])
        actionsT.addAction(job["actions"]["rerun"])
        actionsT.addAction(job["actions"]["remove"])
        self.widget().setItemWidget(item, 3, actionsT)

        self.resize_columns()
        self.show()
        self.widget().scrollToBottom()
        self.timer.start()

    def autohide(self):
        """Hide if empty."""
        if self.widget().topLevelItemCount() == 0:
            self.hide()

    # events
    @pyqtSlot()
    def on_timer(self):
        """Update progress."""
        # read data
        for itemid in range(self.widget().topLevelItemCount()):
            job = self.widget().topLevelItem(itemid).job
            if job["stat"] in ("ERROR", "DONE", "KILL"):
                # job is done
                continue
            if not os.path.isfile(job["reportfile"]):
                # job is pending
                continue
            with open(job["reportfile"]) as fin:
                job["progress"] = len(fin.readlines()) - 2
            if job["stat"] == "TOKILL":
                job["stat"] = "KILL"
            elif job["progress"] >= 0:
                job["stat"] = "RUN"
            if job["progress"] >= job["nresults"]:
                job["stat"] = "DONE"
            if os.path.isfile(job["errorfile"]):
                if os.path.getsize(job["errorfile"]):
                    job["stat"] = "ERROR"
            if job["stat"] in ("ERROR", "DONE", "KILL"):
                job["actions"]["kill"].setDisabled(True)
                job["actions"]["rerun"].setDisabled(False)
                job["actions"]["remove"].setDisabled(False)

        for itemid in range(self.widget().topLevelItemCount()):
            item = self.widget().topLevelItem(itemid)
            job = item.job
            progress = min(max(0, job["progress"]), job["nresults"])
            job["progressbar"].setValue(progress)
            if job["stat"] == "RUN":
                item.setText(
                    2, "%d / %d results" % (job["progress"], job["nresults"])
                )
            elif job["stat"] == "ERROR":
                item.setText(2, "error")
            elif job["stat"] == "KILL":
                item.setText(2, "killed")
            elif job["stat"] == "DONE":
                item.setText(2, "done")

        self.resize_columns()

    @pyqtSlot(QtGui.QTreeWidgetItem, int)
    def on_double_click(self, item, col):
        """Event: double clicked on item."""
        if not item:
            return
        job = item.job
        if job["stat"] in ("RUN", "DONE"):
            self.playmat.on_open_viewer(job["reportfile"])

    def on_keypress(self, event):
        """Event: key pressed."""
        if event.key() in (QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Delete):
            self.on_kill()
            return
        QtGui.QTreeWidget.keyPressEvent(self.widget(), event)

    @pyqtSlot(QtCore.QPoint)
    def on_rightclick(self, pos):
        """Event: right click."""
        globalpos = self.widget().viewport().mapToGlobal(pos)
        menu = QtGui.QMenu()

        alljobs = self.jobs()
        if not alljobs:
            return
        jobs = self.selected_jobs()

        if jobs:
            # kill
            if any(job["stat"] in ("PEND", "RUN") for job in jobs):
                menu.addAction(QtGui.QAction(
                    "Kill", menu, triggered=self.on_kill
                ))

            # rerun
            if any(job["stat"] in ("ERROR", "DONE") for job in jobs):
                menu.addAction(QtGui.QAction(
                    "Rerun", menu, triggered=self.on_rerun
                ))

            # clear
            menu.addAction(QtGui.QAction(
                "Clear", menu, triggered=self.on_remove
            ))

            # open in Viewer
            if any(job["stat"] in ("RUN", "DONE") for job in jobs):
                menu.addAction(QtGui.QAction(
                    "Open in Viewer", menu, triggered=self.on_open_viewer
                ))

            # open in PlayMat
            if len(jobs) == 1:
                menu.addAction(QtGui.QAction(
                    "Open in PlayMat", menu, triggered=self.on_open_playmat
                ))

            menu.addSeparator()

        if len(jobs) != len(alljobs):
            # kill all
            if any(job["stat"] in ("PEND", "RUN") for job in alljobs):
                menu.addAction(QtGui.QAction(
                    "Kill all", menu, triggered=self.on_killall
                ))
            if any(job["stat"] not in ("PEND", "RUN") for job in alljobs):
                menu.addAction(QtGui.QAction(
                    "Clear done", menu, triggered=self.on_removedone
                ))

            # clear all
            menu.addAction(QtGui.QAction(
                "Clear all", menu, triggered=self.on_removeall
            ))

            # open all in Viewer
            if any(job["stat"] in ("RUN", "DONE") for job in alljobs):
                menu.addAction(QtGui.QAction(
                    "Open all in Viewer", menu, triggered=self.on_openall_viewer
                ))

        menu.exec_(globalpos)

    # @pyqtSlot()  # sender() pyqt bug
    def on_kill(self):
        """Event: kill job(s)."""
        for job in self.selected_jobs():
            if job["stat"] in ("PEND", "RUN"):
                job["experiment"].sampler["backend"].kill(job["jobid"])
                job["stat"] = "TOKILL"

    # @pyqtSlot()  # sender() pyqt bug
    def on_rerun(self):
        """Event: rerun job(s)."""
        for job in self.selected_jobs():
            if job["stat"] in ("ERROR", "DONE", "KILL"):
                ex = job["experiment"]
                backend = ex.sampler["backend"]
                filebase = job["filebase"]
                jobid = ex.submit(filebase)
                filename = "%s.%s" % (filebase, defines.report_extension)
                self.playmat.log("Resubmitted job for %r to %r." % (filename, backend.name))
                self.add_job(filebase, jobid, ex)
        self.on_remove()

    @pyqtSlot()
    def on_killall(self):
        """Event: kill all jobs."""
        names = [repr(job["name"]) for job in self.jobs()
                 if job["stat"] in ("PEND", "RUN")]
        self.playmat.UI_dialog(
            "question", "Confirm job termination",
            "I will kill the following jobs: " + " ".join(names),
            {"Ok": (self.on_killall_confirmed, ()), "Cancel": None}
        )

    def on_killall_confirmed(self):
        """Event: kill all jobs confirmed."""
        for job in self.jobs():
            if job["stat"] in ("PEND", "RUN"):
                job["experiment"].sampler["backend"].kill(job["jobid"])
                job["stat"] = "TOKILL"

    # @pyqtSlot()  # sender() pyqt bug
    def on_remove(self):
        """Event: remove job(s)."""
        for job in self.selected_jobs():
            self.widget().takeTopLevelItem(
                self.widget().indexOfTopLevelItem(job["item"])
            )
        self.autohide()

    @pyqtSlot()
    def on_removeall(self):
        """Event: remove all jobs."""
        for job in self.jobs():
            self.widget().takeTopLevelItem(
                self.widget().indexOfTopLevelItem(job["item"])
            )
        """Event: remove all jobs."""
        self.autohide()

    @pyqtSlot()
    def on_removedone(self):
        """Event: remove all jobs."""
        for job in self.jobs():
            if job["stat"] not in ("PEND", "RUN"):
                self.widget().takeTopLevelItem(
                    self.widget().indexOfTopLevelItem(job["item"])
                )
        self.autohide()

    @pyqtSlot()
    def on_open_viewer(self):
        """Event: open job(s) in Viewer."""
        for job in self.selected_jobs():
            if job["stat"] in ("RUN", "DONE"):
                self.playmat.on_open_viewer(job["reportfile"])

    @pyqtSlot()
    def on_openall_viewer(self):
        """Event: open all jobs in Viewer."""
        for job in self.jobs():
            if job["stat"] == "DONE":
                self.playmat.on_open_viewer(job["reportfile"])

    @pyqtSlot()
    def on_open_playmat(self):
        """Event: open job(s) in PlayMat."""
        for job in self.selected_jobs():
            self.playmat.experiment_set(job["experiment"])
            self.playmat.reportname_set(job["name"])
        self.playmat.UI_setall()
