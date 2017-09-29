from rf_inventory import get_host_variables

variables = {'name': 'nstlpar24', 'ip': '172.27.8.90', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'ora111db', 'app_type': 'Oracle', 'apps': ['/', 'ora111db'], 'app_list': ['/', 'ora111db'], 'app_exclude': ['/'], 'cluster_ip': '172.27.8.90', 'racnodelist': '172.27.8.90', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'ora111db', 'oracle_home': '/home/oracle/app/product/11.1.0', 'oracle_path': '/home/oracle/app/product/11.1.0/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/home/oracle/app/product/11.1.0', 'po_tnsadmindir': '/home/oracle/app/product/11.1.0/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
