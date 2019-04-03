# Switch

the switch is the main backend and core of all service, it is a django python application with apps for the various services. 
the apps are grouped into modules


python version 2.7 
django version 1.9.XXXX


## Operation

### services
the switch operates by means of calling service, 
service works by accepting a [payload](payload description)  and returning the same payload as a response (might be a copy), 
the service processing steps involves modification of this payload,

the modification includes operations like
- addition of new keys 
- removing of keys 
- updating keys (e.g addition of triggers)
 
services usually have one or more service commands configured to perform the payload modification

#### configuration

services
- enabled logs to transactions table
- poller do not log to transactions table 


### service command
this is the most basic unit of execution configurable, 
the service commands are configured in the apps' tasks.py in clases that extend on of 3 base classes
service commands are able to filtered using
- triggers
- 

1. Payment
2. System
3. 

#### Structure
it is a python function that accepts 
the following parameters

1. self
2. payload
3. node_info

the function must return a response and updates a response status in the payload


#### Service call lifecycle
During a service call, the service commands tied to the service will be executed 
in the order defined by the level, if a service command fails, defined by some status codes or an Error,
executed stops and a response is returned

#### Response
- last response

##### structure
#### status codes


## Structure

django project structure
settings configuration is done in switch.properties
[INSTALLED APPS]


modules
Categories
- primary
- secondary
- thirdparty
- products

module 
a description of module apps

module app
- description
- service commands
	service_command
		function
		operation
		payload input - requirements payload parameters
		payload outputs - addition/modifications to the payload
		status_codes
	creation

## core module apps
### iic
- interface creation

### dsc
- query creation
- configuration of 
	filters
	sorting
	action links
	response types

### bridge
- service configuration

### vcs
- configuration of ussd flows


### administration
- user, profile, gateway profile, institution, gateway
- access levels
- roles
- templates and themes

### notify
- configuration of notification
	email
	sms
	mqtt



