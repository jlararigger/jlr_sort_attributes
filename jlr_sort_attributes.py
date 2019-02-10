import pymel.core as pm
import maya.mel as mel


##################################################################################
# jlr_sort_attributes.py - Python Script
##################################################################################
# Description:
# Tools for sort user defined attributes in the channel box.
# Creates two menu item commands in the Main Modify Menu, Channel Box Edit Menu and Channel Box Popup Menu.
#
# Author: Juan Lara.
##################################################################################
# Install:
# 1- Copy in the scripts directory this script file.
# 2- In the userSetup.py add the following lines:
#
# import maya.cmds as cmds
# import jlr_sort_attributes
#
# cmds.evalDeferred('jlr_sort_attributes.create_menu_commands()')
#
##################################################################################
# Usage:
# Select one or more user defined attributes in the channel box.
# Click "Move Up Attr" for move the selected attributes one position up.
# Or click "Move Down Attr" for move the selected attributes one position down.
##################################################################################


##############################################
# Menus Items
##############################################

def create_menu_commands():
    """
    Create the menu commands.
    Move Up: Move the selected attributes one position up.
    Move Down: Move the selected attributes one position down.
    """
    edit_menu = 'ChannelBoxLayerEditor|MainChannelsLayersLayout|ChannelsLayersPaneLayout|ChannelBoxForm|menuBarLayout1|menu3'
    channel_box_popup = 'ChannelBoxLayerEditor|MainChannelsLayersLayout|ChannelsLayersPaneLayout|ChannelBoxForm|menuBarLayout1|frameLayout1|mainChannelBox|popupMenu1'
    main_modify_menu = 'MayaWindow|mainModifyMenu'

    mel.eval('generateCBEditMenu {} 0;'.format(edit_menu))
    mel.eval('generateChannelMenu {} 1;'.format(channel_box_popup))
    mel.eval('ModObjectsMenu {};'.format(main_modify_menu))

    d_cbf_items = {'jlr_cbf_attrMoveUp': {'label': 'Move Up Attr', 'command': move_up_attribute},
                   'jlr_cbf_attrMoveDown': {'label': 'Move Down Attr', 'command': move_down_attribute}
                   }

    remove_ui_item_menu(['jlr_divider'])
    remove_ui_item_menu(d_cbf_items.keys())

    add_commands_to_menu(d_cbf_items, edit_menu, divider=True)
    add_commands_to_menu(d_cbf_items, channel_box_popup, divider=True)
    add_commands_to_menu(d_cbf_items, main_modify_menu, divider=True)


def remove_ui_item_menu(name_list):
    """
    It removes command menu items from maya UI.
    :param name_list: list with the name of UI items to remove.
    """
    for name in name_list:
        for item in pm.lsUI():
            if item.endswith(name):
                pm.deleteUI(item)


def add_commands_to_menu(d_commands, menu, divider=False):
    """
    It adds a new menu items to a menu.
    :param d_commands: dictionary with the name, label and command of menu item.
    :param menu: menu object where the items will be created.
    :param divider: Boolean that indicates if a divider must be added before creating the menu items.
    """
    if divider:
        name = '{}_{}'.format(menu.split('|')[-1], 'jlr_divider')
        pm.menuItem(name, parent=menu, divider=divider, dividerLabel='Sort Attributes')

    for key, value in d_commands.iteritems():
        name = '{}_{}'.format(menu.split('|')[-1], key)
        pm.menuItem(name, parent=menu, **value)


#########################################
# Attribute methods
#########################################

def copy_attr(node_source, node_target, attr_name, move=False):
    """
    Copy or move a existing user defined attribute between nodes.
    Copy the source attribute connections to the new attribute.
    If the attribute is copied and has connections, these will be connected through a pairBlend node in order
    to maintain the old and new connections.
    :param node_source: String or dagNode. Object with the user defined attribute.
    :param node_target: String or dagNode. Object will receive the user defined attribute.
    :param attr_name: String. Name of the attribute to be copied.
    :param move: Boolean. Indicate if the attribute must be copied or moved.
    :return: Attribute. The new attribute.
    """
    if type(node_source) is str:
        node_source = pm.PyNode(node_source)
    if type(node_target) is str:
        node_target = pm.PyNode(node_target)

    if not node_source.hasAttr(attr_name):
        pm.warning('The attribute{} does not exist in {}'.format(attr_name, node_source))
        return None

    # Get source attribute info.
    source_attr = node_source.attr(attr_name)
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
        if source_is_locked:
            source_attr.unlock()
            # TODO: Check if the connections are blocked to get the attribute removed
            pm.deleteAttr(source_attr)

    # Create the attribute
    create_attr(node_target, attr_data)

    # If attribute is a Compound, the children attributes are created
    if source_is_compound:

        for child_key in sorted(source_child_info.keys()):
            create_attr(node_target, source_child_info[child_key])

    new_attr = node_target.attr(attr_name)

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


def create_attr(node, attr_data):
    """
    This method creates a new attribute in a node.
    If the node already has an attribute with the same name, the new attribute will not be created.
    :param node: dagNode.
    :param attr_data: dictionary with the necessary data to create the attribute.
    """

    # It checks if the attribute already exists within the node.
    attr_name = attr_data['longName']
    if node.hasAttr(attr_name):
        pm.warning('The attribute {} already exist in {}.'
                   'Can not create a new attribute with the same name'.format(attr_name, node))

    else:
        # Creating the attribute
        pm.addAttr(node, **attr_data)


def connect_attr(attribute, inputs=None, outputs=None):
    """
    It connects an attribute to passed inputs and outputs.
    :param attribute: Attribute Object.
    :param inputs: list of inputs attributes.
    :param outputs: list of outputs attributes.
    """
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
    """
    It connects an attribute to other connected attribute by pairblend node.
    This way the target attribute does'nt lose their existing connections.
    :param attr_source: Source attribute.
    :param target_attr: Target attribute.
    """
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
    """
    Get the selected attributes in the ChannelBox.
    If there are not attributes selected, this method returns a empty list.
    :return: list with the selected attributes.
    """
    attrs = pm.channelBox('mainChannelBox', q=True, sma=True)
    if not attrs:
        return []

    return attrs


def get_attr_info(attribute):
    """
    Get all data of a passed attribute.
    The data that it returns depends on the type of attribute.
    :param attribute: Attribute Object.
    :return: dictionary with the necessary data to recreate the attribute.
    """
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
        if attribute.getMax():
            d_data['maxValue'] = attribute.getMax()
        if attribute.getMin():
            d_data['minValue'] = attribute.getMin()

    if attribute_type in ['enum']:
        d_data['enumName'] = attribute.getEnums()

    if attribute.parent():
        d_data['parent'] = attribute.parent().attrName()

    return d_data


def get_attr_connections(source_attr):
    """
    It returns the inputs and outputs connections of an attribute.
    :param source_attr: Attribute Object.
    :return: dictionary with the inputs and outputs connections.
    """
    return {'inputs': source_attr.inputs(p=True), 'outputs': source_attr.outputs(p=True)}


def select_attributes(attributes, nodes):
    """
    Selects the passed attributes in the main Channel Box.
    :param attributes: List of the attributes to select.
    :param nodes: List of the objects with the attributes to select
    """
    to_select = ['{}.{}'.format(n, a) for a in attributes for n in nodes]
    pm.select(nodes, r=True)
    str_command = "import pymel.core as pm\npm.channelBox('mainChannelBox', e=True, select={}, update=True)"
    pm.evalDeferred(str_command.format(to_select))


def move_up_attribute(*args):
    """
    It moves a selected attributes in the channel box one position up.
    :param args: list of arguments.
    """
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
            if pos_attr == 0:
                continue

            below_attr = all_attributes[pos_attr - 1:]
            below_attr.remove(attribute)

            copy_attr(item, item, attribute, move=True)
            for attr in below_attr:
                copy_attr(item, item, attr, move=True)

    select_attributes(selected_attributes, selected_items)


def move_down_attribute(*args):
    """
    It moves a selected attributes in the channel box one position down.
    :param args: list of arguments.
    """
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
            if pos_attr == len(all_attributes) - 1:
                continue

            below_attr = all_attributes[pos_attr + 2:]

            copy_attr(item, item, attribute, move=True)
            for attr in below_attr:
                copy_attr(item, item, attr, move=True)

    select_attributes(selected_attributes, selected_items)


def get_all_user_attributes(node):
    """
    It gets all user defined attributes of a node.
    :param node: dagNode.
    :return: list with all user defined attributes.
    """
    all_attributes = list()
    for attr in pm.listAttr(node, ud=True):
        if not node.attr(attr).parent():
            all_attributes.append(attr)
    return all_attributes
