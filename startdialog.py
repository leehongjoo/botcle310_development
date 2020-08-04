# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'start_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtWidgets


class Ui_dialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        self.setObjectName("dialog")
        self.resize(326, 160)
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(150, 120, 156, 23))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.label = QtWidgets.QLabel(self)
        self.label.setGeometry(QtCore.QRect(20, 30, 141, 16))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self)
        self.label_2.setGeometry(QtCore.QRect(20, 70, 121, 16))
        self.label_2.setObjectName("label_2")
        self.spinBox = QtWidgets.QSpinBox(self)
        self.spinBox.setGeometry(QtCore.QRect(160, 68, 141, 22))
        self.spinBox.setObjectName("spinBox")
        self.spinBox.setRange(1, 999)
        self.spinBox.setValue(120)
        self.label_2.setBuddy(self.spinBox)

        self.reTranslateUi(self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        QtCore.QMetaObject.connectSlotsByName(self)

    def reTranslateUi(self, dialog):
        _translate = QtCore.QCoreApplication.translate
        dialog.setWindowTitle(_translate("dialog", "측정시간"))
        self.label.setText(_translate("dialog", "측정시간을 설정합니다."))
        self.label_2.setText(_translate("dialog", "측정시간(기본:120초)"))

    def time_info(self):
        start_time = int(self.spinBox.text())
        return start_time
