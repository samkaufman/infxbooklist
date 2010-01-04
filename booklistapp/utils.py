def english_list(l,the_and="&"):
    if isinstance(l, type("")) or isinstance(l, type(u'')):
        return l
    if len(l) == 1:
        return l[0]
    else:
        return ', '.join(l[:-1])+' '+the_and+' '+l[-1]
        