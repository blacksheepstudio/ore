from rf_inventory import get_host_variables

variables = {'name': 'hpvm1', 'ip': '172.16.159.162', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'hpracdb', 'app_type': 'Oracle', 'apps': ['/', 'hpracdb'], 'app_list': ['/', 'hpracdb'], 'app_exclude': ['/'], 'cluster_ip': '172.16.159.162', 'racnodelist': '172.16.159.162', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'hpracdb1', 'oracle_home': '/orahome/app/11.2.0/product/dbhome_1', 'oracle_path': '/orahome/app/11.2.0/product/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/orahome/app/11.2.0/product/dbhome_1', 'po_tnsadmindir': '/orahome/app/11.2.0/product/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
