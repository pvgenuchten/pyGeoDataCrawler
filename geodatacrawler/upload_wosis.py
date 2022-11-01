#!/usr/bin/env python3.9
#coding:utf-8


import pandas as pd
import os
import sqlalchemy as sa
from pathlib import Path,PurePath
import psycopg2
import subprocess
import unidecode
import sys

## File cloned from https://git.wur.nl/isric/databases/wosis/-/blob/master/etl_scripts/1_upload.py

def collect_extensions(root, skip_dataset, extensions):
    for i in root.glob('**/*'):
        pth = PurePath(i)
        if pth.name not in skip_dataset:
            dataset = identifier_from_filename(i)
            if i.suffix not in extensions:
                extensions.append(i.suffix)
    print('\nThe following file extensions were found: \n', extensions, '\n for dataset `' + dataset + '`.')
    return(extensions)


def clean_file_name(file_name, dataset_name):
    file_name = file_name.translate({ord(i):None for i in '!@#$^&*()+={}[]|\/;:,.<>?'})
    file_name = unidecode.unidecode(file_name)
    file_name = file_name.replace(' ','_')
    file_name = file_name.replace('-','_')
    file_name = file_name.replace('–', '_')
    file_name = file_name.replace('___', '_')
    file_name = file_name.replace('__', '_')
    file_name = file_name.lstrip('_')
    file_name = file_name.rstrip('_')
    file_name = file_name.lstrip()
    file_name = file_name.rstrip()
    if dataset_name[3:] in file_name:
        file_name = file_name.replace(dataset_name[3:], '')
    return(file_name)


def clean_sheet_name(dataset_name, file_name, sheet_name):
    sheet_name = sheet_name.lower()
    sheet_name = sheet_name.translate({ord(i):None for i in '!@#$^&*()+={}[]|\/;:,.<>?'})
    sheet_name = unidecode.unidecode(sheet_name)
    sheet_name = sheet_name.replace(' ', '_')
    sheet_name = sheet_name.replace('-', '_')
    sheet_name = sheet_name.replace('–', '_')
    sheet_name = sheet_name.replace('__', '_')
    sheet_name = sheet_name.lstrip('_')
    sheet_name = sheet_name.rstrip('_')
    sheet_name = sheet_name.lstrip()
    sheet_name = sheet_name.rstrip()
    if dataset_name[3:] in sheet_name:
        sheet_name = sheet_name.replace(dataset_name[3:], '')
    if file_name in sheet_name:
        sheet_name = sheet_name.replace(file_name, '')
    if sheet_name in file_name:
        sheet_name = ''
    return(sheet_name)
    

def clean_table_name(table_name):
    table_name = table_name.lower()
    table_name = table_name.translate({ord(i):None for i in '!@#$^&*()+={}[]|\/;:,.<>?'})
    table_name = unidecode.unidecode(table_name)
    table_name = table_name.replace(' ', '_')
    table_name = table_name.replace('-', '_')
    table_name = table_name.replace('–', '_')
    table_name = table_name.replace('__', '_')
    table_name = table_name[:63]
    table_name = table_name.lstrip('_')
    table_name = table_name.rstrip('_')
    table_name = table_name.lstrip()
    table_name = table_name.rstrip()
    return(table_name)


def clean_column_name(df):
    df.columns = df.columns.str.lower()
    df.columns = df.columns.str.translate({ord(i):None for i in '!@#$^&*()+={}[]|\/;:,.<>?'})
    #df.columns = df.columns.str.apply(unidecode.unidecode)
    df.columns = df.columns.str.replace('%', '_perc')
    df.columns = df.columns.str.replace('µm', '_micrometer')
    df.columns = df.columns.str.replace('°', '_deg')
    df.columns = df.columns.str.replace(' ', '_')
    df.columns = df.columns.str.replace('-', '_')
    df.columns = df.columns.str.replace('–', '_')
    df.columns = df.columns.str.replace('___', '_')
    df.columns = df.columns.str.replace('__', '_')
    df.columns = df.columns.str.lstrip('_')
    df.columns = df.columns.str.rstrip('_')
    df.columns = df.columns.str.lstrip()
    df.columns = df.columns.str.rstrip()
    return(df)


def reset_schema(schema,cur):
    # TODO this should be at the end of the import process, not here.
    sql = 'DROP SCHEMA IF EXISTS %s CASCADE;' %schema
    cur.execute(sql)
    sql = 'CREATE SCHEMA %s AUTHORIZATION isric_admin;' %schema
    cur.execute(sql)
    sql = "COMMENT ON SCHEMA %s IS 'Source datasets to be ingested in WoSIS in 2020';" %schema
    cur.execute(sql)
    sql = 'GRANT USAGE ON SCHEMA %s TO wosis_w;' %schema
    cur.execute(sql)
    sql = 'GRANT ALL ON SCHEMA %s TO wosis_r;' %schema
    cur.execute(sql)


def sql_grant_on_table(schema, table_name, cur):
    sql = 'ALTER TABLE %s.%s OWNER TO isric_admin;' %(schema, table_name)
    cur.execute(sql)
    sql = 'GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE %s.%s TO wosis_w;' %(schema, table_name)
    cur.execute(sql)
    sql = 'GRANT SELECT ON TABLE %s.%s TO wosis_r;' %(schema, table_name)
    cur.execute(sql)


def convert_to_sql(root,skip_dataset,skip_file,schema,cur,engine,encoding):
    
    # reset schema, should be done at the end of the last script.
    #reset_schema(schema,cur)
    #conn.commit()
    
    for i in root.glob('**/*'):
        dataset = identifier_from_filename(i)
        if dataset not in skip_dataset:
            #print(i)
            sql = "INSERT INTO wosis_etl.upload_dataset (dataset_id) VALUES('%s') ON CONFLICT (dataset_id) DO NOTHING RETURNING id;" %dataset
            cur.execute(sql)
            # Lets get the dataset id because this insert can run multiples times if the dataset already exists. 
            sql = "SELECT id FROM wosis_etl.upload_dataset WHERE dataset_id='%s'" %dataset
            cur.execute(sql)
            upload_dataset_id=cur.fetchone()[0]
            dataset_name = dataset.replace('-','_').lower()
            
            # Excel files
            if i.suffix in ['.xls','.xlsx'] and i.name not in skip_file:
                #print(i)
                
                # clean file_name
                file_name = clean_file_name(i.stem.lower(), dataset_name)
                
                xls = pd.ExcelFile(i)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(i, sheet)
                    
                    # clean column names
                    clean_column_name(df)
                    
                    # clean sheet_name
                    sheet_name = clean_sheet_name(dataset_name, file_name, sheet)
                    
                    # clean table_name
                    table_name = clean_table_name(dataset_name + '_' + file_name + '_' + sheet_name)
                    
                    # to sql
                    print('Dataset: %15s | Format: %5s | File: %50s | Sheet: %15s | Database: %63s' %(dataset[:15], i.suffix[1:], i.name[:50], sheet[:15], table_name))
                    sql = "INSERT INTO wosis_etl.upload_dataset_table (dataset_id, table_name, ud_id) VALUES('%s','%s','%s') ON CONFLICT DO NOTHING;" %(dataset,table_name,upload_dataset_id)
                    cur.execute(sql)
                    df.to_sql(table_name, engine, schema = '%s' % schema, if_exists = 'replace', index=False)
                    
                    # sql grant
                    sql_grant_on_table(schema, table_name,cur)
                    #conn.commit()
                    
            
            # CSV like files
            if i.suffix in ['.csv','.ssv','.tsv','.tab'] and i.name not in skip_file:
                
                if i.suffix in ['.tsv','.tab']:
                    df = pd.read_csv(i, sep='\t', encoding = encoding, engine='python')
                elif i.suffix in ['.ssv']:
                    df = pd.read_csv(i, sep=';', encoding = encoding, engine='python')
                else:
                    df = pd.read_csv(i, encoding = encoding, engine='python')
                
                # clean column names
                clean_column_name(df)
                
                # clean file_name
                file_name = clean_file_name(i.stem.lower(), dataset_name)
                
                # clean table_name
                table_name = clean_table_name(dataset_name + '_' + file_name)
                
                # to sql
                print('Dataset: %15s | Format: %5s | File: %75s | Database: %63s' %(dataset[:15], i.suffix[1:], i.name[:75], table_name))
                sql = "INSERT INTO wosis_etl.upload_dataset_table (dataset_id, table_name, ud_id) VALUES('%s','%s','%s') ON CONFLICT DO NOTHING;" %(dataset,table_name,upload_dataset_id)
                cur.execute(sql)
                df.to_sql(table_name, engine, schema = '%s' % schema, if_exists = 'replace', index=False)
                    
                # sql grant
                sql_grant_on_table(schema, table_name,cur)
                #conn.commit()
            
            
            # Access files
            if i.suffix in ['.accdb','.mdb'] and i.name not in skip_file:
                #print(i)
                
                # read tables in mdb files
                text = subprocess.check_output("mdb-tables" + ''' -d "," -t table %s''' %i, shell=True)
                text = str(text).split(',')
                text.pop()
                
                for t in text:
                    t = str(t).replace("b'","")
                    
                    # clean file_name
                    file_name = clean_file_name(i.stem.lower(), dataset_name)
                    
                    # clean table_name
                    table_name = clean_table_name(dataset_name + '_' + file_name + '_' + t)
                    table_name = table_name.replace("b'","")
                    print('Dataset: %15s | Format: %5s | File: %50s | Table: %15s | Database: %63s' %(dataset[:15], i.suffix[1:], i.name[:50], t[:15], table_name))
                    sql = "INSERT INTO wosis_etl.upload_dataset_table (dataset_id, table_name, ud_id) VALUES('%s','%s','%s') ON CONFLICT DO NOTHING;" %(dataset,table_name,upload_dataset_id)
                    cur.execute(sql)
                    
                    # drop table
                    sql = 'DROP TABLE IF EXISTS %s.%s;' %(schema, table_name)
                    cur.execute(sql)
                    
                    # create table
                    sql = subprocess.check_output("mdb-schema" + ''' -T "%s" %s''' %(t, i), shell=True)
                    sql = str(sql).replace("b'","")
                    sql = sql.replace('\\n','\n')
                    sql = sql.replace('\\t','\t')
                    sql = sql.replace("'","")
                    sql = sql.replace('[','')
                    sql = sql.replace(']','')
                    sql = sql.replace('ORDER ','"order "')
                    sql = sql.replace('ORDER','"order"')
                    sql = sql.replace('Text (','varchar (')
                    sql = sql.replace('DateTime','text')
                    sql = sql.replace('Memo/Hyperlink','varchar')
                    sql = sql.replace("Double","float")
                    sql = sql.replace("Single","Real")
                    sql = sql.replace("Long Integer","integer")
                    sql = sql.replace("Byte","smallint")
                    sql = sql.replace("Boolean","smallint")
                    sql = sql.replace("Binary","bytea")
                    sql = sql.replace('varchar (255)','text')
                    sql = sql.replace('varchar (510)','text')
                    sql = sql.replace('''CREATE TABLE %s''' %t,"CREATE TABLE IF NOT EXISTS %s.%s" %(schema, table_name))
                    cur.execute(sql)
                    
                    # extract access data
                    subprocess.call("mdb-export" + ''' -H -Q -d "\t" -b strip %s "%s" > /tmp/export_%s.csv''' %(i, t, table_name), shell=True)
                    
                    # to sql
                    sql = '''COPY %s.%s FROM '/tmp/export_%s.csv' WITH NULL AS '';''' %(schema, table_name, table_name)
                    sql = sql.replace("b'","")
                    cur.execute(sql)
                    
                    # grant & commit
                    sql_grant_on_table(schema, table_name,cur)
                    #conn.commit()


def identifier_from_filename(str):
    pth = PurePath(str)
    return clean_file_name(pth.stem.lower(), pth.parent.name+'_'+pth.name)

def convert_to_sql_exceptions(schema, exceptions,cur):
    for i in exceptions:
        i = Path(i)
        dataset = identifier_from_filename(i)
        dataset_name = dataset
                        
        # clean file_name
        file_name = clean_file_name(i.stem.lower(), dataset_name)

        # clean table_name
        table_name = clean_table_name(dataset_name + '_' + file_name + '_1col')
        
        # to sql, entire row in one column
        print('Dataset: %15s | Format: %5s | File: %75s | Database: %63s' %(dataset[:15], i.suffix[1:], i.name[:75], table_name))
        sql = 'DROP TABLE IF EXISTS %s.%s;' %(schema, table_name)
        cur.execute(sql)
        sql = 'CREATE TABLE %s.%s (txt text);' %(schema, table_name)
        cur.execute(sql)
        sql = "COPY %s.%s FROM '%s' (FORMAT csv, ENCODING 'utf8', DELIMITER E'\b');"  %(schema, table_name, i)
        cur.execute(sql)
        sql = "INSERT INTO wosis_etl.upload_dataset_table (dataset_id, table_name) VALUES('%s','%s') ON CONFLICT DO NOTHING;" %(dataset,table_name)
        cur.execute(sql)
        
        # grant & commit
        sql_grant_on_table(schema, table_name,cur)
        #conn.commit()


def main(dbname='mydatabase', input_folder='', user='postgres', password='mypassword', host='localhost', port='5432', skip_dataset=[], extensions=['csv','shp'], skip_file=[], exceptions=[], schema='wosis_upload',encoding="ISO-8859-1"):
    root = Path(input_folder)
    print((host, dbname, user, password, port))
    # database connection
    conn = psycopg2.connect("""host='%s' dbname='%s' user='%s' password='%s' port='%s'""" % (host, dbname, user, password, port))
    #conn = psycopg2.connect("host='ppostgres12.cdbe.wurnet.nl' dbname='pisric' user='myusername' password='mypassword' sslmode='require'")
    cur = conn.cursor()
    # for sqlalchemy
    #dsn = "postgresql://{%s}:{%s}@{%s}/{%s}" %(user,pswd,host,dbname)
    dsn = "postgresql://{user}:{passwd}@{host}:{port}/{db}".format(user=user, passwd=password, host=host, db=dbname, port=port)
    engine = sa.create_engine(dsn)


    # Setup schema for data standerization
    #
    # At the begining (or perhaps even better at the end) of each batch we must truncate tables started with upload (4 tables)
    # Dont truncate these tables if this script is running at the middle of the batch because 
    # Niels works on wosis_etl.upload_dataset_table_column
    #
    # sql_file = open('/Users/lcalisto/Documents/gitRepos/ISRIC/ISRIC_database/wosis/rapid-stream/isric_db_wosis_upload_setup.sql','r')
    # cur.execute(sql_file.read())

    #TODO check if we insert wosis.dataset now or in second script. INSERT INTO wosis.dataset
    collect_extensions(root,skip_dataset, extensions)
    convert_to_sql(root,skip_dataset,skip_file,schema,cur,engine,encoding)
    convert_to_sql_exceptions(schema, exceptions,cur)
    # Populate table upload_dataset_table_column
    sql = """
    INSERT INTO wosis_etl.upload_dataset_table_column (dataset_id, table_name, column_name)
    SELECT d.dataset_id, i.table_name, i.column_name
                FROM information_schema.columns i
                LEFT JOIN wosis_etl.upload_dataset_table d 
                    ON d.table_name = i.table_name
                WHERE table_schema='%s'
                AND  is_updatable = 'YES'
                AND dataset_id is not null ON CONFLICT DO NOTHING;

    ----- Update upload_dataset_table_column fkey
    UPDATE wosis_etl.upload_dataset_table_column as udtc
    SET udt_id = udt.id
    from wosis_etl.upload_dataset_table as udt
    where udtc.dataset_id=udt.dataset_id
    and udtc.table_name=udt.table_name;

    ----- Update upload_dataset_table_column_changes fkey
    UPDATE wosis_etl.upload_dataset_table_column_changes as udtcc
    SET udtc_id = udtc.id
    from wosis_etl.upload_dataset_table_column as udtc
    where udtcc.dataset_id=udtc.dataset_id
    and udtcc.table_name=udtc.table_name
    and udtcc.column_name=udtc.column_name;

    """ %schema
    cur.execute(sql)
    print(cur.statusmessage)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Execute when the module is not initialized from an import statement.
    input_folder='/Users/lcalisto/Documents/gitRepos/ISRIC/Soils4Africa/s4a-data-shop/arc.agric.za/samples-south-africa/'
    dbname = 's4a_datashop'
    user='postgres'
    password='postgis'
    host='localhost'
    encoding = "ISO-8859-1"
    skip_dataset = ['WD-SOLEX-MIR','CA-SDPOLT','AF-AfSIS-MIR','.DS_Store']
    extensions = ['csv','shp']
    skip_file = ['ICPF_level01_coordinates.mdb','.DS_Store']
    exceptions = []
    sys.exit(main(dbname,input_folder,user,password,host,skip_dataset,extensions,skip_file,exceptions))
