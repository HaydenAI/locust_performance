import subprocess
import os
import argparse
import builtins
try:
    from locust_performance.utils import make_get_events_data
except (ModuleNotFoundError, ImportError):
    from .utils import make_get_events_data

try:
    from locust_performance.s3_bucket_ops import Bucket_ops
except (ModuleNotFoundError, ImportError):
    from .s3_bucket_ops import Bucket_ops
global_args = None


def init_routine():
    parser = argparse.ArgumentParser(description="Run Locust performance tests")
    parser.add_argument('--num-users', dest='num_users', type=int, default=9, help="Number of users")
    parser.add_argument('--spawn-rate', dest='spawn_rate', type=int, default=2, help="User spawn rate")
    parser.add_argument('--run-time', dest='run_time', type=int, default=30, help="Test run time")
    global_args = parser.parse_args()
    builtins.params = {'num_users': global_args.num_users, 'run_time': global_args.run_time, 'spawn_rate': global_args.spawn_rate}


def run_locust(**kwargs):
    num_users = kwargs.get('num_users')
    run_time = kwargs.get('run_time')
    spawn_rate = kwargs.get('spawn_rate')

    # Check that all values are not None
    assert num_users is not None, "num_users cannot be None"
    assert run_time is not None, "run_time cannot be None"
    assert spawn_rate is not None, "spawn_rate cannot be None"

    try:
        script_path = os.path.join(os.path.dirname(__file__), 'run_locust.sh')
        subprocess.run(['bash', script_path, str(num_users), str(spawn_rate), str(run_time)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running 'run_locust.sh': {e}")
    except FileNotFoundError:
        print("'run_locust.sh' file not found.")


def run_locust_manager():
    init_routine()
    run_locust(**builtins.params)


# if __name__ == "__main__":
#     # all_the_data = make_get_events_data()
#     args = init_routine()
#     import pdb
#     pdb.set_trace()
#
#
#
#     # bo = Bucket_ops(local_path='/tmp/')
#     # bo.remove_files_from_s3()
#     # bo.get_role_credentials_proc()
#     run_locust(**builtins.params)
#     import pdb
#     pdb.set_trace()