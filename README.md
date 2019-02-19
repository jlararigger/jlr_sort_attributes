
### jlr_sort_attributes.py - Python Script
**Author: Juan Carlos Lara.**

**Description:**

Tools for sort user defined attributes in the channel box.

Creates two menu item commands in the Main Modify Menu, Channel Box Edit Menu and Channel Box Popup Menu.


**Install:**

1- Copy this script file to your scripts directory.

2- In the userSetup.py add the following lines:

    import maya.cmds as cmds
    import jlr_sort_attributes
    
    cmds.evalDeferred('jlr_sort_attributes.create_menu_commands()')


**How to use "Move Attributes Up" or "Move Attributes Down":**

* Select one or more user-defined attributes in the channel box.
* Click on "Move Attributes Up" to move the selected attributes one position up.
* Or click on "Move Attributes down" to move the selected attributes one position down.

**How to use Copy, Cut and Paste Attributes:**

* First select an object and in the channel box, select one or more user-defined attributes.
* Click on "Copy attributes" to copy the selected attributes.
* Or click on 'Cut attributes' to move the selected attributes.
*Finally select the object where you want to copy or move the previously selected attributes and click on "Paste attributes".