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
import re
def cleanhtml(raw_html):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext
class EpidemicForm(forms.ModelForm):

  content = forms.CharField(required=False, widget=TinyMCE(attrs={'cols':80, 'rows': 4}, mce_attrs={   
      "theme": "advanced",
      "plugins": "table,spellchecker,paste,searchreplace",
      'max_chars': "300",         
     
  }))
  active = forms.BooleanField()  

  def clean_content(self):
        content = self.cleaned_data['content']
        html_tag_trim = re.compile('<.*?>')
        trimedContent =re.sub(html_tag_trim, '', content); 
        length = len(trimedContent)
        if len(trimedContent) > 300:
            raise forms.ValidationError(u"The maximum length of the content is 300. You have entered "+ str(length) +" characters.")
        return content