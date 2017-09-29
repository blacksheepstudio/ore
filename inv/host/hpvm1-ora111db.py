from rf_inventory import get_host_variables

variables = {'name': 'hpvm1', 'ip': '172.16.159.162', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'ora111db', 'app_type': 'Oracle', 'apps': ['/', 'ora111db'], 'app_list': ['/', 'ora111db'], 'app_exclude': ['/'], 'cluster_ip': '172.16.159.162', 'racnodelist': '172.16.159.162', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'ora111db1', 'oracle_home': '/orahome/oracle/product/11.1.0', 'oracle_path': '/orahome/oracle/product/11.1.0/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/orahome/oracle/product/11.1.0', 'po_tnsadmindir': '/orahome/oracle/product/11.1.0/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
