#from locust import HttpUser, task, between
import ast
import logging
import botocore
import time
import queue
import hashlib

import os
# import invokust
# Define the S3 bucket details
# bucket_name = 'your-bucket-name'
# https://docs.locust.io/en/stable/configuration.html#running-without-the-web-ui
# https://stackoverflow.com/questions/46397580/how-to-invoke-locust-tests-programmatically
# https://www.tesena.com/en/how-to-tame-your-locusts-or-performance-testing-with-locustio
# @events.request_success.add_listener, @events.request_failure.add_listener
# https://www.appsloveworld.com/amazon-s3/24/example-for-using-locust-with-boto3
# bo = Bucket_ops(local_path='/tmp/')
# local_get_role_s3_client = get_role_s3_client()
# from locust_performance.utils import make_get_events_data
# import pdb
# pdb.set_trace()
# import importlib
# locust = importlib.import_module("locust")

from locust import User, between, TaskSet, task, events, runners, main, stats

import builtins
total_upload_time = 0
total_uploaded_file_size_bits = 0


@events.init_command_line_parser.add_listener
def _(parser):
    # parser.add_argument("--role_s3_client", type=str, env_var="ROLE_S3_CLIENT", default="", help="It's working")
    parser.add_argument("--the_data", type=str, env_var="the_data", default="", help="It's working")


class CustomCSVStatsWriter(stats.StatsCSV):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.average_upload_speed_mbps = 0

    def write_stats(self, file_stream):
        # Call the base class write_stats method to write the standard statistics
        super().write_stats(file_stream)

        # Write the average upload speed to the CSV file
        file_stream.write(f'Average Upload Speed (Mbps),{self.average_upload_speed_mbps:.2f}\n')


# Add a listener to the request_success event to calculate the average upload speed
@events.request.add_listener
def on_request_success(request_type, name, response_time, response_length, **kwargs):
    # Calculate the elapsed_time from the response_time provided by the event
    elapsed_time = response_time / 1000.0  # Convert to seconds

    # Calculate the size of the file in bits
    local_path = kwargs.get('local_path')
    if local_path:
        file_size_bytes = os.path.getsize(local_path)
        file_size_bits = file_size_bytes * 8

        # Update global variables with the upload time and file size
        global total_upload_time
        global total_uploaded_file_size_bits
        total_upload_time += elapsed_time
        total_uploaded_file_size_bits += file_size_bits


# Add a listener to the quitting event to write the average upload speed to the statistics file
@events.quitting.add_listener
def write_average_upload_speed_to_csv(**kwargs):
    if 'environment' in kwargs:
        environment = kwargs['environment']
        if hasattr(environment.runner.stats, 'entries') and total_uploaded_file_size_bits > 0 and total_upload_time > 0:
            average_upload_speed_mbps = total_uploaded_file_size_bits / (total_upload_time * 1_000_000)
        else:
            average_upload_speed_mbps = 0

        # Get the Runner object from the Environment
        runner = environment.runner

        # Check if we are using LocalRunner or MasterLocustRunner
        if isinstance(runner, runners.LocalRunner):
            # If using LocalRunner, use the default CSV file path
            stats_file_path = "/tmp/analysis.csv_stats.csv"
        else:
            # If using MasterLocustRunner, use the custom stats writer instance
            custom_stats_writer = runner.stats.get_writer(stats.CSVStats)
            stats_file_path = custom_stats_writer.file_stream.name

        # Write the average upload speed to the statistics file
        with open(stats_file_path, 'a') as stats_file:
            stats_file.write(f'Average Upload Speed (Mbps),{average_upload_speed_mbps:.2f}\n')


# Global variables to store the total upload time and total uploaded file size in bits
total_upload_time = 0
total_uploaded_file_size_bits = 0


@events.test_start.add_listener
def _(environment, **kw):
    from s3_bucket_ops import Bucket_ops
    bo = Bucket_ops(local_path='/tmp/ZABCDEFGZ', bash_flow=True)
    bo.BUCKET_NAME = 'ai-hayden-event-video-staging'
    # print(bo.role_s3_client)
    # print(f"-----> Custom argument supplied: {type(environment.parsed_options.role_s3_client)}")
    # print(f"-----> Custom argument: type of the_data: {type(ast.literal_eval(environment.parsed_options.the_data))}")
    # globals()['local_role_s3_client'] = environment.parsed_options.role_s3_client
    globals()['local_role_s3_client'] = bo.role_s3_client
    globals()['the_data'] = ast.literal_eval(environment.parsed_options.the_data)

# globals()['local_role_s3_client'] = bo.role_s3_client
# globals()['the_data'] = builtins.the_data


def execute_upload(f, bucket_name, object_key):
    try:
        globals()['local_role_s3_client'].put_object(Body=f, Bucket=bucket_name, Key=object_key)
    except botocore.exceptions.ClientError as e:
        logging.error(f'failed: {e}')


class S3LoaderClient:
    '''
    The s3 client loader that wraps the actual query
    '''

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                res = execute_upload(*args, **kwargs)
                events.request.fire(request_type="POST",
                                            name=name,
                                            response_time=int((time.time() - start_time) * 1000),
                                            response_length=0)
            except Exception as e:
                events.request.fire(request_type="POST",
                                            name=name,
                                            response_time=int((time.time() - start_time) * 1000),
                                            exception=e)

                print('error {}'.format(e))

        return wrapper


class S3LoaderTaskSet(TaskSet):

    def on_start(self):
        # Initialize the queue with events data
        self.event_queue = queue.Queue()
        for event_id, event_data in globals()['the_data'].items():
            for i in range(0, len(event_data), 2):
                object_key = event_data[i]
                local_path = event_data[i + 1]['file_path']
                self.event_queue.put((event_id, object_key, local_path))

        # Initialize a set to keep track of the files uploaded by this client
        self.uploaded_files = set()

    @task(1)
    def execute_s3_upload(self):
        # Get the next event and upload data to S3
        try:
            event_id, object_key, local_path = self.event_queue.get_nowait()
            file_id = f"{event_id}-{object_key}"
            if file_id not in self.uploaded_files:
                with open(local_path, 'rb') as f:
                    bucket_name = "ai-hayden-event-video-staging"
                    start_time = time.time()
                    self.client.execute_upload(f, bucket_name, object_key)
                    end_time = time.time()
                    elapsed_time = end_time - start_time

                    # Calculate the size of the file in bits
                    file_size_bytes = os.path.getsize(local_path)
                    file_size_bits = file_size_bytes * 8

                    # Update global variables with the upload time and file size
                    global total_upload_time
                    global total_uploaded_file_size_bits
                    total_upload_time += elapsed_time
                    total_uploaded_file_size_bits += file_size_bits

                    # Introduce a fixed delay to achieve a stable upload speed
                    target_upload_speed_mbps = 30.0  # Adjust this value to set the desired upload speed
                    target_upload_time = file_size_bits / (target_upload_speed_mbps * 1_000_000)
                    fixed_delay = max(0, target_upload_time - elapsed_time)
                    time.sleep(fixed_delay)

                # Add the file_id to the set to mark it as uploaded
                self.uploaded_files.add(file_id)

                # Introduce a fixed delay to achieve a stable upload speed
                target_upload_speed_mbps = 30.0  # Adjust this value to set the desired upload speed
                target_upload_time = file_size_bits / (target_upload_speed_mbps * 1_000_000)
                fixed_delay = max(0, target_upload_time - elapsed_time)
                time.sleep(fixed_delay)

        except queue.Empty:
            # If the queue is empty, all events are uploaded
            pass


class S3LoaderLocust(User):
    wait_time = between(0, 0)
    tasks = [S3LoaderTaskSet]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = S3LoaderClient()


# def run_locust_programmatically():
#     # Set up the environment variables
#     os.environ["LOCUST_HOST"] = "http://dummy.host"
#     os.environ["LOCUST_LOCUSTFILE"] = "/Users/vadimkhaskel/Development/locust_performance/locust_performance/locustfile.py"
#     os.environ["LOCUST_NUM_USERS"] = "2"
#     os.environ["LOCUST_SPAWN_RATE"] = "1"
#     os.environ["LOCUST_RUN_TIME"] = "15"
#     os.environ["LOCUST_CSV"] = "/tmp/analysis.csv"
#     os.environ["LOCUST_LOGFILE"] = "/tmp/locust.log"
#     os.environ["LOCUST_LOGLEVEL"] = "DEBUG"
#     os.environ["LOCUST_HEADLESS"] = "True"
#
#     # Load Locust settings
#     main.main()
#
#     # Create a Locust runner
#     runner = runners.MasterLocustRunner()
#
#     # Set Locust options
#     options = runner.options
#     options.num_users = int(os.environ["LOCUST_NUM_USERS"])
#     options.spawn_rate = int(os.environ["LOCUST_SPAWN_RATE"])
#     options.run_time = os.environ["LOCUST_RUN_TIME"]
#     options.csvfile = os.environ["LOCUST_CSV"]
#     options.logfile = os.environ["LOCUST_LOGFILE"]
#     options.loglevel = os.environ["LOCUST_LOGLEVEL"]
#     options.headless = os.environ.get("LOCUST_HEADLESS", "").lower() == "true"
#
#     # Start the test
#     events.init.fire()
#     runner.start(options.num_users, options.spawn_rate)

