iic
Interface Creation and Management

the iic is used for configuring the interfaces for the frontend

This is a channel module responsible for configuration and generation of the interfaces for the web and apps

the interface can be grouped into the following hirechay,

starting from the lowest


### Page Inputs 
Are the Elements, this is the basic unit of a interface.
elements evaluate to a WebComponent on [WEB](link to channel) or a custom view on [APP](link to channel).
they abstract a view and provide a way to do configuration through passing of properties.
page-inputs must be contained in a page input group


#### Creation and Configuration

#### Location
http://switch.interintel.co:8080/admin/iic/pageinput/

### Fields
- name 
- description Page Input Description of the page
- status


#### Defination Array
```
    ['Report Type', 'DROPDOWN SELECT', '1', '45', 'data_name', 'data_name', 'icons:file-download','24|24|4', '', True, '', 'DATA SOURCE']
```
Translates to

## Index   Type    Description

1. 0 - Name - Page input name
2. 1 - Element Type/Variable Type - Describes the element that would be referenced on the frontend
3. 2 - Min-number of characters (if minimum is specified, the characters should not be allowed to be more than minimum)
4. 3- Max-number of characters (if maximum is specified, the characters should not be allowed to be more than maximum)
5. 4 - Element Name - Name of the element (Used to just identify the element key in the form submission)
6. 5 - Default Value - Carries a lot of important instructions and attributes for the element e.g. (data_name)
7. 6 - icon - The element icon
8. 7 - section size - The element width
9. 8 - Kind - Carries a lot of additional important information and attributes for the element e.g. [mqtt subscription channel]
10. 9 - Required = True/False
11. 10 - Style - Additional CSS style
12. 11 - SERVICE - Element service e.g. DATA SOURCE
13. 12 - Element Height
14. 13 - Bind Position
15. 14 - Details - Additional Details JSON Object


### Page input groups
are the containers for page inputs
and to differenciate them by adding the Level 

#### Structure
Can also be sometimes refered to as FORM
as it is used to describe forms (a groupe of inputs) that can be submitted

is has an input variable for extra configurations

when used as a FORM
the form submits to the service set on the input_variable


#### Creation and Configuration

### Location
http://switch.interintel.co:8080/admin/iic/pageinputgroup/

## Fields
- Name the name displayed
- Description Additional details on input group
- Item Level  display position in list
- Gateway    display Gateway (a blank gateway will display on all gateways)


#### Defination Array 

e.g
```
   ['BOOTSTRAP', 'FORM', '0', u'0', 'PLACEHOLDER', '', '', '24|24|24', 'done-all', False, False, 900, 'BOOTSTRAP']
```

Translates to


## index    Type      Description
1. 0 - Name - This is the name of the page input group/form. Can be used as form Title. URL example{/admin/iic/inputvariable/1459/change/?_to_field=id&_popup=1}
2. 1 - Form Type/Variable Type - Describes the FORM type that would be referenced on the frontend Url example{/admin/iic/variabletype/5/change/?_to_field=id&_popup=1}
3. 2 - Min
4. 3 - Max-
5. 4 - Element Name - Name of the element (No Particular use. Used to just identify the element)
6. 5 - Default value - Form URL or (POST|GET) location
7. 6 - icon - The element icon
8. 7 - section size - The form width
9. 8 - Kind - Any Additional form attribute
10. 9 - Auto submit flag - Instructs form to autosubmit
11. 10 - Style - Additional CSS style
12. 11 - SERVICE - Form /GOTO/ service
13. 12 - Form Height
14. 13 - Bind Position
15. 14 - Details - Additional Details JSON Object



### Pages
are the containers for page input groups

#### Creation and Configuration

### Location
http://switch.interintel.co:8080/admin/iic/page/


## Fields
- Name the name displayed
- Description Additional details on input group
- Item Level display position in list
- Access Level User’s access rights
- Gateway  display Gateway (a blank gateway will display on all gateways)
- Profile Status Current status of page


### Page Groups
are the Containers for Pages 

#### Creation and Configuration

### Location 
http://switch.interintel.co:8080/admin/iic/pagegroup/

### Fields
- Name the name displayed
- Item Level  display position in list
- Gateway    display Gateway (a blank gateway will display on all gateways)
