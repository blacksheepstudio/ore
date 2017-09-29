from rf_inventory import get_host_variables

variables = {'name': 'sun08-01', 'ip': '172.27.20.11', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'solfsdb', 'app_type': 'Oracle', 'apps': ['/', 'solfsdb'], 'app_list': ['/', 'solfsdb'], 'app_exclude': ['/'], 'cluster_ip': None, 'racnodelist': None, 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'solfsdb', 'oracle_home': '/oracle/product/11.2.0/dbhome_1', 'oracle_path': '/oracle/product/11.2.0/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/oracle/product/11.2.0/dbhome_1', 'po_tnsadmindir': '/oracle/product/11.2.0/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
