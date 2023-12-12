import re
import os
import json
import traceback
import urllib.parse
import boto3
from datetime import datetime
import time
from smart_search_dataload import SmartSearchDataload

EMBEDDING_ENDPOINT_NAME = os.environ.get('embedding_endpoint_name')
host =  os.environ.get('host')
index =  os.environ.get('index')
region = os.environ.get('AWS_REGION')
language = os.environ.get('language')
search_engine_opensearch = True if str(os.environ.get('search_engine_opensearch')).lower() == 'true' else False
search_engine_zilliz = True if str(os.environ.get('search_engine_zilliz')).lower() == 'true' else False
zilliz_endpoint = os.environ.get('zilliz_endpoint')
zilliz_token = os.environ.get('zilliz_token')

port = 443
bulk_size = 10000000

# retrieve secret manager value by key using boto3                                             
sm_client = boto3.client('secretsmanager')
master_user = sm_client.get_secret_value(SecretId='opensearch-master-user')['SecretString']
data= json.loads(master_user)
username = data.get('username')
password = data.get('password')

s3_res = boto3.resource('s3')
s3_cli = boto3.client('s3')

def get_string_after_source_data(text):
    match = re.search(r'source_data/(.+)/(.+)', text)
    if match:
        index = match.group(1) 
        print(f"uploading to index {index}")
        return index
    else:
        return None

def lambda_handler(event, context):
    
    print("event:",event)
    print("host:",host)
    print("region:",region)
    print("language:",language)
    print("username:",username)
    print("password:",password)
    print("search_engine_zilliz:", search_engine_zilliz)
    print("zilliz_endpoint:", zilliz_endpoint)
    print("zilliz_token:", zilliz_token)

    searchEngine = "opensearch"
    if not search_engine_opensearch and search_engine_zilliz:
        searchEngine = "zilliz"
    print('searchEngine:', searchEngine)
    
    #try:
    #    dataload = SmartSearchDataload()
    #    dataload.init_cfg(index,
    #                     username,
    #                     password,
    #                     host,
    #                     port,
    #                     EMBEDDING_ENDPOINT_NAME,
    #                     region,
    #                     language=language
    #                     )
    #                 
    #
    #    bucket_name = event['Records'][0]['s3']['bucket']['name']
    #    file_name = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    #    local_file = "{}/{}".format('/tmp', file_name.split("/")[-1])
    
    #   print("bucket_name:",bucket_name)
    #    print("file_name:",file_name)
    #    print("local_file:",local_file)
    
    try:
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_name = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        local_file = "{}/{}".format('/tmp', file_name.split("/")[-1])
        index = get_string_after_source_data(file_name)
        if not index:
            index =  os.environ.get('index')

        print("bucket_name:",bucket_name)
        print("file_name:",file_name)
        print("index:",index)
        print("local_file:",local_file)

        dataload = SmartSearchDataload()
        dataload.init_cfg(index,
                         username,
                         password,
                         host,
                         port,
                         EMBEDDING_ENDPOINT_NAME,
                         region,
                         searchEngine,
                         zilliz_endpoint,
                         zilliz_token,
                         language=language
                         )
        
        size = int(event['Records'][0]['s3']['object']['size'])
        loaded_files = []
        if size > 0:    
            s3_cli.download_file(Bucket=bucket_name,
                             Key=file_name,
                             Filename=local_file
                             )
            print("finish download file")
        
            now1 = datetime.now()#begin time
            loaded_files = dataload.init_knowledge_vector(local_file,bulk_size)
            now2 = datetime.now()#endtime
            print("File import takes time:",now2-now1)
            print("Complete the import of the following documents:", str(loaded_files))
        
        else:
            print("Empty file")
        
        response = {
            "statusCode": 200,
            "headers": {
                    "Access-Control-Allow-Origin": '*'
                },
                "isBase64Encoded": False
        }
            
        response['body'] = json.dumps(
        {
            'datetime':time.time(),
            'loaded_files': loaded_files
            
        })
        
        print("response:",response)
        return response
        
    except Exception as e:
        traceback.print_exc()
        return {
            'statusCode': 400,
            'body': str(e)
        }
