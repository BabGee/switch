 On USSD, we have levels and groups

 Each hop increments to a level

 and each menu item number selected, have the child items in the next level within the group
---

 Basically, all menu entries would have a level and a group


 And each menu entry can have static menu items, which is the list items entered in menu_items table

 Or dynamic menu items

 Which are created under vcs/backends/page_string.py

-----


 For dynamic menu items, these are menu items that cannot be staticly defined in the table and would be generated from DB records, API's or such


 Each menu and menu item filters to a specific access level and profile status

 For instance, CUSTOMERS, OPERATORS, ADMINISTRATOR etc can have different or same menus

 And ACTIVATED, REGISTERED or ONE TIME PIN profiles can have different or same experience

 There's also a functionality that allows a menu to be closed up behind a PIN requirement


 On the PIN functionality that closes up a menu, this is controlled by the protected field on the menu

 A menu can also be fully enabled or disabled

 There are many variable types allow for entry on the menu of which the menu does not proceed to the next level if the variable check fails

 It validates on each entry as per the input variable which would control the variable type and even the maximum and minimum number of characters

 For instance, if an input variable for a menu is a mobile number, the minimum characters for that are 10 and maximum 12. Any more or less wouldn't allow level to proceed

---

 Services are used in filtering for the position of the menu just like level and group

 A service is optional for each menu

 But once a service is introduced, all the child menu levels in the group have to match the service

 The submit field works hand in hand with the service

 All parameters for a service execution are collected and payload created from the menus that had the selection preview field as "True"

 The menu description becomes the "key" for the payload entry item

 The payload is then submitted to the service on the menu level that has submit field set as "True"

 A menu can have multiple codes pointing to the same menu as the code field is a ManyToMany field

 This means, where an airtel and Safaricom code match in experience, the two codes would be set

-----

Dynamic menu variable looks same as the IIC one

 uses the [variable_name]

 In this case, it looks up from the page_string.py file for the variable and attaches the result

 The [variable_name] can be placed anywhere on the page_string



 Make sure that the session state is CON or BEG

 for whichever menu that would accept entry

 For a menu that exits, the session state should be END

 BEG is for the first 0,0 menu

 CON can still do

 BEG not a must

 Actually, just use CON

 CON is for CONTINUE

-----

menu

page_string  -> controlls ussd menu based on the service command response status

status_code%message%control 

constol can be
- CON
- END


## Adding a USSD menu from a DSC query
You can look at the DataList entry example with data_name "gatewayprofile.postaladdress". 
It updates to USSD. First you create a STRING data type entry

Then you add a [variable] to the USSD entry page string
The terms and conditions are updated with a link ending with .pdf
You can do a vcs/menu/?all=
then search for all .pdf
then, the link can be replaced with the [settings.termsandconditions] variable that will search DataList table for


---

### tasks

#### vcs_menu  
generates vcs menus

view_data = VAS().menu_input(payload, node_info)


VAS 
maintains view_data (an object representation of the view)

-- methods
create_menu

menu_view


