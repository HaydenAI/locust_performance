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


class CustomStatsEntry(stats.StatsEntry):
    def __init__(self, request_type, name):
        super().__init__(request_type, name)
        self.total_uploaded_file_size_bits = 0
        self.total_upload_time = 0
        self.current_upload_speed_mbps = 0


# Define a dictionary to store custom request statistics
custom_request_stats = {}


def update_current_upload_speed_stats(request_type, name, file_size_bits, elapsed_time):
    # Calculate the current upload speed in Mbps
    current_upload_speed_mbps = file_size_bits / (elapsed_time * 1_000_000)

    # Get or create the custom stats for the current request
    request_key = (request_type, name)
    custom_stats = custom_request_stats.get(request_key)
    if custom_stats is None:
        custom_stats = {
            'request_type': request_type,
            'name': name,
            'total_uploaded_file_size_bits': 0,
            'total_upload_time': 0,
            'current_upload_speed_mbps': 0,
            'average_upload_speed_mbps': 0,
        }
        custom_request_stats[request_key] = custom_stats

    # Update the CustomStatsEntry object with the current upload speed
    custom_stats['total_uploaded_file_size_bits'] += file_size_bits
    custom_stats['total_upload_time'] += elapsed_time
    custom_stats['current_upload_speed_mbps'] = current_upload_speed_mbps

    # Calculate and update the average upload speed in Mbps
    if custom_stats['total_upload_time'] > 0:
        average_upload_speed_mbps = custom_stats['total_uploaded_file_size_bits'] / (custom_stats['total_upload_time'] * 1_000_000)
        custom_stats['average_upload_speed_mbps'] = average_upload_speed_mbps

    # Print the current upload speed if needed
    # print(f"-----> Current upload speed (Mbps): {current_upload_speed_mbps:.2f}")


class CustomCSVStatsWriter(stats.StatsCSV):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def write_stats(self, file_stream):
        # Call the base class write_stats method to write the standard statistics
        super().write_stats(file_stream)

        # Write the custom statistics to the CSV file
        file_stream.write("Request Type,Name,Total Uploaded File Size (bits),Total Upload Time (s),Current Upload Speed (Mbps),Average Upload Speed (Mbps)\n")
        for key, custom_stats in events.custom_request_stats.items():
            file_stream.write(
                f"{custom_stats['request_type']},{custom_stats['name']},{custom_stats['total_uploaded_file_size_bits']},{custom_stats['total_upload_time']},{custom_stats['current_upload_speed_mbps']:.2f},{custom_stats['average_upload_speed_mbps']:.2f}\n"
            )


# Register the CustomCSVStatsWriter to be used as the StatsCSV writer
stats.CSV_STATS_WRITER = CustomCSVStatsWriter


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
        print(f"-----> Current upload file size: {file_size_bits}")
        # Call the update_current_upload_speed_stats function with the updated stats
        update_current_upload_speed_stats(request_type, name, file_size_bits, elapsed_time)


# @events.request_success.add_listener
# def on_request_success(request_type, name, response_time, response_length, **kwargs):
#     # Check if the response was received successfully (status code 2xx)
#     if 200 <= kwargs['response'].status_code < 300:
#         import pdb
#         pdb.set_trace()
        # Calculate custom_metric1 and custom_metric2 based on the response or any other logic
        # custom_metric1 = calculate_custom_metric1(kwargs['response'])
        # custom_metric2 = calculate_custom_metric2(kwargs['response'])
        #
        # # Update custom metrics for the request in the StatsEntry object
        # stats_entry = kwargs['user'].get_current_task().get_stats(request_type, name)
        # if stats_entry:
        #     stats_entry.custom_metric1 = custom_metric1
        #     stats_entry.custom_metric2 = custom_metric2


# Add a listener to the quitting event to write the average upload speed to the statistics file
@events.quitting.add_listener
def write_average_upload_speed_to_csv(**kwargs):
    if 'environment' not in kwargs:
        print("Error: 'environment' not found in kwargs. Unable to write average upload speed to CSV.")
        return

    environment = kwargs['environment']

    if not hasattr(environment, 'runner') or not hasattr(environment.runner, 'stats'):
        print(
            "Error: 'environment' or 'environment.runner.stats' not found. Unable to write average upload speed to CSV.")
        return

    if total_uploaded_file_size_bits <= 0 or total_upload_time <= 0:
        print("Warning: No valid data to calculate average upload speed. Writing '0' to CSV.")
        average_upload_speed_mbps = 0
    else:
        average_upload_speed_mbps = total_uploaded_file_size_bits / (total_upload_time * 1_000_000)

    runner = environment.runner

    if isinstance(runner, runners.LocalRunner):
        stats_file_path = "/tmp/analysis.csv_stats.csv"
    else:
        custom_stats_writer = runner.stats.get_writer(stats.CSVStats)
        if custom_stats_writer is None:
            print("Error: Custom stats writer not found. Unable to write average upload speed to CSV.")
            return
        stats_file_path = custom_stats_writer.file_stream.name

    # Write the average upload speed to the statistics file
    with open(stats_file_path, 'a') as stats_file:
        stats_file.write(f'Average Upload Speed (Mbps),{average_upload_speed_mbps:.2f}\n')


@events.test_start.add_listener
def _(environment, **kw):
    from locust_performance.s3_bucket_ops import Bucket_ops
    bo = Bucket_ops(local_path='/tmp/ZABCDEFGZ', bash_flow=True)
    # bo.BUCKET_NAME = 'ai-hayden-event-video-staging'
    bo.BUCKET_NAME = 'ai-hayden-event-video-eupilot'
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
                    # bucket_name = "ai-hayden-event-video-staging"
                    bucket_name = "ai-hayden-event-video-eupilot"
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

                events.request.fire(
                    request_type="POST",
                    name="execute_s3_upload",
                    response_time=int((time.time() - start_time) * 1000),
                    response_length=0,
                    **{'local_path': local_path}  # Include local_path in the kwargs
                )
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

