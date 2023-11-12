#!/bin/bash
# run_performance_tests --num-users 10 --spawn-rate 3 --run-time 10
# Set up environment variables
export LOCUST_HOST="http://dummy.host"
# Get the absolute path of the locustfile.py dynamically
LOCUST_LOCUSTFILE=$(python -c "import os; \
                               from locust_performance import locustfile; \
                               print(os.path.abspath(locustfile.__file__)); \
                             ")
echo ">>>>>>>>>> Value of LOCUST_LOCUSTFILE: $LOCUST_LOCUSTFILE"
export LOCUST_NUM_USERS=${1:-9}
export LOCUST_SPAWN_RATE=${2:-2}
export LOCUST_RUN_TIME=${3:-30}
export TARGET_ENVIRONMENT=${4:-'Staging'}
export LOCUST_CSV="/tmp/analysis.csv"
export LOCUST_LOGFILE="/tmp/locust.log"
export LOCUST_LOGLEVEL="DEBUG"
export LOCUST_HEADLESS="True"

echo ">>>>>>>>>> Value of LOCUST_RUN_TIME: $LOCUST_RUN_TIME"
echo ">>>>>>>>>> Value of TARGET_ENVIRONMENT: $TARGET_ENVIRONMENT"

#role_s3c=$(python -c "from locust_performance.s3_bucket_ops import Bucket_ops; \
#                        bo = Bucket_ops(local_path='/tmp/ZABCDEFGZ', bash_flow=True); \
#                        bo.BUCKET_NAME = 'ai-hayden-event-video-staging'; \
#                       print(bo.role_s3_client); \
#                          ")
#echo "Value of bo: $role_s3c"


get_events_data=$(python -c "import locust_performance.utils; \
                            from locust_performance.utils import make_get_events_data; \
                            local_get_events_data = make_get_events_data(); \
                            print(local_get_events_data); \
                          ")


#get_events_data_str=$(echo "$get_events_data" | jq tostring)


echo ">>>>>>>>>> Value of get_events_data: $get_events_data"

#echo ">>>>>>>>>> Value of role_s3c: $role_s3c"

locust -f "$LOCUST_LOCUSTFILE" --the_data "${get_events_data}"

# Remove all the data from s3
#$(python -c "from  s3_bucket_ops import Bucket_ops; \
#            bo = Bucket_ops(local_path='/tmp/'); \
#            bo.remove_files_from_s3(); \
#         ")
