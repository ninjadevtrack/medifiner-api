# from django import forms
# from .models import Epidemic
# from epidemic.widgets import WYMEditor


# class EpidemicAdminModelForm(forms.ModelForm):
#     content = forms.CharField(widget=WYMEditor())
#     active = forms.BooleanField()

#     class Meta:
#         model = Epidemic

from django import forms
from tinymce.widgets import TinyMCE

class EpidemicForm(forms.ModelForm):

  content = forms.CharField(max_length=300, required=False,  widget=TinyMCE(attrs={'cols':80, 'rows': 4}, mce_attrs={   
      "theme": "advanced",
      "plugins": "table,spellchecker,paste,searchreplace",
      'max_chars': "300",         
     
  }))
  active = forms.BooleanField()  