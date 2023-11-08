import os
import sys
import boto3
from boto3 import Session
import threading
import glob
import datetime
import time
import datetime
import logging
import json
import random
# import pytest
from pathlib import Path
from botocore.exceptions import ClientError

# from automation.testdir.conftest import get_input_parameters
# import polling
import configparser
# from automation.utils.utils_prop import Utils
# from automation.bootstrap.bootstrap_helper import Configuration
'''
https://binaryguy.tech/aws/s3/quickest-ways-to-list-files-in-s3-bucket/
'''


class Bucket_ops:
    def __init__(self, local_path,
                 aws_access_key_id=None,
                 aws_secret_access_key_id=None,
                 logging=None, bash_flow=None):
        '''
        Feb_2021/
        upload
        :param local_path:
        :param s3_dir:
        '''
        # TODO::add active profile check
        # self.session = None
        # self.mc = Configuration()
        # self.current_profile = self.mc.parse_cmd_line().__dict__.get('profile')
        self.current_profile = 'eu_pilot'
        # cred_obj = self.session.get_credentials()
        # s3_client = boto3.client('s3', region_name="us-west-2", session_token=self.session)
        # s3_client.list_buckets()
        # self.session = boto3.Session(profile_name="Staging") - worked
        # s3_client = self.session.client('s3')
        '''
        session = boto3.Session( aws_access_key_id=cred_obj.access_key, aws_secret_access_key=cred_obj.secret_key, aws_session_token=cred_obj.token )
        '''
        if self.current_profile:
            self.session = boto3.Session(profile_name=self.current_profile, region_name='us-west-2')

            self.s3_resource = self.session.resource('s3', region_name='us-west-2')
            self.AWS_ACCESS_KEY_ID = None
            self.AWS_SECRET_ACCESS_KEY = None
        else:
            if aws_access_key_id is None:
                self.AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
            else:
                self.AWS_ACCESS_KEY_ID = aws_access_key_id
            if aws_secret_access_key_id is None:
                self.AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
            else:
                self.AWS_SECRET_ACCESS_KEY = aws_secret_access_key_id
            self.s3_resource = boto3.resource('s3', region_name='us-west-2', aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                                              aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)
            self.session = boto3.Session(
                aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)
        self.parsed_sso_data = None
        # session = boto3.Session()
        # active_profile = session.profile_name
        # print("Active Profile:", active_profile)
        self.REGION = 'us-west-2'
        # if aws_access_key_id is None:
        #     self.AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
        # else:
        #     self.AWS_ACCESS_KEY_ID = aws_access_key_id
        # if aws_secret_access_key_id is None:
        #     self.AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
        # else:
        #     self.AWS_SECRET_ACCESS_KEY = aws_secret_access_key_id
        self.local_config_profiles = {}
        self.sso_client = None
        self.local_path = local_path
        self.file_name = Path(self.local_path).parts[-1]
        # self.BUCKET_NAME = 'ai-hayden-vpn-device-beta'
        self.BUCKET_NAME = 'ai-hayden-iat-reports-beta'
        self.s3_dir = None
        self.local_path_list = []
        self.current_path = os.path.dirname(os.path.realpath(__file__))
        self.parent_directory = os.path.abspath(os.path.join(self.current_path, os.pardir))
        self.shared_json = os.path.abspath(os.path.join(self.parent_directory, 'config', 'shared.json'))
        # self.current_date = datetime.datetime.utcfromtimestamp(time.time()).strftime('%Y%m%d::%H%M%S')
        # self.current_date ='20220213::061415/'

        # if self.session:
        #     self.s3_resource = self.session.resource(
        #         's3',
        #         region_name=self.REGION,
        #         aws_access_key_id=self.AWS_ACCESS_KEY_ID,
        #         aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY
        #     )
        # else:
        #     self.s3_resource = boto3.resource(
        #         's3',
        #         region_name=self.REGION,
        #         aws_access_key_id=self.AWS_ACCESS_KEY_ID,
        #         aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY
        #     )

        # self.destination_path = 's3://ai-hayden-vpn-device-beta/remove-device/'
        # self.folder_path_tmplt = 'clinical/cchtouch/deliverables/test_upload/{current_date}'
        # self.remove_device_path = "remove-device"
        # s3client = self.s3_resource.meta.client
        # s3client.list_objects(Bucket=self.BUCKET_NAME, Prefix='', Delimiter="/")
        # s3client.list_parts(Bucket=self.BUCKET_NAME, Key=self.folder_path)
        # s3client.list_objects_v2(Bucket=self.BUCKET_NAME, Prefix='test_upload', MaxKeys=1000)
        # self.session = boto3.Session(
        #     aws_access_key_id=self.AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)

        # Then use the session to get the resource
        # self.s3session = self.session.resource('s3')
        # self.my_bucket = self.s3session.Bucket(self.BUCKET_NAME)
        self.uploaded_files = []
        self.s3client = self.s3_resource.meta.client
        # response = self.s3client.list_objects_v2(Bucket=self.BUCKET_NAME)
        # files = response.get("Contents")
        self.verification_data = {}

        self.paginator = self.s3client.get_paginator('list_objects')
        self.list_of_prefixes = None
        self.all_the_sub_dirs = None
        self.all_sub_dirs = None
        self.dir_counter = 0
        self.downloaded_file_path = None
        self.dir_data = {}
        self.s3_page_data = {}
        self.folder_path = None
        self.role_credentials = None
        self.staging_profile = None
        self.role_session = None
        self.role_s3_client = None

        # self.local_live_json_results = live_json_results()
        # self.ljr = self.local_live_json_results(table_name="s3_load_data")
        self.the_data = None

        # if self.mc.parse_cmd_line().__dict__.get('flow_name') == 'load_test' or self.bash_flow:
        # todo::refactor to separate flow method -------------
        self.parse_aws_config_file('~/.aws/config')
        self.staging_profile = self.local_config_profiles.get('profile eu_pilot')
        self.parse_latest_sso_file('~/.aws/sso/cache')
        self.get_role_credentials_proc()
        # expln::self.role_credentials becomes available now
        # Create a new session using the role credentials
        self.role_session = boto3.Session(
            aws_access_key_id=self.role_credentials.get('accessKeyId'),
            aws_secret_access_key=self.role_credentials.get('secretAccessKey'),
            aws_session_token=self.role_credentials.get('sessionToken'),
            region_name=self.staging_profile.get('region')
        )

        self.role_s3_client = self.role_session.client('s3')
        #
        # import pdb
        # pdb.set_trace()

        # bucket_name = "ai-hayden-event-video-staging"
        # object_key = "raw/85128058-4904-44d5-bb50-47d69d1d4679/1420122246609/2023-07-03/97e056fd-33e4-bba3-3f85-2d2b79922d7d.jpg"
        # # self.role_s3_client.put_object(Body=f, Bucket=bucket_name, Key=object_key)
        # # expln::put object to Staging
        # with open("/tmp/load_data/97e056fd-33e4-bba3-3f85-2d2b79922d7d/97e056fd-33e4-bba3-3f85-2d2b79922d7d.jpg", 'rb') as file:
        #     import pdb
        #     pdb.set_trace()
        #     self.role_s3_client.put_object(Body=file, Bucket=bucket_name, Key=object_key)
        # expln::remove object from Staging
        # response = self.role_s3_client.list_objects_v2(Bucket=bucket_name, Prefix=object_key)
        '''
        {'ResponseMetadata': {'RequestId': '7XMS4N27XMTTNDKE', 'HostId': 'p/BtWbTp7wPG86SKkbIV2Vns5dvqz7yueL3fKWiHlTdYCyZ9nqquiFbUu68PIzhWEtFjoqS5It0=', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amz-id-2': 'p/BtWbTp7wPG86SKkbIV2Vns5dvqz7yueL3fKWiHlTdYCyZ9nqquiFbUu68PIzhWEtFjoqS5It0=', 'x-amz-request-id': '7XMS4N27XMTTNDKE', 'date': 'Tue, 27 Jun 2023 22:56:03 GMT', 'x-amz-bucket-region': 'us-west-2', 'content-type': 'application/xml', 'transfer-encoding': 'chunked', 'server': 'AmazonS3'}, 'RetryAttempts': 0}, 'IsTruncated': False, 'Contents': [{'Key': 'raw/85128058-4904-44d5-bb50-47d69d1d4679/1420122528548/2023-06-27/3523cc0d-f593-2096-fd37-234c49f822e6-gps.ublox', 'LastModified': datetime.datetime(2023, 6, 27, 22, 26, 22, tzinfo=tzutc()), 'ETag': '"e785710b07dbb8b302aa408d58341e18"', 'Size': 67564, 'StorageClass': 'STANDARD'}], 'Name': 'ai-hayden-event-video-staging', 'Prefix': 'raw/85128058-4904-44d5-bb50-47d69d1d4679/1420122528548/2023-06-27/3523cc0d-f593-2096-fd37-234c49f822e6-gps.ublox', 'MaxKeys': 1000, 'EncodingType': 'url', 'KeyCount': 1}
        '''
        # todo::refactor to separate flow method -------------
        # self.pages = self.paginator.paginate(Bucket=self.BUCKET_NAME, Prefix=self.folder_path)

    # def create_role_s3_client(self):
    #     self.parse_aws_config_file('~/.aws/config')
    #     self.staging_profile = self.local_config_profiles.get('profile Staging')
    #     self.parse_latest_sso_file('~/.aws/sso/cache')
    #     self.get_role_credentials_proc()
    #     # expln::self.role_credentials becomes available now
    #     # Create a new session using the role credentials
    #     self.role_session = boto3.Session(
    #         aws_access_key_id=self.role_credentials.get('accessKeyId'),
    #         aws_secret_access_key=self.role_credentials.get('secretAccessKey'),
    #         aws_session_token=self.role_credentials.get('sessionToken'),
    #         region_name=self.staging_profile.get('region')
    #     )
    #     self.role_s3_client = self.role_session.client('s3')

    # def get_events_data(self):
    #     '''
    #     assumption:: table will have single session with data load, rest are empty
    #     expln:: it works at the moment with single document
    #     expln:: also returns the data, based on single "session id"
    #     :return:
    #     '''
    #     session_id = None
    #     table = self.ljr.db.table('s3_load_data')
    #     all_the_data = table.all()
    #     # session_id = [*all_the_data[0].keys()][0]
    #     # {[*x.keys()][0]: x for x in all_the_data}
    #     # [x for x in dpath.util.search(all_the_data, '**', yielded=True) ]
    #     for item in dpath.util.search(all_the_data, '**', yielded=True):
    #         if len([*item[1].values()][0]) > 0:
    #             session_id = [*item[1].keys()][0]
    #             break
    #     assert session_id is not None, 'Failed to find data'
    #     return [x for x in all_the_data if [*x.keys()][0] == session_id][0].get(session_id)

    def remove_files_from_s3(self):
        # https://docs.aws.amazon.com/AmazonS3/latest/userguide/example_s3_PutObject_section.html
        # implementation goes here
        # Upload the file to the S3 bucket
        from utils import make_get_events_data
        self.the_data = make_get_events_data()
        for event_id in [*self.the_data.keys()][:5]:
            for i in range(0, len(self.the_data.get(event_id)), 2):
                object_key = self.the_data.get(event_id)[i]
                local_path = self.the_data.get(event_id)[i+1].get('file_path')
                logging.info(f"object_key: {object_key}")
                logging.info(f"local_path: {local_path}")

                # bucket_name = "ai-hayden-event-video-staging"
                bucket_name = "ai-hayden-event-video-eupilot"
                if self.check_object_exists(bucket_name, object_key):
                    logging.info(f"removing object: {object_key}")
                    self.role_s3_client.delete_object(Bucket=bucket_name, Key=object_key)
                else:
                    logging.info(f"object doesn't exists in s3: {object_key}")

    def check_object_exists(self, bucket_name: str, object_key: str) -> bool:
        try:
            response = self.role_s3_client.head_object(Bucket=bucket_name, Key=object_key)
            # If the object exists, the 'head_object' method will succeed and return the response.
            # If the object does not exist, it will raise a 'botocore.exceptions.ClientError'.
            # In this case, we assume the object does not exist and return False.
            return True
        except self.role_s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False

    def set_profile(self, profile_name):
        self.current_profile = profile_name

    def get_role_credentials_proc(self):
        '''
        function works currently only with --- Staging --- environment
        :return:
        '''
        self.sso_client = boto3.client('sso')
        response = self.sso_client.get_role_credentials(
            roleName=self.staging_profile.get('sso_role_name'),
            accountId=self.staging_profile.get('sso_account_id'),
            accessToken=self.parsed_sso_data.get('accessToken')
        )
        '''
        response:
         [*response.get('roleCredentials').keys()]
         ['accessKeyId', 'secretAccessKey', 'sessionToken', 'expiration']
        '''
        assert response.get('roleCredentials'), 'Failed to get correct response from sso_client.get_role_credentials'
        self.role_credentials = response.get('roleCredentials')

    def parse_aws_config_file(self, config_file):
        # Create a ConfigParser object
        config = configparser.ConfigParser()

        # Read the AWS config file
        config.read(os.path.expanduser(config_file))

        # Extract the profiles and their corresponding properties
        # Iterate over each section in the config file
        for section in config.sections():
            profile_name = section.strip()

            # Skip the 'default' section
            if profile_name.lower() == 'default':
                continue

            # Extract the properties for the current profile
            properties = {}
            for key, value in config.items(section):
                properties[key.strip()] = value.strip()

            # Store the profile properties in the dictionary
            self.local_config_profiles[profile_name] = properties


    def parse_latest_sso_file(self, directory):
        '''
        # Usage
        directory = '/Users/vadimkhaskel/.aws/sso/cache'
        parsed_data = parse_latest_sso_file(directory)

        # Access the parsed data
        start_url = parsed_data['startUrl']
        region = parsed_data['region']
        expires_at = parsed_data['expiresAt']
        registration_expires_at = parsed_data['registrationExpiresAt']
        '''
        current_time = datetime.datetime.utcnow()
        # Get a list of all files in the directory
        files = os.listdir(os.path.expanduser(directory))

        # Filter out non-JSON files
        json_files = [f for f in files if f.endswith('.json')]

        # Sort the JSON files by modification time in descending order
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(os.path.expanduser(directory), x)), reverse=True)

        # Retrieve the path of the latest JSON file
        latest_file_path = os.path.join(os.path.expanduser(directory), json_files[0])

        # Read the content of the latest JSON file
        with open(latest_file_path, 'r') as file:
            content = file.read()

        # Parse the JSON content into a dictionary
        self.parsed_sso_data = json.loads(content)
        expiration_time = datetime.datetime.strptime(self.parsed_sso_data['expiresAt'], '%Y-%m-%dT%H:%M:%SZ')
        assert current_time < expiration_time, '*** user needs to login to sso, authorization expired ***'
        # Set the AWS accessible environment variables
        os.environ['AWS_ACCESS_KEY_ID'] = self.parsed_sso_data['clientId']
        os.environ['AWS_SECRET_ACCESS_KEY'] = self.parsed_sso_data['clientSecret']
        os.environ['AWS_SESSION_TOKEN'] = self.parsed_sso_data['accessToken']




    def paginate_through_all_objects_s3_bucket(self, max_items=1000, page_size=10, starting_token=None, new_prefix=None):
        '''
        data=self.paginate_through_all_objects_s3_bucket(max_items=2, page_size=5, new_prefix='Bx12_Bx41_FAT_DATA/Bus_5538')
        :param max_items:
        :param page_size:
        :param starting_token:
        :return:
        '''
        try:
            # new_prefix = next(self.all_the_sub_dirs)
            response = self.paginator.paginate(Bucket=self.BUCKET_NAME, Prefix=new_prefix,
                                               PaginationConfig={
                                                   'MaxItems': max_items,
                                                   'PageSize': page_size,
                                                   'StartingToken': starting_token}
                                               )
            return response
        except ClientError as e:
            raise Exception("boto3 client error in paginate_through_all_objects_s3_bucket: " + e.__str__())
        except Exception as e:
            raise Exception("Unexpected error in paginate_through_all_objects_s3_bucket: " + e.__str__())

    def get_bucket_prefixes(self, prefix=None, get_global_data=None, get_number_of_devices=None):
        if prefix is None:
            results = self.paginator.paginate(Bucket=self.BUCKET_NAME, Delimiter='/',
                                              PaginationConfig={
                                                       'MaxItems': 300,
                                                       'PageSize': 300})
        data = [x for x in results]
        if get_global_data is None:
            self.list_of_prefixes = random.sample(data[0].get("CommonPrefixes"), 1)
        elif get_number_of_devices:
            self.list_of_prefixes = data[0].get("CommonPrefixes")[:get_number_of_devices]
        else:
            device_id = get_global_data('portal_ota_devices_device_id')
            self.list_of_prefixes = [x for x in data[0].get("CommonPrefixes") if x.get('Prefix').strip('/') == device_id]
            assert self.list_of_prefixes, f'Unable to find appropriate bucket: {device_id} in AWS s3'
        # self.list_of_prefixes = data[0].get('CommonPrefixes')

    def get_sub_dirs(self):
        """ Yield direct child folders of the given prefix.
        (Pdb) response = self.s3client.list_objects_v2(Bucket=self.BUCKET_NAME)
        (Pdb) files = response.get("Contents")
        (Pdb) [x for x in files]
        """
        sub_dirs = []
        # response = self.paginator.paginate(Bucket=self.BUCKET_NAME, PaginationConfig={"PageSize": 2})
        # [x.get("Contents") for x in response]
        results = self.paginator.paginate(Bucket=self.BUCKET_NAME, Prefix=self.folder_path, Delimiter='/')
        for result in results:
            for prefix in result.get('CommonPrefixes', []):
                # Prefixes look like "<prefix>/<subdir>/"
                # This code replaces "<prefix>/" with an empty
                # space leaving "<subdir>" from the common prefix.
                # yield prefix['Prefix'].replace(prefix, '', 1).strip('/')
                self.dir_counter += 1
                sub_dirs.append(prefix.get('Prefix'))
        self.all_the_sub_dirs = iter(sub_dirs)
        self.all_sub_dirs = sub_dirs

    def list_s3_files_using_paginator(self, prefix):
        """
        This functions list all files in s3 using paginator.
        Paginator is useful when you have 1000s of files in S3.
        S3 list_objects_v2 can list at max 1000 files in one go.
        :return: None
        """
        output = []
        if self.session:
            s3_client = self.session.client("s3")
        else:
            s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")
        response = paginator.paginate(Bucket=self.BUCKET_NAME, Prefix=prefix, PaginationConfig={"PageSize": 1000,
                                                                                                'MaxItems': 1000})

        for page in response:
            # print("getting 2 files from S3")
            files = page.get("Contents")
            # max(sorted(files), key=lambda x: x['LastModified'])
            # all_sorted = sorted(files.items(), key=lambda t: t.get('Key').split('/')[1])
            for file in files:
                # print(f"file_name: {file['Key']}, size: {file['Size']}")
                output.append(file['Key'])
            # print("#" * 10)
        return output

    def get_latest_s3_file_using_paginator(self, prefix):
        """
        This functions list all files in s3 using paginator.
        Paginator is useful when you have 1000s of files in S3.
        S3 list_objects_v2 can list at max 1000 files in one go.
        :return: None
        """
        output = []
        if self.session:
            s3_client = self.session.client("s3")
        else:
            s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")
        response = paginator.paginate(Bucket=self.BUCKET_NAME, Prefix=prefix, PaginationConfig={"PageSize": 1000,
                                                                                                'MaxItems': 1000})

        for page in response:
            # print("getting 2 files from S3")
            files = page.get("Contents")

            latest_file_struct = max(files, key=lambda x: x['LastModified'])
            return latest_file_struct.get('Key')

    def poll_s3_file(self):
        """
        This functions list all files in s3 using paginator.
        Paginator is useful when you have 1000s of files in S3.
        S3 list_objects_v2 can list at max 1000 files in one go.
        :return: None
        """
        my_bucket = self.s3_resource.Bucket(self.BUCKET_NAME)

        # def get_uploaded_file():
        #     for my_file in my_bucket.objects.filter(Prefix='ccd/1421821014174'):
        #         file_name = my_file.key
        #         #if file_name.find("1421020009618") == -1:
        #     print("returning False")
        #     return True
        #
        # polling.poll(
        #     lambda: get_uploaded_file(),
        #     ignore_exceptions=(polling.TimeoutException,),
        #     step=1,
        #     poll_forever=True)

    def get_all_data_by_directory_step(self):
        '''
        returns list of iterrators
        :param:
        :return: ds which returns uploaded files with zero size
        '''
        max_items = 30
        page_size = 5
        file_counter = -1
        num_of_dirs = [x for x in range(1, self.dir_counter+1)]
        for dir in self.all_sub_dirs:
            b = self.paginate_through_all_objects_s3_bucket(max_items=max_items,
                                                            page_size=page_size)
            self.dir_data[os.path.basename(os.path.dirname(dir))] = b

    def upload_file_to_remove_device_folder(self):
        self.s3_resource.Bucket(self.BUCKET_NAME).upload_file(self.local_path,
                                                              "{destination_s3dir}/{file_name}".format(
                                                                  destination_s3dir=self.remove_device_path,
                                                                  file_name=self.file_name))

    # def download_event_set_from_s3_folder(self, file_paths):
    #     '''
    #     https://boto3.amazonaws.com/v1/documentation/api/1.9.42/guide/s3-example-download-file.html
    #     :return:
    #     This is a Python function that downloads files from an Amazon S3 bucket using the Boto3 library.
    #      The function takes a list of file paths as an argument and returns the downloaded file.
    #     The function first defines a nested function, get_current_uuid, which takes a list of file paths
    #      and extracts a unique identifier for the current set of files being downloaded.
    #      The function iterates through the file paths, filters out certain sections based on the file
    #      extension, and returns the UUID.
    #     The main function then creates a temporary directory to store the downloaded files using
    #     the tempfile and pathlib libraries. It calls the get_current_uuid function to get the
    #     UUID for the current set of files, creates a directory with that UUID, and iterates through a
    #     list of prefixes that specify the location of the files in the S3 bucket.
    #     '''
    #     def get_current_uuid(file_paths):
    #         ext = ["mp4", "jpg", "jsonl", "ublox", "json"]
    #         filter_out_section = ["alpr", "gps", "ji", "lp"]
    #         file_names = []
    #         for file_path in file_paths:
    #             if file_path.split('/')[-1].split('-')[-1].split('.')[0] in filter_out_section:
    #                 uuid = "-".join(file_path.split('/')[-1].split('-')[:-1])
    #             elif file_path.split('/')[-1].split('-')[-1].split('.')[1] in ext:
    #                 uuid = "-".join(
    #                     file_path.split('/')[-1].split('-')[:-1] + [file_path.split('/')[-1].split('-')[-1].split('.')[0]])
    #         return uuid
    #
    #     device_ids = []
    #     import tempfile, pathlib
    #     dirpath = tempfile.mkdtemp()
    #     current_uuid = get_current_uuid(file_paths)
    #     logging.info(f'current_uuid {current_uuid} extracted')
    #     the_dir = pathlib.Path(dirpath)
    #     self.local_path = the_dir / current_uuid
    #     Path(str(self.local_path)).mkdir()
    #     # device_id_dict = self.list_of_prefixes[0]
    #     for prefix in self.list_of_prefixes:
    #         self.local_path = f"/tmp/{current_uuid}"
    #         '''
    #         data holds multiple names of downloaded reports
    #         '''
    #         # data = self.get_latest_s3_file_using_paginator(device_id)
    #         # assert data, f'Failed to retrieve information form s3 bucket {self.BUCKET_NAME}/{device_id}'
    #         latest_file_name = prefix.split('/')[-1]
    #         self.local_path = the_dir / current_uuid / latest_file_name
    #         Path(str(self.local_path)).touch()
    #
    #         bucket = self.s3_resource.Bucket(f'{self.BUCKET_NAME}')
    #         obj = bucket.Object(f'{prefix}')
    #         '''
    #         At this point downloaded file will be in the location (self.local_path) similar to
    #         /var/folders/z5/r6dj01j54x33c855y9x7d8s40000gn/T/tmp3flurvzx/1420122039883/Fri_Oct__7_2022_00:21:09.pdf
    #         '''
    #         self.local_path_list.append(str(self.local_path))
    #         with open(self.local_path, 'wb') as data:
    #             obj.download_fileobj(data)
    #     pytest.global_data['global_data']['downloaded_event_data'] = self.local_path_list
    #     # pytest.global_data['global_data']['device_id'] = device_ids


if __name__ == "__main__":
    bo = Bucket_ops(local_path='/tmp/')
    bo.remove_files_from_s3()
    # bo.get_role_credentials_proc()
    import pdb
    pdb.set_trace()


    # aws_data = {'aws_access_key_id': 'xxx',
    #             'aws_secret_access_key': 'xxx', 'region': "'us-west-2'"}
    # bo = Bucket_ops(local_path='/tmp/',
    #                 aws_access_key_id=aws_data.get('aws_access_key_id'),
    #                 aws_secret_access_key_id=aws_data.get('aws_secret_access_key'))
    # bo.BUCKET_NAME = "field-testing-records"
    # bo.get_bucket_prefixes()
    # bo.list_s3_files_using_paginator("Bx12_Bx41_FAT_DATA/Bus_5539")
    # s3://field-testing-records/Bx12_Bx41_FAT_DATA/  /Bx12_Bx41_FAT_DATA/Bus_5539/
    # C:\Users\jino>aws s3 ls s3://field-testing-records/Bx12_Bx41_FAT_DATA/
    # bo.create_current_dated_directory()
    # bo.upload_directory()
    # bo.get_all_uploaded_files()
    # bo.get_sub_dirs()
    # bo.list_s3_files_using_paginator()
    # bo.get_all_data_by_directory_step()
    # bo.verification_step()
    # bo.upload_file_to_remove_device_folder()
    # bo.poll_s3_file()
    # bo.download_file_from_s3_folder()


