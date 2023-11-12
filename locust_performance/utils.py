# from locust_performance.locustfile import run_locust_programmatically
import builtins
import shutil
import logging
import dpath
import os
from tinydb import TinyDB, Query, where, table
import datetime
import time


import subprocess
import json


def get_queue_size(queue_url):
    '''
    # Replace this with the actual URL of the queue you want to query
    queue_url = "https://sqs.us-west-2.amazonaws.com/744897374265/light-event-processor-queue-staging"

    queue_size = get_queue_size(queue_url)
    print("Approximate number of messages in the queue:", queue_size)
    # get_queue_size('https://sqs.us-west-2.amazonaws.com/744897374265/light-event-processor-queue-staging')
    # get_queue_size('https://sqs.us-west-2.amazonaws.com/744897374265/s3-media-transform-queue-staging')
    # get_queue_size('https://sqs.us-west-2.amazonaws.com/744897374265/match-detector-queue-staging')
    :param queue_url:
    :return:
    '''

    command = ["aws", "sqs", "get-queue-attributes", "--queue-url", queue_url, "--attribute-names", "ApproximateNumberOfMessages"]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        print(f"result.returncode: {result.returncode}")
        if result.returncode == 0:
            output = json.loads(result.stdout)
            mesg_nums = int(output["Attributes"]["ApproximateNumberOfMessages"])
            print(f"{queue_url}: number of messages: {mesg_nums}")
        else:
            print("----> Error:", result.stderr)
    except Exception as e:
        print("Error:", e)


def s3_bucket_operations():
    from s3_bucket_ops import Bucket_ops
    bo = Bucket_ops(local_path='/tmp/ZABCDEFGZ')
    return bo


def get_role_s3_client():
    bucket_op = s3_bucket_operations()
    # bucket_op.BUCKET_NAME = "ai-hayden-event-video-staging"
    # bucket_op.BUCKET_NAME = "ai-hayden-event-video-eupilot"
    builtins.role_s3_client = bucket_op.role_s3_client


def make_get_events_data():
    '''
    assumption:: json table: s3_load_data po[ulated with generated data
    assumption:: table will have single session with data load, rest are empty
    expln:: it works at the moment with single document
    expln:: also returns the data, based on single "session id"
    :return:
    '''
    def get_events_data(ljr):
        session_id = None
        table = ljr.db.table('s3_load_data')
        all_the_data = table.all()
        # session_id = [*all_the_data[0].keys()][0]
        # {[*x.keys()][0]: x for x in all_the_data}
        # [x for x in dpath.util.search(all_the_data, '**', yielded=True) ]
        for item in dpath.search(all_the_data, '**', yielded=True):
            if len([*item[1].values()][0]) > 0:
                session_id = [*item[1].keys()][0]
                break
        assert session_id is not None, 'Failed to find data'
        return [x for x in all_the_data if [*x.keys()][0] == session_id][0].get(session_id)
    local_live_json_results = LiveJasonTestsResults
    ljr = local_live_json_results(table_name="s3_load_data")
    the_data = get_events_data(ljr)

    return the_data


def timestamp_string():
    return datetime.datetime.utcfromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')


class LiveJasonTestsResults:
    '''
    https://www.freecodecamp.org/news/get-started-with-tinydb-in-python/
    '''
    _instance = None

    def __new__(cls, table_name="ublox_ops"):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            # Generate a unique session ID
            cls.table_name = table_name
            cls._instance.session_id = timestamp_string()
        return cls._instance

    def __init__(self, table_name="ublox_ops"):
        if hasattr(self, 'initialized'):
            return
        self.initialized = True
        # self.table_name = table_name
        self.converted_table_data = {}
        self.current_path = os.path.dirname(
            os.path.realpath(__file__))

        self.json_file = os.path.abspath(
            os.path.join('/tmp', 'upgrade_ublox_proc.json')
        )

        self.json_file_backup = os.path.abspath(
            os.path.join(self.current_path, 'config', 'local_db', 'upgrade_ublox_proc_backup.json')
        )

        self.db = TinyDB(self.json_file)
        # if 'ublox_ops' not in self.db.tables():
        if self.table_name == 'ublox_ops':
            self.table = self.db.table('ublox_ops')
        else:
            self.table = self.db.table(self.table_name)

        # Create the table if it doesn't exist
        self.table.insert({self._instance.session_id: {}})

    # def __del__(self):
    #     self.db.close()
    #     self.create_backup()

    # def insert_data_to_live_json(self, data, table_name):
    #     table = self.db.table(table_name)
    #     current_doc = self.db.table(table_name).search(where(self._instance.session_id) != None)
    #     current_doc[0][self._instance.session_id] = data
    def insert_data_to_live_json(self, data, table_name):
        table = self.db.table(table_name)
        current_doc = self.db.table(table_name).search(where(self._instance.session_id) != None)
        current_doc[0][self._instance.session_id] = data

    def convert_table_data(self, table_data):
        for step_name, host_ip, operation_result in zip(table_data['step name'],
                                                        table_data['host ip'], table_data['operation result']):
            if host_ip not in self.converted_table_data:
                self.converted_table_data[host_ip] = {}
            self.converted_table_data[host_ip][step_name] = operation_result

    def get_status_from_previous_session(self, ip, step_name):
        import pdb
        pdb.set_trace()
        # Get the previous session ID
        previous_session_id = str(int(self.table[-1].doc_id) - 1)

        # Retrieve the status from the previous session ID
        try:
            status = self.table.get(where('ublox_ops')[previous_session_id][ip][step_name])
            return status
        except KeyError:
            return None
        else:
            return False

    def update_data(self, ip, test_step, result):
        '''
        ljr.update_data('172.20.20.120',  'install_ublox_helper_on_devices', 'failed')
        The first tuple ('0', {'20230527000737': {}}) represents the path '0' (which corresponds
        to the root level of the JSON data) and its value is {'20230527000737': {}}.
        The second tuple ('0/20230527000737', {}) represents the path '0/20230527000737'
        (which corresponds to the nested level within the JSON data) and its value is {}.
        '''
        # Find the session ID in the table
        session_id = self._instance.session_id
        # all_the_data = self.db.table('ublox_ops').all()
        # all_values_paths = [x for x in dpath.util.search(all_the_data, '**', yielded=True) ]
        # self.table.search(Query().ublox_ops.contains(session_id))
        # Search for documents matching the key
        current_doc = self.db.table('ublox_ops').search(where(session_id) != None)[0]
        current_doc.get(session_id).setdefault(ip, {})[test_step] = result
        self.db.table('ublox_ops').update(current_doc, doc_ids=[current_doc.doc_id])

    def get_data_from_backup(self):
        try:
            # Copy the JSON file to the backup file
            if os.path.exists(self.json_backup_file):
                shutil.copy(self.json_backup_file, self.json_file)
                logging.info(f"Backup created: {self.json_backup_file}")
            else:
                shutil.copy(self.json_file, self.json_backup_file)
        except Exception as e:
            logging.error(f"Error creating backup: {str(e)}")

    def create_backup(self):
        try:
            # Copy the JSON file to the backup file
            shutil.copy(self.json_file, self.json_backup_file)
            print(f"Backup created: {self.json_backup_file}")
        except Exception as e:
            print(f"Error creating backup: {str(e)}")

    def get_status_from_previous_session(self, ip, step_name):
        # Use a query to find the desired IP and step name
        query = Query().ublox_ops.any(lambda session: session[Query()][ip].get(step_name) is not None)
        # self.db.table('ublox_ops').search(Query().field.all)
        # Query().field.all(query | list)
        # Search for documents matching the query
        # expln: gets all the test steps results
        # [x for x in dpath.util.search(self.db.table('ublox_ops').all(), "**/test_step_*", yielded=True)]
        # expln: ('0/20230530171007/172.20.20.120/test_step_97676', {'transfer_and_unzip_upgrade_package': 'passed'}),
        # Query().step_name
        matching_docs = self.table.search(query)
        # Iterate over the matching documents to find the status
        for doc in matching_docs:
            sessions = doc['ublox_ops']
            for session in sessions.values():
                if ip in session and step_name in session[ip]:
                    return session[ip][step_name]  # Return the status of the step

        return None  # Return None if no matching step is found for the IP

    def is_step_passed(self, ip, test_step):
        status = self.get_step_status(ip, test_step)
        if status == 'Passed':
            return True
        else:
            return False


if __name__ == '__main__':
    get_role_s3_client()
    import pdb
    pdb.set_trace()
    builtins.get_events_data = make_get_events_data()
    # builtins.run_locust_programmatically()
    import pdb
    pdb.set_trace()

