```
#!text
If the notification product exist, it will be logged
Coz, it checks the MNO and log the notification product for that MNO
So, if its not defined, no notification product would be found
But, one can create more like a placeholder notification product if you need to send to other MNOs
I think for DOOKA we've only created safcom
Or Safcom and airtel

Then, we'll need to create a notification product for Telkom
One starts fom vcs.code->notify.notification->notify.notification_product->notify.notification_template(add the notification_product to a message template)
That's all
I think on list of MNOs, Telkom reads Orange

They are the same prefixes right?
And you can add MNO prefixes, or change MNOs on need under the Administration module
That structure helps in routing of SMSs etc

If we create a notification product for Orange, your SMSs would be logged
Though one can create a general one for all the MNOs that don't have a uniquely defined notification product
This is what the function get_notification does
Filtering and routing SMS as per their product
By logging so that async services can do their thing


```