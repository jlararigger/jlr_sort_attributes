#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymel.core as pm
import maya.mel as mel


##############################################
# Menus Items
##############################################

def create_menu_commands():
    """
    Create the menu commands
    Move Up: Move the selected attributes one position up
    Move Down: Move the selected attributes one position down
    """
    edit_menu = 'ChannelBoxLayerEditor|MainChannelsLayersLayout|ChannelsLayersPaneLayout|ChannelBoxForm|menuBarLayout1|menu3'
    channel_box_popup = 'ChannelBoxLayerEditor|MainChannelsLayersLayout|ChannelsLayersPaneLayout|ChannelBoxForm|menuBarLayout1|frameLayout1|mainChannelBox|popupMenu1'

    mel.eval('generateCBEditMenu {} 0;'.format(edit_menu))
    mel.eval('generateChannelMenu {} 1;'.format(channel_box_popup))

    d_cbf_items = {'jlr_cbf_attrMoveUp': {'label': 'Move Up', 'command': move_up_attribute},
                   'jlr_cbf_attrMoveDown': {'label': 'Move Down', 'command': move_down_attribute}
                   }

    d_cbpm_items = {'jlr_cbpm_attrMoveUp': {'label': 'Move Up', 'command': move_up_attribute},
                    'jlr_cbpm_attrMoveDown': {'label': 'Move Down', 'command': move_down_attribute}
                    }

    for key, value in d_cbf_items.iteritems():
        if pm.menuItem(key, q=True, exists=True):
            pm.deleteUI(key)

        pm.menuItem(key, parent=edit_menu, **value)

    for key, value in d_cbpm_items.iteritems():
        if pm.menuItem(key, q=True, exists=True):
            pm.deleteUI(key)

        pm.menuItem(key, parent=channel_box_popup, **value)


#########################################
# Attribute methods
#########################################

def copy_attr(item_source, item_target, attr_name, move=False):
    """
    Copy or move a existing user defined attribute between objects.
    Copy the source attribute connections to the new attribute.
    If the attribute is copied and has connections, these will be connected through a pairBlend node in order
    to maintain the old and new connections.
    :param item_source: String or Node. Object with the user defined attribute.
    :param item_target: String or Node. Object will receive the user defined attribute.
    :param attr_name: String. Name of the attribute to be copied.
    :param move: Boolean. Indicate if the attribute must be copied or moved
    :return: Attribute. The new attribute.
    """
    if type(item_source) is str: item_source = pm.PyNode(item_source)
    if type(item_target) is str: item_target = pm.PyNode(item_target)

    if not item_source.hasAttr(attr_name):
        pm.warning('The attribute{} does not exist in {}'.format(attr_name, item_source))
        return None

    # Get source attribute info.
    source_attr = item_source.attr(attr_name)
    attr_data = get_attr_info(source_attr)
    if not attr_data:
        return None

    source_value = source_attr.get()
    source_is_locked = source_attr.isLocked()
    source_is_compound = source_attr.isCompound()
    source_connections = get_attr_connections(source_attr)

    # If attribute is a Compound, read the children attributes info.
    source_child_info = dict()
    source_child_connections = dict()
    if source_is_compound:
        for child in source_attr.getChildren():
            source_child_info[child.attrName()] = get_attr_info(child)
            source_child_connections[child.attrName()] = get_attr_connections(child)

    # If move mode, remove the source attribute.
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
    if item.hasAttr(attr_name):
        pm.warning('The attribute {} already exist in {}.'
                   'Can not create a new attribute with the same name'.format(attr_name, item))

    else:
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
    d_previous = {True: pb.inTranslate1, False: pb.inTranslateX1}
    d_source = {True: pb.inTranslate2, False: pb.inTranslateX2}
    d_out = {True: pb.outTranslate, False: pb.outTranslateX}

    is_compound = attr_previous_connected.isCompound()
    attr_previous_connected.connect(d_previous[is_compound])
    attr_source.connect(d_source[is_compound])
    d_out[is_compound].connect(target_attr, force=True)


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
    return {'inputs': source_attr.inputs(p=True), 'outputs': source_attr.outputs(p=True)}


def move_up_attribute(*args):
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

            if attribute not in all_attributes:
                continue

            pos_attr = all_attributes.index(attribute)
            if pos_attr == 0: continue

            below_attr = all_attributes[pos_attr - 1:]
            below_attr.remove(attribute)

            copy_attr(item, item, attribute, move=True)
            for attr in below_attr:
                copy_attr(item, item, attr, move=True)


def move_down_attribute(*args):
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

            if attribute not in all_attributes:
                continue

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
    create_menu_commands()
    # copy_attr('obj_attr', 'target', 'entero')
