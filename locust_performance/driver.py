import subprocess
import os
try:
    from locust_performance.utils import make_get_events_data
except (ModuleNotFoundError, ImportError):
    from .utils import make_get_events_data

try:
    from locust_performance.s3_bucket_ops import Bucket_ops
except (ModuleNotFoundError, ImportError):
    from .s3_bucket_ops import Bucket_ops


def run_locust():
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'run_locust.sh')
        subprocess.run(['bash', script_path], check=True)
        # script_path = os.path.join(os.path.dirname(__file__), 'run_locust.sh')
        # subprocess.run(['ls -l', f'{script_path}'], check=True)
        # loc = subprocess.run(['pwd'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running 'run_locust.sh': {e}")
    except FileNotFoundError:
        print("'run_locust.sh' file not found.")

# Call the run_locust() function to execute the shell script
#run_locust()


if __name__ == "__main__":
    all_the_data = make_get_events_data()
    import pdb
    pdb.set_trace()
    bo = Bucket_ops(local_path='/tmp/')
    # bo.remove_files_from_s3()
    # bo.get_role_credentials_proc()
    run_locust()
    import pdb
    pdb.set_trace()