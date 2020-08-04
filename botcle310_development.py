# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 14:18:38 2020

@author: hong joo LEE
"""

from PySide2.QtWidgets import (QMainWindow, QAction, QApplication, QSplashScreen, QDockWidget, QListWidget,
                               QProgressBar, QLabel, QMessageBox, QWidget, QVBoxLayout, QFileDialog)
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtCore import QSettings, Qt, QRect
import os
import PySide2
import pyqtgraph as pg
# import pyqtgraph.opengl as gl
# from scipy import fftpack
# from scipy.integrate import simps
import startdialog
import stopdialog
import quamash
import asyncio
import numpy as np
from collections import deque
import enum
import two_com as tc
import lowpass_filter as lf
import notch_filter as nf
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import xml_write
import datetime
# from PySide2.QtGui import QPixmap
from time import time
from bleak import BleakScanner
from bleak import BleakClient
import sys

sys.setrecursionlimit(5000)

dirName = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirName, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        # super().__init__()
        QMainWindow.__init__(self, parent)
        # const value
        self.dequeMax = 1000
        self.notchCutOff = 60
        self.notchQualityFactor = 15
        self.lowPassCutOff = 50
        self.lowPassOrder = 8
        self.samplingRate = 500
        self.two_16 = pow(2, 16)
        self.two_8 = pow(2, 8)
        self.max_uv = 407
        self.two_resolution = 8388607
        self.rawGraphFrame = 25
        self.update_num = 20
        self.timerCounter = 0

        # value
        self.measure_time = 0
        self.timerCount = 0
        self.printIndex = 0
        self.headerCount = 0
        self.ch1_1_value = 0
        self.ch1_2_value = 0
        self.ch1_3_value = 0
        self.ch2_1_value = 0
        self.ch2_2_value = 0
        self.ch2_3_value = 0
        self.dataIndex = 0
        self.read_state = parsingState.header1
        self.ptr = 0
        self.ptrFilter = 0
        self.ptrTime = 0
        self.boolPaused = True

        # UI
        self.pgWidget = QWidget()
        self.setCentralWidget(self.pgWidget)
        self.setGeometry(QRect(250, 120, 1600, 820))

        self.dockingWidget = QDockWidget("개발용 텍스트")
        self.listWidget = QListWidget()
        self.listWidget.setFont("Courier")
        self.dockingWidget.setWidget(self.listWidget)
        self.dockingWidget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.dockingWidget.setFloating(False)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dockingWidget)

        self.vBoxLayout2 = QVBoxLayout(self.pgWidget)
        self.lLabel = QLabel("블루투스 자동연결을 실행합니다.")
        self.lLabel.resize(200, 45)
        self.lLabel.setMaximumHeight(45)
        self.lLabel.setMinimumHeight(30)
        self.lLabel.setStyleSheet("color: blue;"
                                  "border-style: solid;"
                                  "border-width: 1px;"
                                  "border-color: #c1f7fe;"
                                  "border-radius: 3px;"
                                  "background-color: #F7FFFE;")
        font1 = self.lLabel.font()
        font1.setPointSize(30)
        font1.setFamily('Times New Roman')
        font1.setBold(True)
        self.lLabel.setFont(font1)

        self.setWindowTitle('Brint Monitor')
        self.setWindowIcon(QIcon("./images/brainGreen.png"))

        # grpah
        self.ax3 = pg.PlotWidget()
        self.ax3.setMaximumHeight(340)
        self.ax3.setMinimumHeight(250)
        self.ax3.setDownsampling(mode='peak')
        self.ax3.setTitle("좌측 뇌파", color='w')
        self.ax3.setClipToView(True)
        self.ax3.setLabel('left', "뇌파 [uV]", color='white')
        self.ax3.setLabel('bottom', '시간 [초]', color='white')
        self.ax3.setRange(xRange=[-10, 0], yRange=[-150, 150])

        self.ax4 = pg.PlotWidget()
        self.ax4.setMaximumHeight(340)
        self.ax4.setMinimumHeight(250)
        self.ax4.setDownsampling(mode='peak')
        self.ax4.setTitle("우측 뇌파", color='w')
        self.ax4.setClipToView(True)
        self.ax4.setRange(xRange=[-10, 0], yRange=[-150, 150])
        self.ax4.setLabel('left', '뇌파 [uV]', color='white')
        self.ax4.setLabel('bottom', '시간 [초]', color='white', size=30)
        self.vBoxLayout2.addWidget(self.ax3)
        self.vBoxLayout2.addWidget(self.ax4)
        self.pen = pg.mkPen(color=(255, 0, 0))
        self.line3 = self.ax3.plot(pen=self.pen)
        self.line4 = self.ax4.plot()
        self.data3 = np.zeros(500)
        self.data3_x = np.linspace(0, 499, 500) * 0.002
        self.data4 = np.zeros(500)
        self.data4_x = np.linspace(0, 499, 500) * 0.002
        self.vBoxLayout2.addWidget(self.lLabel)
        # database
        self.fData = deque(np.zeros(self.dequeMax), maxlen=self.dequeMax)
        self.fData2 = deque(np.zeros(self.dequeMax), maxlen=self.dequeMax)
        self.buffer = []
        self.ch1_int_buffer = []
        self.ch2_int_buffer = []

        # xml
        self.user = ET.Element("userName")

        # bluetooth
        self.scanner = BleakScanner()
        self.macAddress = " "
        self.Read_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
        self.Rx_UUID = "a9da6040-0823-4995-94ec-9ce41ca28833"
        self.Tx_UUID = "a73e9a10-628f-4494-a099-12efaf72258f"
        self.client = None
        # "74:F0:7D:C0:52:0C"
        self.panaxAddress = "PAPA"  # "BGX-76DE"
        self.find_device = False
        self.noexcept = False
        self.conBool = False
        self.autoScan()
        # event
        # create actions, file menu action
        self.save = QAction("&Save", self)
        self.save.setIcon(QIcon("./images/saveBlue.png"))
        self.save.setShortcut("Ctrl+S")
        self.save.setStatusTip("Save .xml file")
        self.save.triggered.connect(self.save_rx)

        self.exitAction = QAction("E&xit", self)
        self.exitAction.setIcon(QIcon("./images/Quit.png"))
        self.exitAction.setShortcut("Ctrl+Q")
        self.exitAction.setStatusTip("Exit the application")
        self.exitAction.triggered.connect(self.close)

        # control menu action
        self.start = QAction("S&tart", self)
        self.start.setIcon(QIcon("./images/recordRed.png"))
        self.start.setStatusTip("측정을 시작합니다")
        self.start.triggered.connect(self.startDialog)

        self.paused = QAction("P&ause", self)
        self.paused.setIcon(QIcon("./images/pauseBlue.png"))
        self.paused.setStatusTip("측정을 정지합니다")
        self.paused.triggered.connect(self.pausedMeasure)

        self.stop = QAction("&Stop", self)
        self.stop.setIcon(QIcon("./images/stopBlue.png"))
        self.stop.setStatusTip("측정을 멈춤니다")
        self.stop.triggered.connect(self.rx_stop)

        # view menu action

        # about
        self.aboutAction = QAction("&About", self)
        self.aboutAction.setStatusTip("Show the application's About box")
        self.aboutAction.triggered.connect(self.about)

        # createMenus
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(self.save)
        # fileMenu.addAction(self.load)
        fileMenu.addAction(self.exitAction)
        ControlMenu = self.menuBar().addMenu("&Control")
        ControlMenu.addAction(self.start)
        ControlMenu.addAction(self.paused)
        ControlMenu.addAction(self.stop)

        helpMenu = self.menuBar().addMenu("&Help")
        helpMenu.addAction(self.aboutAction)

        # createToolBar
        pgToolBar = self.addToolBar("&PG")
        pgToolBar.setObjectName("PGToolBar")
        pgToolBar.addAction(self.save)
        pgToolBar.addSeparator()

        pgToolBar.addAction(self.start)
        pgToolBar.addAction(self.paused)
        pgToolBar.addAction(self.stop)

        pgToolBar.addSeparator()
        pgToolBar.addAction(self.aboutAction)

        pgToolBar2 = self.addToolBar("PG2")
        pgToolBar2.setObjectName("PGToolBar2")

        # createStatusBar
        '''
        lLabel = QLabel("status bar")
        #lLabel.setAlignment(Qt.AlignHCenter)
        #lLabel.setMinimumSize(lLabel.sizeHint())
        self.locationLabel = QLabel("test")
        self.locationLabel.setMinimumWidth(100)
        self.statusBar().setMinimumHeight(50)
        self.statusBar().addWidget(lLabel)
        self.statusBar().addWidget(self.locationLabel)
        '''

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
        self.lLabel.setText("PANAXTOS 기기를 Scan 중....")
        run_time = 0
        start_time = time()
        while run_time < 16:
            await self.scanner.start()
            await asyncio.sleep(5.0)
            await self.scanner.stop()
            devices = await self.scanner.get_discovered_devices()
            if not devices:
                self.lLabel.setText("bluetooth를 켜주세요")
            for d in devices:
                if d.name == self.panaxAddress:
                    self.find_device = True
                    self.macAddress = d.address
                    break
            if self.find_device:
                print("True")
                self.lLabel.setText("기기를 찾았습니다. connection을 진행합니다.")
                await self.connect_panax(self.macAddress, loop)
                break
            end_time = time()
            run_time = end_time - start_time
        if not self.find_device:
            self.lLabel.setText("기기가 켜져있는지 확인해주시고 프로그램을 다시 시작해주세요")

    async def connect_panax(self, address, loop):
        self.client = BleakClient(address, loop=loop)
        while not self.noexcept:
            try:
                await self.client.connect()
                await self.isConnected()
                self.start.setEnabled(True)
                self.noexcept = True
                self.lLabel.setText("연결이 완료 되었습니다. 측정시작 버튼을 눌러주세요")
            except Exception as e:
                print(e)
                self.lLabel.setText("Connection 중")

    async def isConnected(self):
        self.conBool = await self.client.is_connected()

    async def disconnect_panax(self):
        # await self.client.disconnect()
        await self.client.stop_notify(self.Read_UUID)

    async def start_panax(self):
        if self.conBool:
            await  self.client.start_notify(self.Read_UUID, self.tx_data_received)
            # await self.client.start_notify(self.Rx_UUID, self.rx_data_received)
            # await asyncio.sleep(0.2)
            # await self.client.stop_notify(self.Rx_UUID)
            # await self.client.start_notify(self.Tx_UUID, self.tx_data_received)

    async def start_rx(self):
        if self.conBool:
            await self.client.start_notify(self.Rx_UUID, self.rx_data_received)

    async def stop_rx(self):
        await self.client.stop_notify(self.Read_UUID)

    def measureStart(self):
        asyncio.ensure_future(self.isConnected())
        asyncio.ensure_future(self.start_panax(), loop=loop)
        self.start.setDisabled(True)
        self.save.setEnabled(True)
        self.lLabel.setText("뇌파를 측정중입니다.")

    # event
    def save_xml(self):
        xml_write.indent(self.user)
        now = datetime.datetime.now()
        nowDate = now.strftime('%Y-%m-%d.%H.%M')
        nowXml = nowDate + '.xml'
        ET.ElementTree(self.user).write(nowXml)
        nowXml = "저장이 완료 되었습니다" + nowXml
        self.lLabel.setText(nowXml)

    def save_rx(self):
        asyncio.ensure_future(self.start_rx(), loop=loop)

    def rx_stop(self):
        asyncio.ensure_future(self.stop_rx(), loop=loop)

    def startDialog(self):
        sd = startdialog.Ui_dialog(self)
        if sd.exec():
            self.measure_time = sd.time_info()
            self.measureStart()

    def stopDialog(self):
        sd = stopdialog.Ui_dialog(self)
        if sd.exec():
            self.plotInit()

    def pausedMeasure(self):
        self.boolPaused = not self.boolPaused
        if not self.boolPaused:
            asyncio.ensure_future(self.disconnect_panax())
            self.paused.setIcon(QIcon("./images/playBlue.png"))
            self.paused.setStatusTip("측정을 재개합니다")
            self.lLabel.setText("측정을 정지합니다.")
        else:
            self.measureStart()
            self.paused.setIcon(QIcon("./images/pauseBlue.png"))
            self.paused.setStatusTip("측정을 정지합니다")
            self.lLabel.setText("측정을 재개합니다.")

    def plotInit(self):
        self.lLabel.setText("측정을 초기화 하였습니다. 다시 시작하려면 시작버튼을 누르시오")
        if self.boolPaused:
            self.pausedMeasure()
        self.fData.clear()
        self.fData2.clear()
        self.fData.extend(np.zeros(500))
        self.fData2.extend(np.zeros(500))
        self.ptr = 0
        self.ptrTime = 0
        self.ptrFilter = 0
        self.timerCount = 0
        self.line3.setData(np.empty(1))
        self.line4.setData(np.empty(1))
        self.ax3.setRange(xRange=[-10, 0], yRange=[-150, 150])
        self.ax4.setRange(xRange=[-10, 0], yRange=[-150, 150])
        self.boolPaused = not self.boolPaused
        self.paused.setIcon(QIcon("./images/pauseBlue.png"))
        self.paused.setStatusTip("측정을 정지합니다")
        self.start.setEnabled(True)
        self.paused.setDisabled(True)
        self.stop.setDisabled(True)

    def about(self):
        QMessageBox.about(self, "About Shape",
                          "<h2>Brint Monitor 1.0</h2>"
                          "<p>Copyright &copy; 2020 Panaxtos Inc."
                          "<p>Shape is a small application that "
                          "demonstrates QAction, QMainWindow, QMenuBar, "
                          "QStatusBar, QToolBar, and many other "
                          )

    # data_received -> parsing -> int -> 20 -> print

    def rx_data_received(self, sender, data):
        print("RX {}".format(data))

    def tx_data_received(self, sender, data):
        data_len = len(data)
        for rep in range(data_len):
            self.buffer.append(data[rep])
        self.print_data()
        '''data_len = len(data)
        for rep in range(data_len):
            self.buffer.append(data[rep])
        self.read_data()
        if len(self.ch1_int_buffer) >= self.update_num and len(self.ch2_int_buffer) >= self.update_num:
            self.print_graph()
        '''

    def print_data(self):
        while len(self.buffer) > 0:
            temp = self.buffer.pop(0)
            if self.read_state == parsingState.header1:
                if temp == 255:
                    self.read_state = parsingState.header2
            elif self.read_state == parsingState.header2:
                if temp == 119:
                    self.read_state = parsingState.header3
            elif self.read_state == parsingState.header3:
                self.headerCount = temp
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
                stringFF = hex(255)
                string77 = hex(119)
                hCount = "0x{:02x}".format(self.headerCount)
                ch1_1 = "0x{:02x}".format(self.ch1_1_value)
                ch1_2 = "0x{:02x}".format(self.ch1_2_value)
                ch1_3 = "0x{:02x}".format(self.ch1_3_value)
                ch2_1 = "0x{:02x}".format(self.ch2_1_value)
                ch2_2 = "0x{:02x}".format(self.ch2_2_value)
                ch2_3 = "0x{:02x}".format(self.ch2_3_value)
                ss = stringFF + " " + string77 + " " + hCount + " " + ch1_1 + " " + ch1_2 + " " + ch1_3 + " " + ch2_1 \
                    + " " + ch2_2 + " " + ch2_3
                self.listWidget.addItem(ss)
                self.printIndex += 1
                if self.printIndex > 40:
                    self.listWidget.takeItem(0)
                self.read_state = parsingState.header1

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
                self.dataIndex += 1
                data = xml_write.makeXML(self.dataIndex, ch1_int, ch2_int)
                self.user.append(data)
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
        # self.fData3.extend(filtering_ch1[-self.update_num:])
        # self.fData4.extend(filtering_ch2[-self.update_num:])
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
        self.timerCount += 0.04
        if self.timerCount > self.measure_time:
            self.pausedMeasure()
            self.paused.setDisabled(True)
            self.lLabel.setText("측정이 끝났습니다. 수고하셨습니다.")


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
    app = QApplication(sys.argv)
    if app is None:
        app = QApplication([])
    loop = quamash.QEventLoop(app)
    asyncio.set_event_loop(loop)
    splash_pix = QPixmap('./images/splash.png')
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.setEnabled(False)
    # adding progress bar
    progressBar = QProgressBar(splash)
    progressBar.setMaximum(10)
    progressBar.setGeometry(0, splash_pix.height() - 50, splash_pix.width(), 20)

    splash.show()
    splash.showMessage("<h1><font color='white' size= 10>Brint Monitor !</font></h1>", Qt.AlignTop | Qt.AlignCenter,
                       Qt.black)

    for i in range(1, 11):
        progressBar.setValue(i)
        t = time()
        while time() < t + 0.1:
            app.processEvents()

    with loop:
        window33 = MainWindow()
        window33.show()
        splash.finish(window33)
        sys.exit(app.exec_())
        loop.run_forever()
