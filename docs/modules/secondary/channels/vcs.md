


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


