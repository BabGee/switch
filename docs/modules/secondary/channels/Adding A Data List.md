```
you specify the  model, module   and the model fields to be returned
you start from Dsc > Data List
here is where you set the data_name then in the query field is where you'll configure the module and model
and the fields
there are also more configurations you can do like joins, ordering depending on the data you want to query

on query 

the main fields are 

Module name: the module that has the module, this are the switch django apps 

Model name: a model in the module, has a corresponding database table created by django
Values: the model fields, will be the database columns 
they are formatted in this way 

id%id|name%name

table_column_title1%model_field_path1|table_column_title2%model_field_path2

```