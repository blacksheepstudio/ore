from rf_inventory import get_host_variables

variables = {'name': 'sun08-03', 'ip': '172.27.20.18', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'sol12pdb', 'app_type': 'Oracle', 'apps': ['/', 'sol12pdb'], 'app_list': ['/', 'sol12pdb'], 'app_exclude': ['/'], 'cluster_ip': '172.27.20.18', 'racnodelist': '172.27.20.18', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'sol12pdb1', 'oracle_home': '/oracle/12.1.0/product/dbhome_1', 'oracle_path': '/oracle/12.1.0/product/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/oracle/12.1.0/product/dbhome_1', 'po_tnsadmindir': '/oracle/12.1.0/product/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
