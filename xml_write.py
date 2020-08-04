# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import os

def indent(elem, level=0):
    i = "\n" + level * " "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def makeXML(userIndex, ch1, ch2):
    node = ET.Element("data")
    str_id = str(userIndex)
    str_ch1 = str(ch1)
    str_ch2 = str(ch2)
    node.attrib["ID"] = str_id
    ET.SubElement(node, "Fp1").text = str_ch1
    ET.SubElement(node, "Fp2").text = str_ch2
    return node

'''
user = ET.Element("leehong")
data = makeXML(1, "3.414", "4.3204")
user.append(data)
data = makeXML(2, "4.4324", "34.234")
user.append(data)
indent(user)
ET.ElementTree(user).write("887.xml")
'''
