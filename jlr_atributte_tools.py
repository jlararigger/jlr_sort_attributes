#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymel.core as pm


def copy_attr(item_source, item_target, attr_name, move=False):
    if not item_source.hasAttr(attr_name):
        pm.warning('The attribute{} does not exist in {}'.format(attr_name, item_source))
        return None

    # Get source attribute info
    source_attr = item_source.attr(attr_name)
    attr_data = get_attr_info(source_attr)
    if not attr_data:
        return None

    source_value = source_attr.get()
    source_is_locked = source_attr.isLocked()
    source_is_compound = source_attr.isCompound()
    source_connections = get_attr_connections(source_attr)

    source_child_info = dict()
    source_child_connections = dict()
    if source_is_compound:
        source_child_info = dict()
        source_child_connections = dict()
        for child in source_attr.getChildren():
            source_child_info[child.attrName()] = get_attr_info(child)
            source_child_connections[child.attrName()] = get_attr_connections(child)

    if move:
        if source_is_locked: source_attr.unlock()
        pm.deleteAttr(source_attr)

    # Create the attribute
    create_attr(item_target, attr_data)

    # If attribute is a Compound, the children attributes are created
    if source_is_compound:
        for child_key in sorted(source_child_info.keys()):
            create_attr(item_target, source_child_info[child_key])

    new_attr = item_target.attr(attr_name)

    # Copy the value
    new_attr.set(source_value)

    # Copy the lock status
    if source_is_locked:
        new_attr.lock()
    else:
        new_attr.unlock()

    # Connect the attributes
    connect_attr(new_attr, **source_connections)

    # If attribute is a Compound, the children attributes are connected
    if source_is_compound:
        for attr_child, child_key in zip(new_attr.getChildren(), sorted(source_child_connections.keys())):
            connect_attr(attr_child, **source_child_connections[child_key])

    return new_attr


def create_attr(item, attr_data):
    attr_name = attr_data['longName']

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
    pm.addAttr(item, **attr_data)


def connect_attr(attribute, inputs=None, outputs=None):
    if inputs:
        for attr_input in inputs:
            if attribute.inputs():
                make_shared_connection(attr_input, attribute)
            else:
                attr_input.connect(attribute)

    if outputs:
        if attribute.type() in ['long', 'bool', 'double', 'enum', 'double3']:
            for attr_output in outputs:
                if attr_output.inputs(p=1):
                    make_shared_connection(attribute, attr_output)
                else:
                    attribute.connect(attr_output)


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


def get_attr_info(attribute):
    attribute_type = str(attribute.type())

    d_data = dict()
    d_data['longName'] = str(pm.attributeName(attribute, long=True))
    d_data['niceName'] = str(pm.attributeName(attribute, nice=True))
    d_data['shortName'] = str(pm.attributeName(attribute, short=True))
    d_data['hidden'] = attribute.isHidden()
    d_data['keyable'] = attribute.isKeyable()

    if attribute_type in ['string']:
        d_data['dataType'] = attribute_type
    else:
        d_data['attributeType'] = attribute_type

    if attribute_type in ['long', 'double', 'bool']:
        d_data['defaultValue'] = attribute.get(default=True)
        if attribute.getMax(): d_data['maxValue'] = attribute.getMax()
        if attribute.getMin(): d_data['minValue'] = attribute.getMin()

    if attribute_type in ['enum']:
        d_data['enumName'] = attribute.getEnums()

    if attribute.parent():
        d_data['parent'] = attribute.parent().attrName()

    return d_data


def get_attr_connections(source_attr):
    source_inputs = source_attr.inputs(p=True)
    source_outputs = source_attr.outputs(p=True)
    return {'inputs': source_inputs, 'outputs': source_outputs}


def move_up_attribute():
    selected_attributes = get_selected_attributes()

    if not len(pm.ls(sl=1)) or not selected_attributes:
        print 'Nothing Selected'
        return

    selected_items = pm.selected()
    last_parent = None

    for item in selected_items:
        for attribute in selected_attributes:
            if item.attr(attribute).parent():
                attribute = item.attr(attribute).parent().attrName()
                if attribute == last_parent:
                    continue
                last_parent = attribute

            all_attributes = get_all_user_attributes(item)
            pos_attr = all_attributes.index(attribute)
            if pos_attr == 0: continue

            below_attr = all_attributes[pos_attr - 1:]
            below_attr.remove(attribute)

            copy_attr(item, item, attribute, move=True)
            for attr in below_attr:
                copy_attr(item, item, attr, move=True)


def move_down_attribute():
    selected_attributes = get_selected_attributes()

    if not len(pm.ls(sl=1)) or not selected_attributes:
        print 'Nothing Selected'
        return

    selected_items = pm.selected()
    last_parent = None

    for item in selected_items:
        for attribute in reversed(selected_attributes):

            if item.attr(attribute).parent():
                attribute = item.attr(attribute).parent().attrName()
                if attribute == last_parent:
                    continue
                last_parent = attribute

            all_attributes = get_all_user_attributes(item)
            pos_attr = all_attributes.index(attribute)
            if pos_attr == len(all_attributes) - 1: continue

            below_attr = all_attributes[pos_attr + 2:]

            copy_attr(item, item, attribute, move=True)
            for attr in below_attr:
                copy_attr(item, item, attr, move=True)


def get_all_user_attributes(item):
    all_attributes = list()
    for attr in pm.listAttr(item, ud=True):
        if not item.attr(attr).parent():
            all_attributes.append(attr)
    return all_attributes


if __name__ == '__main__':
    move_down_attribute()

    # mel.eval('file -f -options "v=0;p=17;f=0"  -ignoreVersion  -typ "mayaAscii"'
    #          '-o "C:/Users/LD_Juan/Documents/maya/projects/default/scenes/attr_tools.ma";'
    #          'addRecentFile("C:/Users/LD_Juan/Documents/maya/projects/default/scenes/attr_tools.ma", "mayaAscii");')
    #
    # copy_attr(pm.PyNode('obj_attr'), pm.PyNode('target'), 'flotante', move=True)
    # copy_attr(pm.PyNode('obj_attr'), pm.PyNode('target'), 'check', move=True)
    # copy_attr(pm.PyNode('obj_attr'), pm.PyNode('target'), 'entero', move=True)
    # copy_attr(pm.PyNode('obj_attr'), pm.PyNode('target'), 'cadena', move=True)
    # copy_attr(pm.PyNode('obj_attr'), pm.PyNode('target'), 'lista', move=True)
    # copy_attr(pm.PyNode('obj_attr'), pm.PyNode('target'), 'vv3', move=True)
