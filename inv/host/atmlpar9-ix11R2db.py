from rf_inventory import get_host_variables

variables = {'name': 'atmlpar9', 'ip': '172.27.36.34', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'ix11R2db', 'app_type': 'Oracle', 'apps': ['/', 'ix11R2db'], 'app_list': ['/', 'ix11R2db'], 'app_exclude': ['/'], 'cluster_ip': '172.27.36.34', 'racnodelist': '172.27.36.34', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'ix11R2db1', 'oracle_home': '/u01/orahome/11.2.0/product/dbhome_1', 'oracle_path': '/u01/orahome/11.2.0/product/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/u01/orahome/11.2.0/product/dbhome_1', 'po_tnsadmindir': '/u01/orahome/11.2.0/product/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
