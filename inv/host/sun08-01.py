from rf_inventory import get_host_variables

variables = {'name': 'sun08-01', 'ip': '172.27.20.11', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'soldb', 'app_type': 'Oracle', 'apps': ['/', 'soldb'], 'app_list': ['/', 'soldb'], 'app_exclude': ['/'], 'cluster_ip': '172.27.20.11', 'racnodelist': '172.27.20.11', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'soldb1', 'oracle_home': '/oracle/product/11.2.0/dbhome_1', 'oracle_path': '/oracle/product/11.2.0/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/oracle/product/11.2.0/dbhome_1', 'po_tnsadmindir': '/oracle/product/11.2.0/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
