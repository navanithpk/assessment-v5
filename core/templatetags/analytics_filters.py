"""
Custom template filters for analytics dashboard
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary in template
    Usage: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def get_lo_performance(student, lo_name):
    """
    Get LO performance for a student
    Usage: {{ student|get_lo_performance:lo.name }}
    """
    if not hasattr(student, 'get') or 'lo_performance' not in student:
        return None
    return student['lo_performance'].get(lo_name)
