from rf_inventory import get_host_variables

variables = {'name': 'nstlpar24', 'ip': '172.27.8.90', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'ten205db', 'app_type': 'Oracle', 'apps': ['/', 'ten205db'], 'app_list': ['/', 'ten205db'], 'app_exclude': ['/'], 'cluster_ip': '172.27.8.90', 'racnodelist': '172.27.8.90', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'ten205db1', 'oracle_home': '/ora10gr2home/db/OraHome_1', 'oracle_path': '/ora10gr2home/db/OraHome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/ora10gr2home/db/OraHome_1', 'po_tnsadmindir': '/ora10gr2home/db/OraHome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
