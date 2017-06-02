from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog

import os
import sys
import traceback
from itertools import groupby
import pandas as pd
import numpy as np

sys.path.append("..")

from idw import idw
from cfm import cfm
from knncad import knn


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args):
        super().__init__(*args)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Set up progress bar with cancel button
        self.progressbar = QtWidgets.QProgressBar()
        self.statusBar().showMessage("Ready")
        self.statusBar().addPermanentWidget(self.progressbar)
        self.progressbar.setGeometry(30, 40, 200, 20)
        self.progressbar.setValue(0)
        self.progressbar.hide()
        self.cancelBtn = QtWidgets.QPushButton("Cancel")
        self.cancelBtn.clicked.connect(self.cancel_pressed)
        self.statusBar().addPermanentWidget(self.cancelBtn)
        self.cancelBtn.hide()
        self.cancelling = False

        # Set up connections for IDW
        self.stations = {}
        self.files = []
        self.ui.browseBtn.clicked.connect(self.idw_set_input_folder)
        self.ui.outBrowseBtn.clicked.connect(self.idw_set_output_folder)
        self.ui.resetBtn.clicked.connect(self.idw_reset_input)
        self.ui.runBtn.clicked.connect(self.idw_run)

        # Set up Connections for CFM
        self.ui.observedFileBrowse.clicked.connect(self.cfm_get_obs_file)
        self.ui.historicalFileBrowse.clicked.connect(self.cfm_get_his_file)
        self.ui.futureFileBrowse.clicked.connect(self.cfm_get_fut_file)
        self.ui.runButton.clicked.connect(self.cfm_run)
        self.ui.outBrowse.clicked.connect(self.cfm_get_out_path)
        self.ui.cfmResetBtn.clicked.connect(self.cfm_reset_input)

        # Set up Connections for KNN
        self.ui.knnBrowse.clicked.connect(self.knn_get_input_file)
        self.ui.knnAddFile.clicked.connect(self.knn_add_file)
        self.ui.knnRemoveFile.clicked.connect(self.knn_remove_file)
        self.ui.knnOutputBrowse.clicked.connect(self.knn_set_output_folder)
        self.ui.knnRun.clicked.connect(self.knn_run)
        self.ui.knnResetInput.clicked.connect(self.knn_reset_input)

        tableHHeader = self.ui.knnTableWidget.horizontalHeader()
        tableHHeader.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        tableHHeader.setVisible(True)

    def cancel_pressed(self):
        self.cancelling = True
        self.statusBar().showMessage("Cancelling...")

    def idw_set_input_folder(self):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        self.ui.pathLineEdit.setText(path)

    def idw_set_output_folder(self):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        self.ui.outputLineEdit.setText(path)

    def idw_reset_input(self):
        self.files = []
        self.stations = {}
        self.ui.pathLineEdit.setText("")
        self.ui.outputLineEdit.setText("")
        self.ui.varEdit.setText("")
        self.ui.alphaSpin.setValue(2)
        self.ui.pointsSpin.setValue(4)
        self.ui.extraLineEdit.setText("")
        self.ui.startDateEdit.setDate(QtCore.QDate(1975, 1, 1))
        self.ui.endDateEdit.setDate(QtCore.QDate(2005, 1, 1))
        self.ui.northSpin.setValue(0)
        self.ui.eastSpin.setValue(0)
        self.ui.southSpin.setValue(0)
        self.ui.westSpin.setValue(0)
        self.ui.timeGroupBox.setChecked(False)
        self.ui.spatialGroupBox.setChecked(False)

        R = self.ui.stationTable.rowCount()
        C = self.ui.stationTable.columnCount()

        for r in range(R):
            for c in range(C):
                cell = self.ui.stationTable.item(r, c)
                if cell:
                    cell.setText("")

    def idw_get_stations(self):
        stations = {}
        R = self.ui.stationTable.rowCount()

        for i in range(R):
            name_cell = self.ui.stationTable.item(i, 0)
            lat_cell = self.ui.stationTable.item(i, 1)
            lon_cell = self.ui.stationTable.item(i, 2)

            if not name_cell:
                break
            elif not name_cell.text():
                break

            name = name_cell.text()

            try:
                lat = float(lat_cell.text())
                lon = float(lon_cell.text())
                stations[name] = (lat, lon)
            except ValueError as e:
                QtWidgets.QMessageBox.warning(self, "Input Error", e)

        return stations

    def idw_get_input(self):
        path = self.ui.pathLineEdit.text()
        out = self.ui.outputLineEdit.text()
        varname = self.ui.varEdit.text()
        stations = self.idw_get_stations()
        alpha = self.ui.alphaSpin.value()
        points = self.ui.pointsSpin.value()
        options = self.ui.extraLineEdit.text()

        files = []
        for fl in os.listdir(path):
            if fl.endswith('.nc') and varname + '_' in fl:
                files.append(fl)

        if self.ui.spatialGroupBox.isChecked():
            n = self.ui.northSpin.value()
            e = self.ui.eastSpin.value()
            s = self.ui.southSpin.value()
            w = self.ui.westSpin.value()

            extent = [n, e, s, w]
        else:
            extent = None

        if self.ui.timeGroupBox.isChecked():
            sDate = self.ui.startDateEdit.date().toPyDate()
            eDate = self.ui.endDateEdit.date().toPyDate()

            period = [(sDate.year, sDate.month, sDate.day),
                      (eDate.year, eDate.month, eDate.day)]
        else:
            period = None

        kwargs = {}

        if options:
            for o in options.split(','):
                k, v = o.split('=')
                kwargs[k.strip()] = int(v)

        return (path, out, varname, stations, alpha, points, kwargs, files,
                extent, period)

    def idw_run(self):
        pars = self.idw_get_input()
        (path, out, varname, stations, alpha, points, kwargs, files,
         extent, period) = pars

        def file_splitter(fname):
            *first, _ = fname.split('_')
            return first

        self.statusBar().showMessage("Interpolating...")
        self.progressbar.setRange(0, len(files))
        self.progressbar.setValue(0)
        self.progressbar.show()
        self.cancelBtn.show()

        try:
            for k, group in groupby(files, key=file_splitter):
                if self.cancelling:
                    self.cancelling = False
                    break

                grouped_files = [os.path.join(path, g) for g in group]

                df = idw.idw(grouped_files,
                             varname,
                             stations,
                             extent=extent,
                             period=period,
                             alpha=alpha,
                             k=points,
                             **kwargs)

                df.to_csv(os.path.join(out, 'idw_' + '_'.join(k)) + '.csv')

                new = self.progressbar.value() + len(grouped_files)
                self.progressbar.setValue(new)

        except Exception as e:
            msg = traceback.format_exc(5)
            QtWidgets.QMessageBox.critical(self, "Error", msg)

        finally:
            self.statusBar().showMessage("Ready")
            self.progressbar.reset()
            self.progressbar.hide()
            self.cancelBtn.hide()

    def cfm_reset_input(self):
        self.ui.cfmVarNameEdit.setText("")
        self.ui.observedFileEdit.setText("")
        self.ui.historicalFileEdit.setText("")
        self.ui.futureFileEdit.setText("")
        self.ui.outLineEdit.setText("")
        self.ui.scalingComboBox.setCurrentIndex(0)
        self.ui.binsSpinBox.setValue(25)

    def cfm_get_obs_file(self):
        fl, _ = QFileDialog.getOpenFileName(self, "Select Observed File",
                                            filter="CSV files (*.csv)")
        self.ui.observedFileEdit.setText(fl)

    def cfm_get_his_file(self):
        fl, _ = QFileDialog.getOpenFileName(self,
                                            "Select Historical GCM File",
                                            filter="CSV files (*.csv)")
        self.ui.historicalFileEdit.setText(fl)

    def cfm_get_fut_file(self):
        fl, _ = QFileDialog.getOpenFileName(self, "Select Future GCM File",
                                            filter="CSV files (*.csv)")
        self.ui.futureFileEdit.setText(fl)

    def cfm_get_out_path(self):
        fl = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        self.ui.outLineEdit.setText(fl)

    def cfm_run(self):
        self.statusBar().showMessage("Loading Files...")
        self.progressbar.setRange(0, 4)
        self.progressbar.show()
        self.cancelBtn.show()

        try:
            varname = self.ui.cfmVarNameEdit.text()

            obs_fl = self.ui.observedFileEdit.text()
            obs = pd.read_csv(obs_fl, index_col=[0, 1, 2], header=[0, 1])
            obs = obs.sort_index(axis=1)
            obs = obs.xs(varname, axis=1, level=0, drop_level=False)
            self.progressbar.setValue(1)

            if self.cancelling:
                self.cancelling = False
                return

            his_fl = self.ui.historicalFileEdit.text()
            his = pd.read_csv(his_fl, index_col=[0, 1, 2], header=[0, 1])
            his = his.sort_index(axis=1)
            self.progressbar.setValue(2)

            if self.cancelling:
                self.cancelling = False
                return

            fut_fl = self.ui.futureFileEdit.text()
            fut = pd.read_csv(fut_fl, index_col=[0, 1, 2], header=[0, 1])
            fut = fut.sort_index(axis=1)
            self.progressbar.setValue(3)

            if self.cancelling:
                self.cancelling = False
                return

            method = self.ui.scalingComboBox.currentIndex()
            bins = self.ui.binsSpinBox.value()
            out_path = self.ui.outLineEdit.text()

            fname = os.path.basename(fut_fl)
            fpath = os.path.join(out_path, f"scaled_{fname}")

            self.statusBar().showMessage("Scaling...")

            cfm.cfm(his, fut, obs, method, bins).to_csv(fpath)

        except Exception as e:
            msg = traceback.format_exc(5)
            QtWidgets.QMessageBox.critical(self, "Error", msg)

        finally:
            self.statusBar().showMessage("Ready")
            self.progressbar.setValue(4)
            self.progressbar.reset()
            self.progressbar.hide()
            self.cancelBtn.hide()

    def knn_get_input_file(self):
        fl, _ = QFileDialog.getOpenFileName(self, "Select Input File",
                                            filter="CSV files (*.csv)")
        self.ui.knnInputEdit.setText(fl)

    def knn_add_file(self):
        varname = self.ui.knnVarNameEdit.text()
        fl = self.ui.knnInputEdit.text()
        perturb = self.ui.knnPerturbation.currentIndex()

        rowIdx = self.ui.knnTableWidget.rowCount()
        self.ui.knnTableWidget.insertRow(rowIdx)

        varname_item = QtWidgets.QTableWidgetItem(varname)
        fl_item = QtWidgets.QTableWidgetItem(fl)
        perturbation_item = QtWidgets.QTableWidgetItem(str(perturb))

        self.ui.knnTableWidget.setItem(rowIdx, 0, varname_item)
        self.ui.knnTableWidget.setItem(rowIdx, 1, fl_item)
        self.ui.knnTableWidget.setItem(rowIdx, 2, perturbation_item)

    def knn_remove_file(self):
        rows = self.ui.knnTableWidget.selectionModel().selectedRows()

        for row in rows:
            self.ui.knnTableWidget.removeRow(row.row())

    def knn_set_output_folder(self):
        path, k = QFileDialog.getSaveFileName(None, "Save Output", "", ".csv")
        self.ui.knnOutputLineEdit.setText(path + k)

    def knn_reset_input(self):
        self.ui.knnInputEdit.setText("")
        self.ui.knnVarNameEdit.setText("")
        self.ui.knnPerturbation.setCurrentIndex(0)
        self.ui.windowSpin.setValue(14)
        self.ui.lambdaSpin.setValue(0.9)
        self.ui.replicationsSpin.setValue(5)
        self.ui.blockSizeSpin.setValue(10)
        self.ui.knnOutputLineEdit.setText("")

        R = self.ui.knnTableWidget.rowCount()

        for i in range(R)[::-1]:
            self.ui.knnTableWidget.removeRow(i)

    def knn_run(self):
        w = self.ui.windowSpin.value()
        interp = self.ui.lambdaSpin.value()
        runs = self.ui.replicationsSpin.value()
        B = self.ui.blockSizeSpin.value()
        outpath = self.ui.knnOutputLineEdit.text()

        dfs = []
        perturb = {}
        R = self.ui.knnTableWidget.rowCount()

        self.statusBar().showMessage("Loading Files...")
        self.progressbar.setRange(0, R + runs)
        self.progressbar.setValue(0)
        self.progressbar.show()
        self.cancelBtn.show()

        try:

            for i in range(R):
                v = self.ui.knnTableWidget.item(i, 0).text()
                f = self.ui.knnTableWidget.item(i, 1).text()
                p = self.ui.knnTableWidget.item(i, 2).text()

                perturb[v] = int(p)
                dfs.append(pd.read_csv(f, index_col=[0, 1, 2], header=[0, 1]))

                if self.cancelling:
                    self.cancelling = False
                    return

                self.progressbar.setValue(i + 1)

            df = pd.concat(dfs, axis=1).sort_index(axis=1)
            P = np.array([perturb[v] for v, s in df.columns], np.uint8)

            generator = knn.KNN(df, P, w=w, B=B, interp=interp)

            for i, r in enumerate(range(runs)):
                msg = f"Generating replication {i + 1} of {runs}"
                self.statusBar().showMessage(msg)

                if self.cancelling:
                    self.cancelling = False
                    return

                result = generator.bootstrap(i)
                if i == 0:
                    result.to_csv(outpath)
                else:
                    result.to_csv(outpath, mode='a')

                self.progressbar.setValue(R + i)

        except Exception as e:
            msg = traceback.format_exc(5)
            QtWidgets.QMessageBox.critical(self, "Error", msg)

        finally:
            self.statusBar().showMessage("Ready")
            self.progressbar.reset()
            self.progressbar.hide()
            self.cancelBtn.hide()


class PastableTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Paste):
            self.paste()
        else:
            super().keyPressEvent(event)

    def paste(self):
        data = QtWidgets.QApplication.clipboard().text().split('\n')

        for i, row in enumerate(data):
            for j, element in enumerate(row.split('\t')):
                self.setItem(i, j, QtWidgets.QTableWidgetItem(element))


# Created by: PyQt5 UI code generator 5.6

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(670, 531)
        MainWindow.setMinimumSize(QtCore.QSize(0, 0))
        MainWindow.setMaximumSize(QtCore.QSize(1000, 1000))
        MainWindow.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.tab)
        self.horizontalLayout_2.setContentsMargins(8, 8, 8, 8)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_8 = QtWidgets.QVBoxLayout()
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.filesGroupBox = QtWidgets.QGroupBox(self.tab)
        self.filesGroupBox.setObjectName("filesGroupBox")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.filesGroupBox)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.formLayout_4 = QtWidgets.QFormLayout()
        self.formLayout_4.setObjectName("formLayout_4")
        self.label = QtWidgets.QLabel(self.filesGroupBox)
        self.label.setObjectName("label")
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.pathLineEdit = QtWidgets.QLineEdit(self.filesGroupBox)
        self.pathLineEdit.setObjectName("pathLineEdit")
        self.formLayout_4.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.pathLineEdit)
        self.outputLabel = QtWidgets.QLabel(self.filesGroupBox)
        self.outputLabel.setObjectName("outputLabel")
        self.formLayout_4.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.outputLabel)
        self.outputLineEdit = QtWidgets.QLineEdit(self.filesGroupBox)
        self.outputLineEdit.setObjectName("outputLineEdit")
        self.formLayout_4.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.outputLineEdit)
        self.horizontalLayout.addLayout(self.formLayout_4)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.browseBtn = QtWidgets.QPushButton(self.filesGroupBox)
        self.browseBtn.setObjectName("browseBtn")
        self.verticalLayout_2.addWidget(self.browseBtn)
        self.outBrowseBtn = QtWidgets.QPushButton(self.filesGroupBox)
        self.outBrowseBtn.setObjectName("outBrowseBtn")
        self.verticalLayout_2.addWidget(self.outBrowseBtn)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_7.addLayout(self.horizontalLayout)
        self.verticalLayout_8.addWidget(self.filesGroupBox)
        self.groupBox = QtWidgets.QGroupBox(self.tab)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.stationTable = PastableTableWidget(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.stationTable.sizePolicy().hasHeightForWidth())
        self.stationTable.setSizePolicy(sizePolicy)
        self.stationTable.setAutoFillBackground(False)
        self.stationTable.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.stationTable.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.stationTable.setGridStyle(QtCore.Qt.SolidLine)
        self.stationTable.setRowCount(100)
        self.stationTable.setObjectName("stationTable")
        self.stationTable.setColumnCount(3)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        item.setFont(font)
        self.stationTable.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.stationTable.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.stationTable.setHorizontalHeaderItem(2, item)
        self.stationTable.horizontalHeader().setVisible(True)
        self.stationTable.horizontalHeader().setCascadingSectionResizes(True)
        self.stationTable.horizontalHeader().setSortIndicatorShown(False)
        self.stationTable.horizontalHeader().setStretchLastSection(False)
        self.stationTable.verticalHeader().setVisible(True)
        self.stationTable.verticalHeader().setCascadingSectionResizes(False)
        self.stationTable.verticalHeader().setStretchLastSection(False)
        self.verticalLayout.addWidget(self.stationTable)
        self.verticalLayout_8.addWidget(self.groupBox)
        self.horizontalLayout_2.addLayout(self.verticalLayout_8)
        self.optionsGroupBox = QtWidgets.QGroupBox(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.optionsGroupBox.sizePolicy().hasHeightForWidth())
        self.optionsGroupBox.setSizePolicy(sizePolicy)
        self.optionsGroupBox.setMinimumSize(QtCore.QSize(250, 0))
        self.optionsGroupBox.setObjectName("optionsGroupBox")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.optionsGroupBox)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.groupBox_4 = QtWidgets.QGroupBox(self.optionsGroupBox)
        self.groupBox_4.setObjectName("groupBox_4")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.groupBox_4)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.formLayout_3 = QtWidgets.QFormLayout()
        self.formLayout_3.setObjectName("formLayout_3")
        self.variableLabel = QtWidgets.QLabel(self.groupBox_4)
        self.variableLabel.setObjectName("variableLabel")
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.variableLabel)
        self.varEdit = QtWidgets.QLineEdit(self.groupBox_4)
        self.varEdit.setPlaceholderText("")
        self.varEdit.setClearButtonEnabled(False)
        self.varEdit.setObjectName("varEdit")
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.varEdit)
        self.alphaLabel = QtWidgets.QLabel(self.groupBox_4)
        self.alphaLabel.setObjectName("alphaLabel")
        self.formLayout_3.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.alphaLabel)
        self.alphaSpin = QtWidgets.QDoubleSpinBox(self.groupBox_4)
        self.alphaSpin.setAccelerated(False)
        self.alphaSpin.setProperty("showGroupSeparator", False)
        self.alphaSpin.setDecimals(1)
        self.alphaSpin.setMinimum(1.0)
        self.alphaSpin.setMaximum(10.0)
        self.alphaSpin.setProperty("value", 2.0)
        self.alphaSpin.setObjectName("alphaSpin")
        self.formLayout_3.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.alphaSpin)
        self.pointsLabel = QtWidgets.QLabel(self.groupBox_4)
        self.pointsLabel.setObjectName("pointsLabel")
        self.formLayout_3.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.pointsLabel)
        self.pointsSpin = QtWidgets.QSpinBox(self.groupBox_4)
        self.pointsSpin.setMinimum(2)
        self.pointsSpin.setMaximum(10)
        self.pointsSpin.setProperty("value", 4)
        self.pointsSpin.setObjectName("pointsSpin")
        self.formLayout_3.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.pointsSpin)
        self.label_2 = QtWidgets.QLabel(self.groupBox_4)
        self.label_2.setObjectName("label_2")
        self.formLayout_3.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.extraLineEdit = QtWidgets.QLineEdit(self.groupBox_4)
        self.extraLineEdit.setObjectName("extraLineEdit")
        self.formLayout_3.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.extraLineEdit)
        self.verticalLayout_5.addLayout(self.formLayout_3)
        self.verticalLayout_6.addWidget(self.groupBox_4)
        self.timeGroupBox = QtWidgets.QGroupBox(self.optionsGroupBox)
        self.timeGroupBox.setCheckable(True)
        self.timeGroupBox.setChecked(False)
        self.timeGroupBox.setObjectName("timeGroupBox")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.timeGroupBox)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.startLabel = QtWidgets.QLabel(self.timeGroupBox)
        self.startLabel.setObjectName("startLabel")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.startLabel)
        self.startDateEdit = QtWidgets.QDateEdit(self.timeGroupBox)
        self.startDateEdit.setTime(QtCore.QTime(12, 0, 0))
        self.startDateEdit.setCalendarPopup(False)
        self.startDateEdit.setDate(QtCore.QDate(1975, 1, 1))
        self.startDateEdit.setObjectName("startDateEdit")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.startDateEdit)
        self.endLabel = QtWidgets.QLabel(self.timeGroupBox)
        self.endLabel.setObjectName("endLabel")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.endLabel)
        self.endDateEdit = QtWidgets.QDateEdit(self.timeGroupBox)
        self.endDateEdit.setTime(QtCore.QTime(12, 0, 0))
        self.endDateEdit.setCalendarPopup(False)
        self.endDateEdit.setDate(QtCore.QDate(2005, 1, 1))
        self.endDateEdit.setObjectName("endDateEdit")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.endDateEdit)
        self.verticalLayout_3.addLayout(self.formLayout)
        self.verticalLayout_6.addWidget(self.timeGroupBox)
        self.spatialGroupBox = QtWidgets.QGroupBox(self.optionsGroupBox)
        self.spatialGroupBox.setCheckable(True)
        self.spatialGroupBox.setChecked(False)
        self.spatialGroupBox.setObjectName("spatialGroupBox")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.spatialGroupBox)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.formLayout_2 = QtWidgets.QFormLayout()
        self.formLayout_2.setObjectName("formLayout_2")
        self.northLabel = QtWidgets.QLabel(self.spatialGroupBox)
        self.northLabel.setObjectName("northLabel")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.northLabel)
        self.northSpin = QtWidgets.QDoubleSpinBox(self.spatialGroupBox)
        self.northSpin.setPrefix("")
        self.northSpin.setObjectName("northSpin")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.northSpin)
        self.eastLabel = QtWidgets.QLabel(self.spatialGroupBox)
        self.eastLabel.setObjectName("eastLabel")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.eastLabel)
        self.eastSpin = QtWidgets.QDoubleSpinBox(self.spatialGroupBox)
        self.eastSpin.setObjectName("eastSpin")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.eastSpin)
        self.southLabel = QtWidgets.QLabel(self.spatialGroupBox)
        self.southLabel.setObjectName("southLabel")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.southLabel)
        self.southSpin = QtWidgets.QDoubleSpinBox(self.spatialGroupBox)
        self.southSpin.setObjectName("southSpin")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.southSpin)
        self.westLabel = QtWidgets.QLabel(self.spatialGroupBox)
        self.westLabel.setObjectName("westLabel")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.westLabel)
        self.westSpin = QtWidgets.QDoubleSpinBox(self.spatialGroupBox)
        self.westSpin.setObjectName("westSpin")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.westSpin)
        self.verticalLayout_4.addLayout(self.formLayout_2)
        self.verticalLayout_6.addWidget(self.spatialGroupBox)
        self.resetBtn = QtWidgets.QPushButton(self.optionsGroupBox)
        self.resetBtn.setObjectName("resetBtn")
        self.verticalLayout_6.addWidget(self.resetBtn)
        self.runBtn = QtWidgets.QPushButton(self.optionsGroupBox)
        self.runBtn.setObjectName("runBtn")
        self.verticalLayout_6.addWidget(self.runBtn)
        self.horizontalLayout_2.addWidget(self.optionsGroupBox)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.verticalLayout_15 = QtWidgets.QVBoxLayout(self.tab_2)
        self.verticalLayout_15.setContentsMargins(8, 8, 8, 8)
        self.verticalLayout_15.setObjectName("verticalLayout_15")
        self.verticalLayout_12 = QtWidgets.QVBoxLayout()
        self.verticalLayout_12.setObjectName("verticalLayout_12")
        self.inputFilesGroupBox = QtWidgets.QGroupBox(self.tab_2)
        self.inputFilesGroupBox.setObjectName("inputFilesGroupBox")
        self.verticalLayout_10 = QtWidgets.QVBoxLayout(self.inputFilesGroupBox)
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.cfmVarNameLabel = QtWidgets.QLabel(self.inputFilesGroupBox)
        self.cfmVarNameLabel.setObjectName("cfmVarNameLabel")
        self.gridLayout.addWidget(self.cfmVarNameLabel, 0, 0, 1, 1)
        self.cfmVarNameEdit = QtWidgets.QLineEdit(self.inputFilesGroupBox)
        self.cfmVarNameEdit.setObjectName("cfmVarNameEdit")
        self.gridLayout.addWidget(self.cfmVarNameEdit, 0, 1, 1, 1)
        self.observedFileLabel = QtWidgets.QLabel(self.inputFilesGroupBox)
        self.observedFileLabel.setObjectName("observedFileLabel")
        self.gridLayout.addWidget(self.observedFileLabel, 1, 0, 1, 1)
        self.observedFileEdit = QtWidgets.QLineEdit(self.inputFilesGroupBox)
        self.observedFileEdit.setObjectName("observedFileEdit")
        self.gridLayout.addWidget(self.observedFileEdit, 1, 1, 1, 1)
        self.observedFileBrowse = QtWidgets.QPushButton(self.inputFilesGroupBox)
        self.observedFileBrowse.setObjectName("observedFileBrowse")
        self.gridLayout.addWidget(self.observedFileBrowse, 1, 2, 1, 1)
        self.historicalFileLabel = QtWidgets.QLabel(self.inputFilesGroupBox)
        self.historicalFileLabel.setObjectName("historicalFileLabel")
        self.gridLayout.addWidget(self.historicalFileLabel, 2, 0, 1, 1)
        self.historicalFileEdit = QtWidgets.QLineEdit(self.inputFilesGroupBox)
        self.historicalFileEdit.setObjectName("historicalFileEdit")
        self.gridLayout.addWidget(self.historicalFileEdit, 2, 1, 1, 1)
        self.historicalFileBrowse = QtWidgets.QPushButton(self.inputFilesGroupBox)
        self.historicalFileBrowse.setObjectName("historicalFileBrowse")
        self.gridLayout.addWidget(self.historicalFileBrowse, 2, 2, 1, 1)
        self.futureFileLabel = QtWidgets.QLabel(self.inputFilesGroupBox)
        self.futureFileLabel.setObjectName("futureFileLabel")
        self.gridLayout.addWidget(self.futureFileLabel, 3, 0, 1, 1)
        self.futureFileEdit = QtWidgets.QLineEdit(self.inputFilesGroupBox)
        self.futureFileEdit.setObjectName("futureFileEdit")
        self.gridLayout.addWidget(self.futureFileEdit, 3, 1, 1, 1)
        self.futureFileBrowse = QtWidgets.QPushButton(self.inputFilesGroupBox)
        self.futureFileBrowse.setObjectName("futureFileBrowse")
        self.gridLayout.addWidget(self.futureFileBrowse, 3, 2, 1, 1)
        self.outputPathLabel = QtWidgets.QLabel(self.inputFilesGroupBox)
        self.outputPathLabel.setObjectName("outputPathLabel")
        self.gridLayout.addWidget(self.outputPathLabel, 4, 0, 1, 1)
        self.outLineEdit = QtWidgets.QLineEdit(self.inputFilesGroupBox)
        self.outLineEdit.setObjectName("outLineEdit")
        self.gridLayout.addWidget(self.outLineEdit, 4, 1, 1, 1)
        self.outBrowse = QtWidgets.QPushButton(self.inputFilesGroupBox)
        self.outBrowse.setObjectName("outBrowse")
        self.gridLayout.addWidget(self.outBrowse, 4, 2, 1, 1)
        self.verticalLayout_10.addLayout(self.gridLayout)
        self.verticalLayout_12.addWidget(self.inputFilesGroupBox)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.optionsGroupBox_2 = QtWidgets.QGroupBox(self.tab_2)
        self.optionsGroupBox_2.setObjectName("optionsGroupBox_2")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout(self.optionsGroupBox_2)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.scalingLabel = QtWidgets.QLabel(self.optionsGroupBox_2)
        self.scalingLabel.setObjectName("scalingLabel")
        self.gridLayout_2.addWidget(self.scalingLabel, 0, 0, 1, 1)
        self.scalingComboBox = QtWidgets.QComboBox(self.optionsGroupBox_2)
        self.scalingComboBox.setObjectName("scalingComboBox")
        self.scalingComboBox.addItem("")
        self.scalingComboBox.addItem("")
        self.gridLayout_2.addWidget(self.scalingComboBox, 0, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(self.optionsGroupBox_2)
        self.label_5.setObjectName("label_5")
        self.gridLayout_2.addWidget(self.label_5, 1, 0, 1, 1)
        self.binsSpinBox = QtWidgets.QSpinBox(self.optionsGroupBox_2)
        self.binsSpinBox.setMinimum(2)
        self.binsSpinBox.setMaximum(100)
        self.binsSpinBox.setProperty("value", 25)
        self.binsSpinBox.setObjectName("binsSpinBox")
        self.gridLayout_2.addWidget(self.binsSpinBox, 1, 1, 1, 1)
        self.verticalLayout_9.addLayout(self.gridLayout_2)
        self.horizontalLayout_5.addWidget(self.optionsGroupBox_2)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem)
        self.verticalLayout_11 = QtWidgets.QVBoxLayout()
        self.verticalLayout_11.setObjectName("verticalLayout_11")
        self.cfmResetBtn = QtWidgets.QPushButton(self.tab_2)
        self.cfmResetBtn.setObjectName("cfmResetBtn")
        self.verticalLayout_11.addWidget(self.cfmResetBtn)
        self.runButton = QtWidgets.QPushButton(self.tab_2)
        self.runButton.setMaximumSize(QtCore.QSize(100, 16777215))
        self.runButton.setObjectName("runButton")
        self.verticalLayout_11.addWidget(self.runButton)
        self.horizontalLayout_5.addLayout(self.verticalLayout_11)
        self.verticalLayout_12.addLayout(self.horizontalLayout_5)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_12.addItem(spacerItem1)
        self.verticalLayout_15.addLayout(self.verticalLayout_12)
        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QtWidgets.QWidget()
        self.tab_3.setObjectName("tab_3")
        self.verticalLayout_13 = QtWidgets.QVBoxLayout(self.tab_3)
        self.verticalLayout_13.setContentsMargins(8, 8, 8, 8)
        self.verticalLayout_13.setObjectName("verticalLayout_13")
        self.groupBox_3 = QtWidgets.QGroupBox(self.tab_3)
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout_27 = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_27.setObjectName("verticalLayout_27")
        self.gridLayout_5 = QtWidgets.QGridLayout()
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_5.setObjectName("gridLayout_5")
        spacerItem2 = QtWidgets.QSpacerItem(358, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_5.addItem(spacerItem2, 1, 3, 1, 2)
        self.knnAddFile = QtWidgets.QPushButton(self.groupBox_3)
        self.knnAddFile.setObjectName("knnAddFile")
        self.gridLayout_5.addWidget(self.knnAddFile, 3, 4, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(408, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_5.addItem(spacerItem3, 2, 2, 1, 3)
        self.inputFileLabel = QtWidgets.QLabel(self.groupBox_3)
        self.inputFileLabel.setObjectName("inputFileLabel")
        self.gridLayout_5.addWidget(self.inputFileLabel, 0, 0, 1, 1)
        self.knnBrowse = QtWidgets.QPushButton(self.groupBox_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.knnBrowse.sizePolicy().hasHeightForWidth())
        self.knnBrowse.setSizePolicy(sizePolicy)
        self.knnBrowse.setObjectName("knnBrowse")
        self.gridLayout_5.addWidget(self.knnBrowse, 0, 4, 1, 1)
        self.knnVarNameEdit = QtWidgets.QLineEdit(self.groupBox_3)
        self.knnVarNameEdit.setObjectName("knnVarNameEdit")
        self.gridLayout_5.addWidget(self.knnVarNameEdit, 1, 1, 1, 2)
        self.perturbationLabel = QtWidgets.QLabel(self.groupBox_3)
        self.perturbationLabel.setObjectName("perturbationLabel")
        self.gridLayout_5.addWidget(self.perturbationLabel, 2, 0, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(488, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_5.addItem(spacerItem4, 3, 0, 1, 4)
        self.knnInputEdit = QtWidgets.QLineEdit(self.groupBox_3)
        self.knnInputEdit.setObjectName("knnInputEdit")
        self.gridLayout_5.addWidget(self.knnInputEdit, 0, 1, 1, 3)
        self.varNameLabel = QtWidgets.QLabel(self.groupBox_3)
        self.varNameLabel.setObjectName("varNameLabel")
        self.gridLayout_5.addWidget(self.varNameLabel, 1, 0, 1, 1)
        self.knnPerturbation = QtWidgets.QComboBox(self.groupBox_3)
        self.knnPerturbation.setObjectName("knnPerturbation")
        self.knnPerturbation.addItem("")
        self.knnPerturbation.addItem("")
        self.knnPerturbation.addItem("")
        self.gridLayout_5.addWidget(self.knnPerturbation, 2, 1, 1, 1)
        self.verticalLayout_27.addLayout(self.gridLayout_5)
        self.verticalLayout_13.addWidget(self.groupBox_3)
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.groupBox_7 = QtWidgets.QGroupBox(self.tab_3)
        self.groupBox_7.setObjectName("groupBox_7")
        self.verticalLayout_31 = QtWidgets.QVBoxLayout(self.groupBox_7)
        self.verticalLayout_31.setObjectName("verticalLayout_31")
        self.verticalLayout_30 = QtWidgets.QVBoxLayout()
        self.verticalLayout_30.setObjectName("verticalLayout_30")
        self.knnTableWidget = QtWidgets.QTableWidget(self.groupBox_7)
        self.knnTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.knnTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.knnTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.knnTableWidget.setRowCount(0)
        self.knnTableWidget.setObjectName("knnTableWidget")
        self.knnTableWidget.setColumnCount(3)
        item = QtWidgets.QTableWidgetItem()
        self.knnTableWidget.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.knnTableWidget.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.knnTableWidget.setHorizontalHeaderItem(2, item)
        self.knnTableWidget.horizontalHeader().setVisible(False)
        self.knnTableWidget.horizontalHeader().setCascadingSectionResizes(False)
        self.knnTableWidget.verticalHeader().setVisible(False)
        self.knnTableWidget.verticalHeader().setCascadingSectionResizes(False)
        self.verticalLayout_30.addWidget(self.knnTableWidget)
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_10.addItem(spacerItem5)
        self.knnRemoveFile = QtWidgets.QPushButton(self.groupBox_7)
        self.knnRemoveFile.setObjectName("knnRemoveFile")
        self.horizontalLayout_10.addWidget(self.knnRemoveFile)
        self.verticalLayout_30.addLayout(self.horizontalLayout_10)
        self.verticalLayout_31.addLayout(self.verticalLayout_30)
        self.horizontalLayout_11.addWidget(self.groupBox_7)
        self.groupBox_6 = QtWidgets.QGroupBox(self.tab_3)
        self.groupBox_6.setObjectName("groupBox_6")
        self.formLayout_9 = QtWidgets.QFormLayout(self.groupBox_6)
        self.formLayout_9.setObjectName("formLayout_9")
        self.windowLabel = QtWidgets.QLabel(self.groupBox_6)
        self.windowLabel.setObjectName("windowLabel")
        self.formLayout_9.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.windowLabel)
        self.windowSpin = QtWidgets.QSpinBox(self.groupBox_6)
        self.windowSpin.setReadOnly(False)
        self.windowSpin.setPrefix("")
        self.windowSpin.setMinimum(4)
        self.windowSpin.setMaximum(30)
        self.windowSpin.setSingleStep(2)
        self.windowSpin.setProperty("value", 14)
        self.windowSpin.setObjectName("windowSpin")
        self.formLayout_9.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.windowSpin)
        self.lambdaLabel = QtWidgets.QLabel(self.groupBox_6)
        self.lambdaLabel.setObjectName("lambdaLabel")
        self.formLayout_9.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.lambdaLabel)
        self.lambdaSpin = QtWidgets.QDoubleSpinBox(self.groupBox_6)
        self.lambdaSpin.setMaximum(1.0)
        self.lambdaSpin.setSingleStep(0.1)
        self.lambdaSpin.setProperty("value", 0.9)
        self.lambdaSpin.setObjectName("lambdaSpin")
        self.formLayout_9.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.lambdaSpin)
        self.replicationsLabel = QtWidgets.QLabel(self.groupBox_6)
        self.replicationsLabel.setObjectName("replicationsLabel")
        self.formLayout_9.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.replicationsLabel)
        self.replicationsSpin = QtWidgets.QSpinBox(self.groupBox_6)
        self.replicationsSpin.setMinimum(1)
        self.replicationsSpin.setMaximum(9999)
        self.replicationsSpin.setProperty("value", 5)
        self.replicationsSpin.setObjectName("replicationsSpin")
        self.formLayout_9.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.replicationsSpin)
        self.blockSizeLabel = QtWidgets.QLabel(self.groupBox_6)
        self.blockSizeLabel.setObjectName("blockSizeLabel")
        self.formLayout_9.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.blockSizeLabel)
        self.blockSizeSpin = QtWidgets.QSpinBox(self.groupBox_6)
        self.blockSizeSpin.setMinimum(1)
        self.blockSizeSpin.setMaximum(30)
        self.blockSizeSpin.setProperty("value", 10)
        self.blockSizeSpin.setObjectName("blockSizeSpin")
        self.formLayout_9.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.blockSizeSpin)
        self.horizontalLayout_11.addWidget(self.groupBox_6)
        self.verticalLayout_13.addLayout(self.horizontalLayout_11)
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.knnResetInput = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.knnResetInput.sizePolicy().hasHeightForWidth())
        self.knnResetInput.setSizePolicy(sizePolicy)
        self.knnResetInput.setObjectName("knnResetInput")
        self.gridLayout_3.addWidget(self.knnResetInput, 0, 3, 1, 1)
        self.knnOutputPathLabel = QtWidgets.QLabel(self.tab_3)
        self.knnOutputPathLabel.setObjectName("knnOutputPathLabel")
        self.gridLayout_3.addWidget(self.knnOutputPathLabel, 1, 0, 1, 1)
        self.knnOutputLineEdit = QtWidgets.QLineEdit(self.tab_3)
        self.knnOutputLineEdit.setObjectName("knnOutputLineEdit")
        self.gridLayout_3.addWidget(self.knnOutputLineEdit, 1, 1, 1, 1)
        self.knnOutputBrowse = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.knnOutputBrowse.sizePolicy().hasHeightForWidth())
        self.knnOutputBrowse.setSizePolicy(sizePolicy)
        self.knnOutputBrowse.setObjectName("knnOutputBrowse")
        self.gridLayout_3.addWidget(self.knnOutputBrowse, 1, 2, 1, 1)
        self.knnRun = QtWidgets.QPushButton(self.tab_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.knnRun.sizePolicy().hasHeightForWidth())
        self.knnRun.setSizePolicy(sizePolicy)
        self.knnRun.setObjectName("knnRun")
        self.gridLayout_3.addWidget(self.knnRun, 1, 3, 1, 1)
        self.verticalLayout_13.addLayout(self.gridLayout_3)
        self.tabWidget.addTab(self.tab_3, "")
        self.horizontalLayout_3.addWidget(self.tabWidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        MainWindow.setTabOrder(self.pathLineEdit, self.browseBtn)
        MainWindow.setTabOrder(self.browseBtn, self.outputLineEdit)
        MainWindow.setTabOrder(self.outputLineEdit, self.outBrowseBtn)
        MainWindow.setTabOrder(self.outBrowseBtn, self.stationTable)
        MainWindow.setTabOrder(self.stationTable, self.varEdit)
        MainWindow.setTabOrder(self.varEdit, self.alphaSpin)
        MainWindow.setTabOrder(self.alphaSpin, self.pointsSpin)
        MainWindow.setTabOrder(self.pointsSpin, self.extraLineEdit)
        MainWindow.setTabOrder(self.extraLineEdit, self.timeGroupBox)
        MainWindow.setTabOrder(self.timeGroupBox, self.startDateEdit)
        MainWindow.setTabOrder(self.startDateEdit, self.endDateEdit)
        MainWindow.setTabOrder(self.endDateEdit, self.spatialGroupBox)
        MainWindow.setTabOrder(self.spatialGroupBox, self.northSpin)
        MainWindow.setTabOrder(self.northSpin, self.eastSpin)
        MainWindow.setTabOrder(self.eastSpin, self.southSpin)
        MainWindow.setTabOrder(self.southSpin, self.westSpin)
        MainWindow.setTabOrder(self.westSpin, self.resetBtn)
        MainWindow.setTabOrder(self.resetBtn, self.runBtn)
        MainWindow.setTabOrder(self.runBtn, self.tabWidget)
        MainWindow.setTabOrder(self.tabWidget, self.cfmVarNameEdit)
        MainWindow.setTabOrder(self.cfmVarNameEdit, self.observedFileEdit)
        MainWindow.setTabOrder(self.observedFileEdit, self.observedFileBrowse)
        MainWindow.setTabOrder(self.observedFileBrowse, self.historicalFileEdit)
        MainWindow.setTabOrder(self.historicalFileEdit, self.historicalFileBrowse)
        MainWindow.setTabOrder(self.historicalFileBrowse, self.futureFileEdit)
        MainWindow.setTabOrder(self.futureFileEdit, self.futureFileBrowse)
        MainWindow.setTabOrder(self.futureFileBrowse, self.outLineEdit)
        MainWindow.setTabOrder(self.outLineEdit, self.outBrowse)
        MainWindow.setTabOrder(self.outBrowse, self.scalingComboBox)
        MainWindow.setTabOrder(self.scalingComboBox, self.binsSpinBox)
        MainWindow.setTabOrder(self.binsSpinBox, self.cfmResetBtn)
        MainWindow.setTabOrder(self.cfmResetBtn, self.runButton)
        MainWindow.setTabOrder(self.runButton, self.knnInputEdit)
        MainWindow.setTabOrder(self.knnInputEdit, self.knnBrowse)
        MainWindow.setTabOrder(self.knnBrowse, self.knnVarNameEdit)
        MainWindow.setTabOrder(self.knnVarNameEdit, self.knnPerturbation)
        MainWindow.setTabOrder(self.knnPerturbation, self.knnAddFile)
        MainWindow.setTabOrder(self.knnAddFile, self.knnTableWidget)
        MainWindow.setTabOrder(self.knnTableWidget, self.knnRemoveFile)
        MainWindow.setTabOrder(self.knnRemoveFile, self.windowSpin)
        MainWindow.setTabOrder(self.windowSpin, self.lambdaSpin)
        MainWindow.setTabOrder(self.lambdaSpin, self.replicationsSpin)
        MainWindow.setTabOrder(self.replicationsSpin, self.blockSizeSpin)
        MainWindow.setTabOrder(self.blockSizeSpin, self.knnOutputLineEdit)
        MainWindow.setTabOrder(self.knnOutputLineEdit, self.knnOutputBrowse)
        MainWindow.setTabOrder(self.knnOutputBrowse, self.knnResetInput)
        MainWindow.setTabOrder(self.knnResetInput, self.knnRun)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "GCM Processing"))
        self.filesGroupBox.setTitle(_translate("MainWindow", "Input Files"))
        self.label.setText(_translate("MainWindow", "Path"))
        self.outputLabel.setText(_translate("MainWindow", "Ouput"))
        self.browseBtn.setText(_translate("MainWindow", "Browse..."))
        self.outBrowseBtn.setText(_translate("MainWindow", "Browse..."))
        self.groupBox.setTitle(_translate("MainWindow", "Stations"))
        self.stationTable.setSortingEnabled(False)
        item = self.stationTable.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Name"))
        item = self.stationTable.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Lat (° N)"))
        item = self.stationTable.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Lon (° E)"))
        self.optionsGroupBox.setTitle(_translate("MainWindow", "Options"))
        self.groupBox_4.setTitle(_translate("MainWindow", "Parameters"))
        self.variableLabel.setText(_translate("MainWindow", "Variable"))
        self.alphaLabel.setText(_translate("MainWindow", "Alpha"))
        self.pointsLabel.setText(_translate("MainWindow", "Points"))
        self.label_2.setText(_translate("MainWindow", "Filter"))
        self.timeGroupBox.setTitle(_translate("MainWindow", "Time Bounds"))
        self.startLabel.setText(_translate("MainWindow", "Start Date"))
        self.endLabel.setText(_translate("MainWindow", "End Date"))
        self.spatialGroupBox.setTitle(_translate("MainWindow", "Spatial Extent"))
        self.northLabel.setText(_translate("MainWindow", "North"))
        self.northSpin.setSuffix(_translate("MainWindow", " ° N"))
        self.eastLabel.setText(_translate("MainWindow", "East"))
        self.eastSpin.setSuffix(_translate("MainWindow", " ° E"))
        self.southLabel.setText(_translate("MainWindow", "South"))
        self.southSpin.setSuffix(_translate("MainWindow", " ° N"))
        self.westLabel.setText(_translate("MainWindow", "West"))
        self.westSpin.setSuffix(_translate("MainWindow", " ° E"))
        self.resetBtn.setText(_translate("MainWindow", "Reset"))
        self.runBtn.setText(_translate("MainWindow", "Run"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Interpolation"))
        self.inputFilesGroupBox.setTitle(_translate("MainWindow", "Input Files"))
        self.cfmVarNameLabel.setText(_translate("MainWindow", "Variable Name"))
        self.observedFileLabel.setText(_translate("MainWindow", "Observed File"))
        self.observedFileBrowse.setText(_translate("MainWindow", "Browse..."))
        self.historicalFileLabel.setText(_translate("MainWindow", "Historical GCM File"))
        self.historicalFileBrowse.setText(_translate("MainWindow", "Browse..."))
        self.futureFileLabel.setText(_translate("MainWindow", "Future GCM File"))
        self.futureFileBrowse.setText(_translate("MainWindow", "Browse..."))
        self.outputPathLabel.setText(_translate("MainWindow", "Output Path"))
        self.outBrowse.setText(_translate("MainWindow", "Browse..."))
        self.optionsGroupBox_2.setTitle(_translate("MainWindow", "Options"))
        self.scalingLabel.setText(_translate("MainWindow", "Scaling Method"))
        self.scalingComboBox.setItemText(0, _translate("MainWindow", "Additive"))
        self.scalingComboBox.setItemText(1, _translate("MainWindow", "Multiplicative"))
        self.label_5.setText(_translate("MainWindow", "Bins"))
        self.cfmResetBtn.setText(_translate("MainWindow", "Reset"))
        self.runButton.setText(_translate("MainWindow", "Run"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Scaling"))
        self.groupBox_3.setTitle(_translate("MainWindow", "Add Variables"))
        self.knnAddFile.setText(_translate("MainWindow", "Add"))
        self.inputFileLabel.setText(_translate("MainWindow", "Input File"))
        self.knnBrowse.setText(_translate("MainWindow", "Browse..."))
        self.perturbationLabel.setText(_translate("MainWindow", "Perturbation"))
        self.varNameLabel.setText(_translate("MainWindow", "Variable Name"))
        self.knnPerturbation.setItemText(0, _translate("MainWindow", "(0) None"))
        self.knnPerturbation.setItemText(1, _translate("MainWindow", "(1) Normal"))
        self.knnPerturbation.setItemText(2, _translate("MainWindow", "(2) Log-Normal"))
        self.groupBox_7.setTitle(_translate("MainWindow", "Current Variables"))
        item = self.knnTableWidget.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Variable Name"))
        item = self.knnTableWidget.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "File"))
        item = self.knnTableWidget.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Perturbation"))
        self.knnRemoveFile.setText(_translate("MainWindow", "Remove"))
        self.groupBox_6.setTitle(_translate("MainWindow", "Options"))
        self.windowLabel.setText(_translate("MainWindow", "Window Size"))
        self.windowSpin.setSuffix(_translate("MainWindow", " days"))
        self.lambdaLabel.setText(_translate("MainWindow", "Lambda"))
        self.replicationsLabel.setText(_translate("MainWindow", "Replications"))
        self.blockSizeLabel.setText(_translate("MainWindow", "Block Size"))
        self.knnResetInput.setText(_translate("MainWindow", "Reset"))
        self.knnOutputPathLabel.setText(_translate("MainWindow", "Output File"))
        self.knnOutputBrowse.setText(_translate("MainWindow", "Browse..."))
        self.knnRun.setText(_translate("MainWindow", "Run"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), _translate("MainWindow", "KNN Weather Generator"))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
