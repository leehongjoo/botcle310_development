# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 14:18:38 2020

@author: hong joo LEE
"""
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

        self.translateUi(self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        QtCore.QMetaObject.connectSlotsByName(self)

    def translateUi(self, dialog):
        _translate = QtCore.QCoreApplication.translate
        dialog.setWindowTitle(_translate("dialog", "Confirm Exit"))
        self.label.setText(_translate("dialog", "모두 초기화 됩니다"))
        self.label_2.setText(_translate("dialog", "종료하시겠습니까?"))