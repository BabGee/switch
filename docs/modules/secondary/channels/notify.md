
this module is used for messaging and sending notifications to the various [channels](link to channels doc).

- SMS
- EMAIL
- MQTT

notification are sent asynchronously  using a background service, 
the background service sends out notifications from the Outbound table  


# Configuring a notification

the **notification product** 

- it mainly ties services to relevant Notification to be sent (at notification is where the template/message is defined) 
- it holds other configs 
    i.e 
    - describes the charges for sending the notification,
    - defines if the notification subscribable/recurring
 

## Required service commands to send a notification
the main service commands required to send a notification to single channel are

1. get_notification

retrieves the notification product and updates into `payload['notification_product_id']`

this requires that the `notification_delivery_channel` be defined
you can use the service commands `get_email_notification` , `get_sms_notification` to define the delivery channel

performs the message template processing 

for SMS
this also splits the message into groups of 160 chars to work  and updates the float amount



2. send_notification

logs the notification into the Outbound table for sending 

this also creates a contact, used to manage subscriptions
performs message template processing if `notification_template_id`


notification can be scheduled by passing `payload["scheduled_send"], '%d/%m/%Y %I:%M %p'`


the above work for a single channel, if you need to send notifications to more than 1 channel from the same service,
you need to add `init_notification` to reset the previous notification processing.
it will remove/reset 
- payload['notification_template_id']
- payload['notification_product_id']
- payload['message']
 
 
 ### For paid notification
 No float amount to debit
 - float are the the notification charges
 - for paid notifications, e.g SMS, 
    the institution or gateway should have float to be able to send the notification


# Creating a notification Product

If the notification product exist, it will be logged
Coz, it checks the MNO and log the notification product for that MNO
So, if its not defined, no notification product would be found
But, one can create more like a placeholder notification product if you need to send to other MNOs


Then, we'll need to create a notification product for Telkom

One starts fom 
1. vcs.code
2. notify.notification
3. notify.notification_product
4. notify.notification_template(add the notification_product to a message template)

That's all
I think on list of MNOs, Telkom reads Orange


And you can add MNO prefixes, or change MNOs on need under the Administration module
That structure helps in routing of SMSs etc

If we create a notification product for Orange, your SMSs would be logged
Though one can create a general one for all the MNOs that don't have a uniquely defined notification product
This is what the function get_notification does
Filtering and routing SMS as per their product
By logging so that async services can do their thing


