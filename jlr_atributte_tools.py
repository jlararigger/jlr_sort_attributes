#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymel.core as pm
import maya.mel as mel
from pprint import pprint

# TODO: falta dar soporte a los atributos de tipo string


def copy_attr(item_source, item_target, attr_name, move=False):
    attr_data = get_attr_info(item_source, attr_name)
    if not attr_data:
        return

    new_attr = create_attr(item_target, attr_data)
    if new_attr:

        if move:
            if attr_data['attributeType'] == 'double3':
                pm.warning('Vector-type attributes can not be moved: {}'.format(attr_name))
                pm.warning('Connections to this attribute will be disconnected.')
                pm.disconnectAttr(item_source.attr(attr_name))

                for axis in attr_data['axes'].values():
                    pm.disconnectAttr(item_source.attr(axis['longName']))

            else:
                pm.deleteAttr(item_source, at=attr_name)

        connect_attr(new_attr, attr_data['in'], attr_data['out'])
        if new_attr.type() == 'double3':
            for axis in attr_data['axes'].values():
                sub_attr = item_target.attr(axis['longName'])
                connect_attr(sub_attr, axis['in'], axis['out'])


def create_attr(item, attr_data):
    attr_name = attr_data['longName']
    del attr_data['longName']
    # Check if the attribute exists within the item.
    # If it exists, a number will be added to the end of the name.
    cont_name = 0
    tmp_name = attr_name
    while item.hasAttr(tmp_name):
        cont_name += 1
        tmp_name = attr_name + str(cont_name).zfill(2)

    if cont_name:
        pm.warning('There is already an attribute {} inside {}'.format(attr_name, item))
        attr_name = attr_name + str(cont_name).zfill(2)
        attr_data['niceName'] = attr_data['niceName'] + str(cont_name).zfill(2)
        attr_data['shortName'] = attr_data['shortName'] + str(cont_name).zfill(2)
        pm.warning('An attribute {} will be created inside {}'.format(attr_name, item))

    # Creating the attribute
    pprint(attr_data)
    item.addAttr(attr_name, **attr_data)
    new_attr = item.attr(attr_name)
    return new_attr


def old_create_attr(item, attr_data):
    attr_name = attr_data['longName']

    cont_name = 0
    tmp_name = attr_name
    while item.hasAttr(tmp_name):
        cont_name += 1
        tmp_name = attr_name + str(cont_name).zfill(2)

    if cont_name:
        pm.warning('There is already an attribute {} inside {}'.format(attr_name, item))
        attr_name = attr_name + str(cont_name).zfill(2)
        attr_data['niceName'] = attr_data['niceName'] + str(cont_name).zfill(2)
        attr_data['shortName'] = attr_data['shortName'] + str(cont_name).zfill(2)
        pm.warning('An attribute {} will be created inside {}'.format(attr_name, item))

    if attr_data['attributeType'] in ['long', 'bool', 'double']:
        item.addAttr(attr_name, nn=attr_data['niceName'], sn=attr_data['shortName'],
                     hidden=attr_data['hidden'], keyable=attr_data['keyable'], at=attr_data['attributeType'],
                     dv=attr_data['defaultValue'])

    elif attr_data['attributeType'] == 'enum':
        enum_data = ':'.join(attr_data['enumName'].keys())
        item.addAttr(attr_name, nn=attr_data['niceName'], sn=attr_data['shortName'],
                     hidden=attr_data['hidden'], keyable=attr_data['keyable'], at=attr_data['attributeType'], en=enum_data)

    elif attr_data['attributeType'] == 'double3':
        item.addAttr(attr_name, at=attr_data['attributeType'])
        for axis in 'XYZ':
            axis = attr_data['axes'][axis]
            item.addAttr(axis['longName'], nn=axis['niceName'], sn=attr_data['shortName'],
                         hidden=axis['hidden'], keyable=axis['keyable'], at=axis['attributeType'], dv=axis['defaultValue'],
                         parent=axis['parent'])

    new_attr = item.attr(attr_name)

    if new_attr.type() in ['long', 'bool', 'double']:
        min_value, max_value = attr_data['range']
        if min_value is not None: new_attr.setMin(min_value)
        if max_value is not None: new_attr.setMax(max_value)

    if not new_attr.type() in ['double3']:
        new_attr.set(attr_data['value'])
    else:
        for axis in 'XYZ':
            sub_attr = item.attr(attr_data['axes'][axis]['longName'])
            sub_attr.set(attr_data['axes'][axis]['value'])

    if attr_data['locked']:
        new_attr.lock()
    else:
        new_attr.unlock()

    return new_attr


def connect_attr(attr, attr_inputs=None, attr_outputs=None):

    if attr_inputs:
        for attr_input in attr_inputs:
            if attr.inputs():
                make_shared_connection(attr_input, attr)
            else:
                attr_input.connect(attr)

    if attr_outputs:
        if attr.type() in ['long', 'bool', 'double', 'enum', 'double3']:
            # print attr, attr_inputs, attr_outputs
            for attr_output in attr_outputs:
                if attr_output.inputs(p=1):
                    make_shared_connection(attr, attr_output)
                else:
                    attr.connect(attr_output)


def make_shared_connection(attr_source, target_attr):
    attr_previous_connected = target_attr.inputs(p=1)[0]
    pb = pm.createNode('pairBlend')
    is_triple = attr_previous_connected.type() == 'double3'
    attr_previous_connected.connect(pb.inTranslate1 if is_triple else pb.inTranslateX1)
    attr_source.connect(pb.inTranslate2 if is_triple else pb.inTranslateX2)
    if is_triple:
        pb.outTranslate.connect(target_attr, force=True)
    else:
        pb.outTranslateX.connect(target_attr, force=True)


def get_selected_attributes():
    attrs = pm.channelBox('mainChannelBox', q=True, sma=True)
    if not attrs:
        return []
    return attrs


def get_attr_info(item_source, attr_name):
    if not item_source.hasAttr(attr_name):
        pm.warning('The attribute{} does not exist in {}'.format(attr_name, item_source))
        return None

    attr = item_source.attr(attr_name)
    attributeType = str(attr.type())

    d_data = dict()
    d_data['longName'] = str(pm.attributeName(attr, l=True))
    d_data['niceName'] = str(pm.attributeName(attr, n=True))
    d_data['shortName'] = str(pm.attributeName(attr, s=True))
    d_data['hidden'] = attr.isHidden()
    d_data['keyable'] = attr.isKeyable()
    d_data['attributeType'] = attributeType

    # d_data['locked'] = attr.isLocked()
    # d_data['maxValue'] = attr.getMax()
    # d_data['minValue'] = attr.getMin()
    # d_data['defaultValue'] = attr.get(default=1)
    # d_data['enumName'] = attr.getEnums() if attributeType == 'enum' else None
    # d_data['in'] = attr.inputs(p=1)
    # d_data['out'] = attr.outputs(p=1)
    # d_data['value'] = attr.get()
    # d_data['parent'] = attr.parent().attrName() if attr.parent() else None
    # d_data['axes'] = dict()

    # if attributeType == 'double3':
    #     d_data['axes'] = {axis: get_attr_info(item_source, attr_name + axis) for axis in 'XYZ'}

    return d_data


mel.eval('file -f -options "v=0;p=17;f=0"  -ignoreVersion  -typ "mayaAscii"'
         '-o "C:/Users/LD_Juan/Documents/maya/projects/default/scenes/attr_tools.ma";'
         'addRecentFile("C:/Users/LD_Juan/Documents/maya/projects/default/scenes/attr_tools.ma", "mayaAscii");')

source = pm.PyNode('obj_attr')
target = pm.PyNode('target')
for attr in ['entero', 'flotante', 'check', 'lista', 'vv3']:
    # print attr
    copy_attr(source, target, attr, move=True)

source = pm.PyNode('target')
target = pm.PyNode('locator1')
for attr in ['entero', 'flotante', 'check', 'lista', 'vv3']:
    # print attr
    copy_attr(source, target, attr, move=True)
