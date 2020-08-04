# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 14:18:38 2020

@author: hong joo LEE
"""

from PySide2.QtWidgets import (QMainWindow, QAction, QApplication, QSplashScreen,
                               QProgressBar, QLabel, QMessageBox, QWidget, QVBoxLayout, QScrollArea)
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtCore import QSettings, Qt, QRect
import os
import PySide2
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from scipy import fftpack
from scipy.integrate import simps
import startdialog
import quamash
import asyncio
import numpy as np
from collections import deque
import enum
import two_com as tc
import lowpass_filter as lf
import notch_filter as nf
import matplotlib.pyplot as plt
# from PySide2.QtGui import QPixmap
from time import time
from bleak import BleakScanner
from bleak import BleakClient
import sys

dirName = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirName, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        # const value
        self.dequeMax = 1000
        self.fftMax = 1000
        self.notchCutOff = 60
        self.notchQualityFactor = 15
        self.lowPassCutOff = 50
        self.lowPassOrder = 8
        self.BL = 1000
        self.frequencyRange = 50
        self.samplingRate = 500
        self.two_16 = pow(2, 16)
        self.two_8 = pow(2, 8)
        self.max_uv = 407
        self.two_resolution = 8388607
        self.rawGraphFrame = 25
        self.update_num = 20
        self.timerCounter = 0
        self.fftHeight = 10
        self.windowed = np.hamming(self.fftMax)

        # value
        self.measure_time = 0
        self.ch1_1_value = 0
        self.ch1_2_value = 0
        self.ch1_3_value = 0
        self.ch2_1_value = 0
        self.ch2_2_value = 0
        self.ch2_3_value = 0
        self.read_state = parsingState.header1
        self.ptr = 0
        self.ptrFilter = 0
        self.ptrTime = 0
        # UI
        self.pgWidget = QWidget()
        self.setCentralWidget(self.pgWidget)
        self.vBoxLayout = QVBoxLayout(self.pgWidget)

        self.vScrollArea = QScrollArea(self.pgWidget)
        self.vScrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 500, 500))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.vBoxLayout2 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.setWindowTitle('NeuroSpec Demo')
        self.setWindowIcon(QIcon("./images/neuro.png"))
        self.setGeometry(QRect(0, 0, 1000, 1000))
        self.vScrollArea.setWidget(self.scrollAreaWidgetContents)
        self.vBoxLayout.addWidget(self.vScrollArea)

        # grpah
        self.ax = pg.PlotWidget()
        self.ax.setMaximumHeight(300)
        self.ax.setMinimumHeight(250)

        self.ax.setDownsampling(mode='peak')
        self.ax.setClipToView(True)
        self.ax.setTitle("Left Raw Data", color='r')
        self.ax.setLabel('left', '[uV]', color='red', size=30)
        self.ax.setRange(xRange=[-10, 0], yRange=[-50, 50])

        self.ax2 = pg.PlotWidget()
        self.ax2.setMaximumHeight(300)
        self.ax2.setMinimumHeight(250)
        self.ax2.setDownsampling(mode='peak')
        self.ax2.setClipToView(True)
        self.ax2.setTitle("Right Raw Data")
        self.ax2.setLabel('left', '[uV]', color='red', size=30)
        self.ax2.setRange(xRange=[-10, 0], yRange=[-50, 50])

        self.ax3 = pg.PlotWidget()
        self.ax3.setMaximumHeight(300)
        self.ax3.setMinimumHeight(250)
        self.ax3.setDownsampling(mode='peak')
        self.ax3.setClipToView(True)
        self.ax3.setLabel('left', "<span style=\"color:red;font-size:10px\">uV</span>")
        self.ax3.setTitle("Left Filtering Data", color='r')
        self.ax3.setRange(xRange=[-10, 0], yRange=[-50, 50])

        self.ax4 = pg.PlotWidget()
        self.ax4.setMaximumHeight(300)
        self.ax4.setMinimumHeight(250)
        self.ax4.setDownsampling(mode='peak')
        self.ax4.setTitle("Right Filtering Data")
        self.ax4.setClipToView(True)
        self.ax4.setRange(xRange=[-10, 0], yRange=[-50, 50])
        self.ax4.setLabel('left', '[uV]', color='red', size=30)
        self.ax4.setLabel('bottom', 'Time', color='red', size=30)
        self.vBoxLayout2.addWidget(self.ax)
        self.vBoxLayout2.addWidget(self.ax2)
        self.vBoxLayout2.addWidget(self.ax3)
        self.vBoxLayout2.addWidget(self.ax4)
        self.pen = pg.mkPen(color=(255, 0, 0))
        self.line = self.ax.plot(pen=self.pen)
        self.line2 = self.ax2.plot()
        self.line3 = self.ax3.plot(pen=self.pen)
        self.line4 = self.ax4.plot()
        self.data = np.zeros(500)
        self.data_x = np.linspace(0, 499, 500) * 0.002
        self.data2 = np.zeros(500)
        self.data2_x = np.linspace(0, 499, 500) * 0.002
        self.data3 = np.zeros(500)
        self.data3_x = np.linspace(0, 499, 500) * 0.002
        self.data4 = np.zeros(500)
        self.data4_x = np.linspace(0, 499, 500) * 0.002

        # 3d
        fft_freq = fftpack.fftfreq(self.BL, 1 / self.samplingRate)
        pos_mask = np.where(fft_freq > 0)
        self.frequencies = fft_freq[pos_mask]
        self.frequencies = np.delete(self.frequencies, range(self.frequencyRange * 2, 499), axis=0)
        #self.idx_band = dict()
        #for band in eeg_bands:
        #    self.idx_band[band] = np.logical_and(self.frequencies >= eeg_bands[band][0],
        #                                         self.frequencies <= eeg_bands[band][1])
        self.figure3d = gl.GLViewWidget()
        self.figure3d.show()
        self.figure3d.setMaximumHeight(300)
        self.figure3d.setMinimumHeight(250)
        self.figure3d.setCameraPosition(distance=80, azimuth=12, elevation=15)
        self.gz = gl.GLGridItem()
        self.gz.rotate(90, 0, 1, 0)
        self.gz.setSize(10, 10, 1)
        self.gz.translate(0, 5, 5)
        self.figure3d.addItem(self.gz)
        self.gx = gl.GLGridItem()
        self.gx.setSize(50, 10, 1)
        self.gx.translate(25, 5, 0)
        self.figure3d.addItem(self.gx)
        self.vBoxLayout2.addWidget(self.figure3d)
        self.cMap = plt.get_cmap('jet')

        self.freq_ix = dict()
        self.freqBand = dict()
        self.ampBand = dict()
        self.Time = dict()
        self.Fre = dict()
        self.CvMax = dict()
        self.surfPlot = dict()

        for band in eeg_bands:
            self.freq_ix[band] = np.where((self.frequencies >= eeg_bands[band][0]) & (self.frequencies <= eeg_bands[band][1]))[0]
            self.freqBand[band] = self.frequencies[self.freq_ix[band]]
            self.ampBand[band] = np.zeros((len(self.freq_ix[band]), 10))
            self.Time[band] = np.linspace(0, 9, 10)
            self.Fre[band] = self.freqBand[band]
            self.cMap = plt.get_cmap(cMapList[band])
            self.CvMax[band] = self.cMap(self.ampBand[band] / self.fftHeight)
            self.surfPlot[band] = gl.GLSurfacePlotItem(x=self.Fre[band], y=self.Time[band], z=self.ampBand[band],
                                                       colors=self.CvMax[band], smooth=True, glOptions='opaque')
            self.figure3d.addItem(self.surfPlot[band])
        self.surfPlot['Theta'].translate(-0.5, 0, 0)
        self.surfPlot['Alpha'].translate(-1, 0, 0)
        self.surfPlot['Beta'].translate(-1.5, 0, 0)
        self.surfPlot['Gamma'].translate(-2, 0, 0)

        # database
        self.fData = deque(np.zeros(self.dequeMax), maxlen=self.dequeMax)
        self.fData2 = deque(np.zeros(self.dequeMax), maxlen=self.dequeMax)
        self.fData3 = deque(np.zeros(self.fftMax), maxlen=self.fftMax)
        self.buffer = []
        self.ch1_int_buffer = []
        self.ch2_int_buffer = []

        # bluetooth
        self.scanner = BleakScanner()
        self.macAddress = " "
        self.Read_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
        self.Read_UUID2 = "0000fff2-0000-1000-8000-00805f9b34fb"
        self.client = None
        # "74:F0:7D:C0:52:0C"
        self.panaxAddress = "PAPA"
        self.find_device = False
        self.noexcept = False
        self.conBool = False
        self.autoScan()
        # event
        # create actions, file menu action
        self.save = QAction("&저장", self)
        self.save.setIcon(QIcon("./images/saving.png"))
        self.save.setShortcut("Ctrl+S")
        self.save.setStatusTip("Save txt file")
        self.save.triggered.connect(self.close)

        self.load = QAction("L&oad", self)
        self.load.setIcon(QIcon("./images/loading.png"))
        self.load.setShortcut("Ctrl+O")
        self.load.setStatusTip("Load txt file")
        self.load.triggered.connect(self.close)

        self.exitAction = QAction("E&xit", self)
        self.exitAction.setIcon(QIcon("./images/Quit.png"))
        self.exitAction.setShortcut("Ctrl+Q")
        self.exitAction.setStatusTip("Exit the application")
        self.exitAction.triggered.connect(self.close)

        # control menu action
        self.start = QAction("S&tart", self)
        self.start.setIcon(QIcon("./images/start_red.png"))
        self.start.setStatusTip("측정을 시작합니다")
        self.start.triggered.connect(self.startDialog)

        self.paused = QAction("P&ause", self)
        self.paused.setIcon(QIcon("./images/pause.png"))
        self.paused.setStatusTip("측정을 정지합니다")
        self.paused.triggered.connect(self.stopMeasure)

        self.openClose = QAction("O&penclose", self)
        self.openClose.setIcon(QIcon("./images/openclose.png"))
        self.openClose.setStatusTip("개안폐안개안 40초씩 측정합니다")
        self.openClose.triggered.connect(self.measureClear)

        self.stop = QAction("&Stop", self)
        self.stop.setIcon(QIcon("./images/all_stop.png"))
        self.stop.setStatusTip("측정을 멈춤니다")
        self.stop.triggered.connect(self.plotInit)

        # view menu action
        self.surface = QAction("&Surface", self)
        self.surface.setIcon(QIcon("./images/surface.png"))
        self.surface.setStatusTip("입체로 보기-전압에 따른 색상")

        self.band = QAction("&Band", self)
        self.band.setIcon(QIcon("./images/band.png"))
        self.band.setStatusTip("입체로 보기-대역에 따른 색상")

        self.bar = QAction("&Bar", self)
        self.bar.setIcon(QIcon("./images/bar.png"))
        self.bar.setStatusTip("막대 그래프 보기")

        self.pie = QAction("&Pie", self)
        self.pie.setIcon(QIcon("./images/pie.png"))
        self.pie.setStatusTip("파이 그래프 보기")

        self.lineplot = QAction("&Line", self)
        self.lineplot.setIcon(QIcon("./images/lineplot.png"))
        self.lineplot.setStatusTip("입체로 보기-전압에 따른 색상")

        # configuration menu action
        self.rawDataConfig = QAction("&Rawconfig", self)
        self.rawDataConfig.setIcon(QIcon("./images/config2.png"))
        self.rawDataConfig.setStatusTip("Raw Graph 설정")

        self.tdConfig = QAction("&3Dconfig", self)
        self.tdConfig.setIcon(QIcon("./images/config2.png"))
        self.tdConfig.setStatusTip("3D graph 설정")

        # about
        self.aboutAction = QAction("&About", self)
        self.aboutAction.setStatusTip("Show the application's About box")
        self.aboutAction.triggered.connect(self.about)

        # createMenus
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(self.save)
        fileMenu.addAction(self.load)
        fileMenu.addAction(self.exitAction)
        ControlMenu = self.menuBar().addMenu("&Control")
        ControlMenu.addAction(self.start)
        ControlMenu.addAction(self.paused)
        ControlMenu.addAction(self.openClose)
        ControlMenu.addAction(self.stop)
        viewMenu = self.menuBar().addMenu("&View")
        viewMenu.addAction(self.surface)
        viewMenu.addAction(self.band)
        viewMenu.addAction(self.bar)
        viewMenu.addAction(self.pie)
        viewMenu.addAction(self.lineplot)
        configMenu = self.menuBar().addMenu("&Config")
        configMenu.addAction(self.rawDataConfig)
        configMenu.addAction(self.tdConfig)
        helpMenu = self.menuBar().addMenu("&Help")
        helpMenu.addAction(self.aboutAction)

        # createToolBar
        pgToolBar = self.addToolBar("&PG")
        pgToolBar.setObjectName("PGToolBar")
        pgToolBar.addAction(self.load)
        pgToolBar.addAction(self.save)
        pgToolBar.addSeparator()
        pgToolBar.addAction(self.start)
        pgToolBar.addAction(self.paused)
        pgToolBar.addAction(self.openClose)
        pgToolBar.addAction(self.stop)
        # spacer
        pgToolBar.addSeparator()
        pgToolBar.addAction(self.surface)
        pgToolBar.addAction(self.band)
        # spacer
        pgToolBar.addSeparator()
        pgToolBar.addAction(self.bar)
        pgToolBar.addAction(self.pie)
        pgToolBar.addAction(self.lineplot)
        # spacer
        pgToolBar.addSeparator()
        pgToolBar.addAction(self.rawDataConfig)
        pgToolBar.addAction(self.tdConfig)
        # spacer
        pgToolBar.addSeparator()
        pgToolBar.addAction(self.aboutAction)

        # createStatusBar
        locationLabel = QLabel("status bar")
        locationLabel.setAlignment(Qt.AlignHCenter)
        locationLabel.setMinimumSize(locationLabel.sizeHint())

        self.statusBar().addWidget(locationLabel)

    def readSettings(self):
        settings = QSettings("Panaxtos", "newneuroSpec_Demo")  # modify

        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("state"))

    def writeSettings(self):
        settings = QSettings("Qt5Programming Inc.", "Shape")
        self.saveGeometry()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())

    def autoScan(self):
        asyncio.ensure_future(self.scan_start(), loop=loop)
        print('btnCallback returns...')

    def detection_callback(*args):
        print(args)

    async def scan_start(self):
        self.scanner.register_detection_callback(self.detection_callback)
        run_time = 0
        start_time = time()
        while run_time < 16:
            await self.scanner.start()
            await asyncio.sleep(5.0)
            await self.scanner.stop()
            devices = await self.scanner.get_discovered_devices()
            if not devices:
                print("bluetooth를 켜주세요")
            for d in devices:
                if d.name == self.panaxAddress:
                    self.find_device = True
                    self.macAddress = d.address
                    break
            if self.find_device:
                print("find panaxtos")
                await self.connect_panax(self.macAddress, loop)
                break
            end_time = time()
            run_time = end_time - start_time

    async def connect_panax(self, address, loop):
        self.client = BleakClient(address, loop=loop)
        while not self.noexcept:
            try:
                await self.client.connect()
                await self.isConnected()
                print(self.conBool)
                self.noexcept = True
            except Exception as e:
                print(e)

    async def isConnected(self):
        self.conBool = await self.client.is_connected()

    async def disconnect_panax(self):
        await self.client.disconnect()

    async def start_panax(self):
        if self.conBool:
            await self.client.start_notify(self.Read_UUID, self.tx_data_received)
            await self.client.start_notify(self.Read_UUID2, self.tx_data_received2)

    def measureStart(self):
        asyncio.ensure_future(self.isConnected())
        asyncio.ensure_future(self.start_panax(), loop=loop)

    # event
    def close_event(self, event):
        self.writeSettings()

    def startDialog(self):
        sd = startdialog.Ui_dialog(self)
        if sd.exec():
            self.measure_time = sd.time_info()
            self.measureStart()

    def measureClear(self):
        self.pgWidget.plotClear()

    def stopMeasure(self):
        asyncio.ensure_future(self.disconnect_panax())

    def plotInit(self):
        self.pgWidget.plotInit()

    def about(self):
        QMessageBox.about(self, "About Shape",
                          "<h2>newNeuroSpec Demo 1.0</h2>"
                          "<p>Copyright &copy; 2020 Panaxtos Inc."
                          "<p>Shape is a small application that "
                          "demonstrates QAction, QMainWindow, QMenuBar, "
                          "QStatusBar, QToolBar, and many other "
                          "데모데모")

    # data_received -> parsing -> int -> 20 -> print
    def tx_data_received2(self, sender, data):
        print("tx2!!!!")

    def tx_data_received(self, sender, data):
        #print("RX!!!> {}".format(data))
        data_len = len(data)
        b = []
        c = []
        for rep in range(data_len):
            self.buffer.append(data[rep])
            b.append(data[rep])
        for rep in range(len(b)):
            if b[rep] == 255:
                c.append('0xFF')
            elif b[rep] == 119:
                c.append('0x77')
            else:
                c.append(data[rep])
        print(c)
        self.read_data()
        # state2
        if len(self.ch1_int_buffer) >= self.update_num and len(self.ch2_int_buffer) >= self.update_num:
            self.print_graph()
            self.timerCounter += 1

        if self.timerCounter >= self.rawGraphFrame:
            self.timerCounter -= self.rawGraphFrame
            self.print3DGraph()

    def read_data(self):
        while len(self.buffer) > 0:
            temp = self.buffer.pop(0)
            if self.read_state == parsingState.header1:
                if temp == 255:
                    self.read_state = parsingState.header2
            elif self.read_state == parsingState.header2:
                if temp == 119:
                    self.read_state = parsingState.header3
            elif self.read_state == parsingState.header3:
                if temp == 255:
                    self.read_state = parsingState.ch1_1
            elif self.read_state == parsingState.ch1_1:
                self.ch1_1_value = temp
                self.read_state = parsingState.ch1_2
            elif self.read_state == parsingState.ch1_2:
                self.ch1_2_value = temp
                self.read_state = parsingState.ch1_3
            elif self.read_state == parsingState.ch1_3:
                self.ch1_3_value = temp
                self.read_state = parsingState.ch2_1
            elif self.read_state == parsingState.ch2_1:
                self.ch2_1_value = temp
                self.read_state = parsingState.ch2_2
            elif self.read_state == parsingState.ch2_2:
                self.ch2_2_value = temp
                self.read_state = parsingState.ch2_3
            elif self.read_state == parsingState.ch2_3:
                self.ch2_3_value = temp
                ch1_int = (self.ch1_1_value * self.two_16) + (self.ch1_2_value * self.two_8) + self.ch1_3_value
                ch1_int = tc.twos_comp(ch1_int, 24)
                ch1_int = (ch1_int * self.max_uv) / self.two_resolution
                self.ch1_int_buffer.append(ch1_int)
                ch2_int = (self.ch2_1_value * self.two_16) + (self.ch2_2_value * self.two_8) + self.ch2_3_value
                ch2_int = tc.twos_comp(ch2_int, 24)
                ch2_int = (ch2_int * self.max_uv) / self.two_resolution
                self.ch2_int_buffer.append(ch2_int)
                self.read_state = parsingState.header1

    def print_graph(self):
        ch1 = []
        ch2 = []
        for rep in range(0, self.update_num):
            temp = self.ch1_int_buffer.pop(0)
            temp2 = self.ch2_int_buffer.pop(0)
            ch1.append(temp)
            ch2.append(temp2)
        self.fData.extend(ch1)
        self.fData2.extend(ch2)
        self.data[self.ptr: self.ptr + self.update_num] = ch1
        self.data2[self.ptr: self.ptr + self.update_num] = ch2
        self.ptr += self.update_num
        if self.ptr >= self.data.shape[0]:
            tmp = self.data
            tmp2 = self.data2
            self.data = np.zeros(self.data.shape[0] * 2)
            self.data2 = np.zeros(self.data2.shape[0] * 2)
            self.data[:tmp.shape[0]] = tmp
            self.data2[:tmp2.shape[0]] = tmp2
            self.data_x = np.linspace(0, self.data.shape[0] - 1, self.data.shape[0]) * 0.002
            self.data2_x = np.linspace(0, self.data.shape[0] - 1, self.data.shape[0]) * 0.002
        self.line.setData(x=self.data_x[:self.ptr], y=self.data[:self.ptr])
        self.line.setPos(-self.ptr * 0.002, 0)
        self.line2.setData(x=self.data2_x[:self.ptr], y=self.data2[:self.ptr])
        self.line2.setPos(-self.ptr * 0.002, 0)

        notch_ch1 = nf.notch_filter(self.fData, self.notchCutOff, self.samplingRate, self.notchQualityFactor)
        notch_ch2 = nf.notch_filter(self.fData2, self.notchCutOff, self.samplingRate, self.notchQualityFactor)
        notch_ch1 = nf.notch_filter(notch_ch1, self.notchCutOff, self.samplingRate, self.notchQualityFactor)
        notch_ch2 = nf.notch_filter(notch_ch2, self.notchCutOff, self.samplingRate, self.notchQualityFactor)
        notchLowPass_ch1 = lf.butter_lowpass_filter(notch_ch1, self.lowPassCutOff, self.samplingRate, self.lowPassOrder)
        notchLowPass_ch2 = lf.butter_lowpass_filter(notch_ch2, self.lowPassCutOff, self.samplingRate, self.lowPassOrder)
        filtering_ch1 = lf.butter_lowpass_filter(notchLowPass_ch1, self.lowPassCutOff, self.samplingRate,
                                                 self.lowPassOrder)
        filtering_ch2 = lf.butter_lowpass_filter(notchLowPass_ch2, self.lowPassCutOff, self.samplingRate,
                                                 self.lowPassOrder)
        self.fData3.extend(filtering_ch1[-self.update_num:])
        self.data3[self.ptrFilter: self.ptrFilter + self.update_num] = filtering_ch1[-self.update_num:]
        self.data4[self.ptrFilter: self.ptrFilter + self.update_num] = filtering_ch2[-self.update_num:]
        self.ptrFilter += self.update_num
        if self.ptrFilter >= self.data3.shape[0]:
            tmp = self.data3
            tmp2 = self.data4
            self.data3 = np.zeros(self.data3.shape[0] * 2)
            self.data4 = np.zeros(self.data3.shape[0] * 2)
            self.data3[:tmp.shape[0]] = tmp
            self.data4[:tmp2.shape[0]] = tmp2
            self.data3_x = np.linspace(0, self.data3.shape[0] - 1, self.data3.shape[0]) * 0.002
            self.data4_x = np.linspace(0, self.data3.shape[0] - 1, self.data3.shape[0]) * 0.002
        self.line3.setData(x=self.data3_x[:self.ptrFilter], y=self.data3[:self.ptrFilter])
        self.line3.setPos(-self.ptrFilter * 0.002, 0)
        self.line4.setData(x=self.data4_x[:self.ptrFilter], y=self.data4[:self.ptrFilter])
        self.line4.setPos(-self.ptrFilter * 0.002, 0)

    def print3DGraph(self):
        ch1_raw_data = self.fData3
        ch1_raw_data = ch1_raw_data * self.windowed
        ch1_fft = np.absolute(np.fft.rfft(ch1_raw_data))
        ch1_fft = np.delete(ch1_fft, 0, axis=0)
        ch1_fft = np.delete(ch1_fft, range(self.frequencyRange * 2, int(self.fftMax / 2)), axis=0)
        '''
        bar graph .  band power band_power_array = np.zeros(5)
        band_power_array[0] = simps(ch1_fft_vals[idx_band['Delta']], dx = 0.5)
        band_power_array[1] = simps(ch1_fft_vals[idx_band['Theta']], dx = 0.5)
        band_power_array[2] = simps(ch1_fft_vals[idx_band['Alpha']], dx = 0.5)
        band_power_array[3] = simps(ch1_fft_vals[idx_band['Beta']], dx = 0.5)
        band_power_array[4] = simps(ch1_fft_vals[idx_band['Gamma']], dx = 0.5)
        '''
        ch1_fft = np.log(ch1_fft)
        for band in eeg_bands:
            self.ampBand[band][:, self.ptrTime] = ch1_fft[self.freq_ix[band][0] : self.freq_ix[band][-1] + 1]
            if self.ptrTime >= self.ampBand[band].shape[1] - 1:
                tmp = self.ampBand[band]
                self.ampBand[band] = np.zeros((len(self.freq_ix[band]), self.ampBand[band].shape[1] + 10))
                self.ampBand[band][:, :tmp.shape[1]] = tmp
                self.Time[band] = np.linspace(0, tmp.shape[1] + 9, tmp.shape[1] + 10)
                if band == 'Delta':
                    self.gx.setSize(50, 10+self.ptrTime, 1)
                    self.gx.translate(0, 1, 0)
                    self.gz.setSize(10, 10+self.ptrTime, 1)
                    self.gz.translate(0, 1, 0)
                self.surfPlot[band].translate(0, -4, 0)
            self.cMap = plt.get_cmap('jet')
            self.CvMax[band] = self.cMap(self.ampBand[band] / self.fftHeight)
            self.surfPlot[band].setData(y=self.Time[band], z=self.ampBand[band], colors=self.CvMax[band])
        self.ptrTime += 1


class parsingState(enum.Enum):
    header1 = 0
    header2 = 1
    header3 = 2
    ch1_1 = 3
    ch1_2 = 4
    ch1_3 = 5
    ch2_1 = 6
    ch2_2 = 7
    ch2_3 = 8
    end = 9


eeg_bands = {'Delta': (0.5, 3.5),
             'Theta': (4, 7.5),
             'Alpha': (8, 12.5),
             'Beta': (13, 30),
             'Gamma': (30.5, 100)
             }

cMapList = {'Delta': plt.cm.Reds,
            'Theta': plt.cm.Oranges,
            'Alpha': plt.cm.Wistia,
            'Beta': plt.cm.BuGn,
            'Gamma': plt.cm.YlGnBu
            }

if __name__ == '__main__':
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(loop)
    splash_pix = QPixmap('./images/splash.png')
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.setEnabled(False)
    # splash = QSplashScreen(splash_pix)
    # adding progress bar
    progressBar = QProgressBar(splash)
    progressBar.setMaximum(10)
    progressBar.setGeometry(0, splash_pix.height() - 50, splash_pix.width(), 20)
    # splash.setMask(splash_pix.mask())

    splash.show()
    splash.showMessage("<h1><font color='black' size= 10>New Neuro Spec !</font></h1>", Qt.AlignTop | Qt.AlignCenter,
                       Qt.black)

    for i in range(1, 11):
        progressBar.setValue(i)
        t = time()
        while time() < t + 0.1:
            app.processEvents()

    # Simulate something that takes time
    with loop:
        window33 = MainWindow()
        window33.show()
        splash.finish(window33)
        sys.exit(app.exec_())
        loop.run_forever()
    print('ended')
