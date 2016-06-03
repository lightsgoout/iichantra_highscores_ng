from django import template

register = template.Library()


@register.filter
def mult(value, arg):
    "Multiplies the arg and the value"
    try:
        return int(value) * int(arg)
    except ValueError:
        return value


@register.filter
def sub(value, arg):
    try:
        return int(value) - int(arg)
    except ValueError:
        return value


@register.filter
def seconds2time(value):
    try:
        h = value / 3600
        m = value / 60 - h * 60
        s = value - (h * 3600 + m * 60)

        sh = str(h) if h > 0 else "00"
        sm = "0" + str(m) if m < 10 else m
        if m == 0:
            sm = "00"
        ss = "0" + str(s) if s < 10 else s
        if s == 0:
            ss = "00"

        return "%s:%s:%s" % (sh, sm, ss)
    except ValueError:
        return value
