#!/usr/bin/env python3
#coding:utf-8

import sys
import os
import getopt
import psycopg2
import json
import yaml

# import current wosis upload script. A replacement is needed since this file was not designed for this.
from upload_wosis import main as wosis_etl_upload

def export_config(output_file='./config.json', dbname='mydatabase', user='postgres', password='mypassword', host='localhost', port='5432'):
    """Function that exports into a json file the config parameters using the sql function wosis_etl.export_mapping()


    Args:
        output_file (str): _description_
        dbname (str, optional): _description_. Defaults to 'mydatabase'.
        user (str, optional): _description_. Defaults to 'postgres'.
        password (str, optional): _description_. Defaults to 'mypassword'.
        host (str, optional): _description_. Defaults to 'localhost'.
    """
    conn = psycopg2.connect("""host='%s' dbname='%s' user='%s' password='%s' port='%s'""" % (host, dbname, user, password, port))
    cur = conn.cursor()
    # https://github.com/psycopg/psycopg2/issues/172 cast json as text to prevent python parsing
    sql = """SELECT cast(wosis_etl.export_mapping() as text) as jsonconfig;"""
    try:
        cur.execute(sql)
    except Exception as e:
        conn.close()
        exit('Error while running SQL export function.',e)
    config_json_result=json.loads(cur.fetchone()[0])
    filename, file_extension = os.path.splitext(output_file)
    with open(output_file, "w") as outfile:
        if (file_extension in ['.yml','.yaml']):
            yaml.dump(config_json_result, outfile, indent=2)
        else:
            json.dump(config_json_result, outfile)
    conn.close()

def import_config(input_file='./config.json', dbname='mydatabase', user='postgres', password='mypassword', host='localhost', port='5432'):
    """Function that exports into a json file the config parameters using the sql function wosis_etl.import_mapping()

    Args:
        input_file (str, optional): _description_. Defaults to './config.json'.
        dbname (str, optional): _description_. Defaults to 'mydatabase'.
        user (str, optional): _description_. Defaults to 'postgres'.
        password (str, optional): _description_. Defaults to 'mypassword'.
        host (str, optional): _description_. Defaults to 'localhost'.
    """

    conn = psycopg2.connect("""host='%s' dbname='%s' user='%s' password='%s' port='%s'""" % (host, dbname, user, password, port))

    filename, file_extension = os.path.splitext(input_file)
    config_file = open(input_file, "r")

    if (file_extension in ['.yml','.yaml']):
        with open(config_file, "r") as stream:
            try:
                data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("Error importing: ", config_file, exc)
    else:
        f = open(config_file)
        data  = json.load(f)
        f.close()
    cur = conn.cursor()
    sql = """SELECT wosis_etl.import_mapping('%s') as jsonconfig;"""%(json.dumps(data))
    try:
        cur.execute(sql)
    except Exception as e:
        conn.close()
        exit('Error while running SQL import function.',e)
    config_json_result=cur.fetchone()
    conn.commit()
    conn.close()


def main(argv):
    """
    This function performs 3 actions:
    1. Assuming an existing database already exists, Imports data into ETL (current wosis ETL model) 
        generating all internal tables and configuration and at the same time exports the configuration into a json file. 
        When uploading data a json config file will be generated afterwards. 
        There is no need to export config file after data upload since a json config file is always generated after upload.
    2. Exports configuration into a json file from Wosis ETL config tables.
    3. Imports configuration from a json file into Wosis ETL config tables.

    Usage:
        1. ./upload.py -c config.json -u postgres -d s4a_datashop -H localhost -p password -P 5432  -i samples-20220418 --upload-data
        2. ./upload.py -c config.json -u postgres -d s4a_datashop -H localhost -p password -P 5432 --export-config
        3. ./upload.py -c config.json -u postgres -d s4a_datashop -H localhost -p password -P 5432 --import-config

    Args:
        argv (_type_): _description_
    """
    arg_input_folder = ""
    arg_config_file = "./config.json"
    arg_user = ""
    arg_dbname = ""
    arg_host = ""
    arg_password = ""
    arg_port = "5432"
    arg_upload_data = False
    arg_import_config = False
    arg_export_config = False
    arg_help = "{0} -c <config file> -u <user> -d <dbname> -H <host> -p <password> -P <port> -i <input data folder> --upload-data --import-config --export-config".format(argv[0])

    opts, args = getopt.getopt(argv[1:], "hc:u:d:H:p:P:i:U:I:E", ["help", "config-file=", "user=", "dbname=", "host=", "password=", "port=", "input-data-folder=", "upload-data", "import-config", "export-config"])
    
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(arg_help)  # print the help message
            sys.exit(2)
        elif opt in ("-i", "--input"):
            arg_input_folder = arg
        elif opt in ("-c", "--config"):
            arg_config_file = arg
        elif opt in ("-u", "--user"):
            arg_user = arg
        elif opt in ("-d", "--dbname"):
            arg_dbname = arg
        elif opt in ("-H", "--host"):
            arg_host = arg
        elif opt in ("-p", "--password"):
            arg_password = arg
        elif opt in ("-P", "--port"):
            arg_port = arg
        elif opt in ("-U","--upload-data"):
            arg_upload_data = True
        elif opt in ("-I","--import-config"):
            arg_import_config = True
        elif opt in ("-E","--export-config"):
            arg_export_config = True
    if arg_upload_data:
        try:
            wosis_etl_upload(arg_dbname, arg_input_folder, arg_user, arg_password, arg_host, arg_port)
        except:
            exit('Error while running Wosis ETL upload.')
        export_config(arg_config_file, dbname=arg_dbname, user=arg_user, password=arg_password, host=arg_host, port=arg_port)
    elif arg_export_config:
        export_config(arg_config_file, dbname=arg_dbname, user=arg_user, password=arg_password, host=arg_host, port=arg_port)
    elif arg_import_config:
        import_config(arg_config_file, dbname=arg_dbname, user=arg_user, password=arg_password, host=arg_host, port=arg_port)
    
if __name__ == "__main__":
    main(sys.argv)