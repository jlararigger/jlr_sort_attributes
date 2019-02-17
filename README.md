
### jlr_sort_attributes.py - Python Script
**Author: Juan Carlos Lara.**

**Description:**

Tools for sort user defined attributes in the channel box.

Creates two menu item commands in the Main Modify Menu, Channel Box Edit Menu and Channel Box Popup Menu.


**Install:**
1- Copy in the scripts directory this script file.
2- In the userSetup.py add the following lines:

    import maya.cmds as cmds
    import jlr_sort_attributes
    
    cmds.evalDeferred('jlr_sort_attributes.create_menu_commands()')

**Usage:**

Select one or more user defined attributes in the channel box.
Click "Move Up Attr" for move the selected attributes one position up.
Or click "Move Down Attr" for move the selected attributes one position down.
