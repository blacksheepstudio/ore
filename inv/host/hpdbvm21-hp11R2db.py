from rf_inventory import get_host_variables

variables = {'name': 'hpdbvm21', 'ip': '172.16.159.73', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'hp11R2db', 'app_type': 'Oracle', 'apps': ['/', 'hp11R2db'], 'app_list': ['/', 'hp11R2db'], 'app_exclude': ['/'], 'cluster_ip': '172.16.159.73', 'racnodelist': '172.16.159.73', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'hp11R2db1', 'oracle_home': '/oracle/11.2.0/product/dbhome_1', 'oracle_path': '/oracle/11.2.0/product/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/oracle/11.2.0/product/dbhome_1', 'po_tnsadmindir': '/oracle/11.2.0/product/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
