
if we reference the many to many object fields, it will return a list for every item in the many to many field


For q to filter, you need to add the fields to be filtered
If you need an AND filter, you use the and_filter field
If you need an OR filter, you use the or_filter field
If its a filter that has a list, list_filter would be used
Basically, the same query used on the header filters would be used with q

For and and or filters, you would require the alias%field|alias%field|alias%field
q would be filtering on fields All fields
The alias would be for direct particular field matching with its alias
Meaning, q would do all fields, and alias would do only its field

payload['q'] will filter all fields in AND and OR payload['alias'] will filter only the alias column



## Filtering 

or_filters -> adds search input fields
e.g
service__name|gateway_profile__msisdn__phone_number


list_filters -> adds column dropdowns to datalist
this provides a means of filtering down for only a specific row column
e.g 
service__name|gateway_profile__msisdn__phone_number



## Action
added using *Data list link querys*
> the Link Name must be unique