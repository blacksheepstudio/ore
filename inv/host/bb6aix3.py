from rf_inventory import get_host_variables

variables = {'name': 'bb6aix3', 'ip': '172.16.199.53', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'bb12rcdb', 'app_type': 'Oracle', 'apps': ['/', 'bb12rcdb'], 'app_list': ['/', 'bb12rcdb'], 'app_exclude': ['/'], 'cluster_ip': '172.16.199.53', 'racnodelist': '172.16.199.53', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'bb12rcdb1', 'oracle_home': '/oracle/12.1.0/product/dbhome_1', 'oracle_path': '/oracle/12.1.0/product/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/oracle/12.1.0/product/dbhome_1', 'po_tnsadmindir': '/oracle/12.1.0/product/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
