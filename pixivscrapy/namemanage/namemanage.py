# coding: utf-8


def name_manage(m):
    m = m.strip()
    m = m.replace('\\', '')
    m = m.replace('/', '')
    m = m.replace(':', '')
    m = m.replace('*', '')
    m = m.replace('?', '')
    m = m.replace('"', '')
    m = m.replace('<', '')
    m = m.replace('>', '')
    m = m.replace('|', '')
    m = m.rstrip("\\")
    return m


