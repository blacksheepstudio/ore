from rf_inventory import get_host_variables

variables = {'name': 'sun08-01', 'ip': '172.27.20.11', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'tensoldb', 'app_type': 'Oracle', 'apps': ['/', 'tensoldb'], 'app_list': ['/', 'tensoldb'], 'app_exclude': ['/'], 'cluster_ip': '172.27.20.11', 'racnodelist': '172.27.20.11', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'tensoldb1', 'oracle_home': '/oracle/product/10.2.0/db_1', 'oracle_path': '/oracle/product/10.2.0/db_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/oracle/product/10.2.0/db_1', 'po_tnsadmindir': '/oracle/product/10.2.0/db_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
