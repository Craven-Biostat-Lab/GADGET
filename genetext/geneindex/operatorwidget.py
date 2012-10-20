#!/usr/bin/python

from django import forms

class OperatorInput(forms.widgets.RadioInput):
    def __unicode__(self):
        if 'id' in self.attrs:
            label_for = 
