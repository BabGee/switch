>>> from django.utils import translation
>>> translation.activate("fr")
>>> my_string = _("Yes")
Traceback (most recent call last):
  File "<console>", line 1, in <module>
NameError: name '_' is not defined
>>> from django.utils.translation import ugettext as _
>>> 
>>> my_string = _("Yes")
>>> my_string
