from rf_inventory import get_host_variables

variables = {'name': 'nstlpar24', 'ip': '172.27.8.90', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'autodb', 'app_type': 'Oracle', 'apps': ['/', 'autodb'], 'app_list': ['/', 'autodb'], 'app_exclude': ['/'], 'cluster_ip': '172.27.8.90', 'racnodelist': '172.27.8.90', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'autodb1', 'oracle_home': '/database/11.2.0/product/dbhome_1', 'oracle_path': '/database/11.2.0/product/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/database/11.2.0/product/dbhome_1', 'po_tnsadmindir': '/database/11.2.0/product/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
