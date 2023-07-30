from setuptools import setup, find_packages

setup(
    name='locust_performance',
    version='1.0.0',
    description='A package for Locust performance testing',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/your-username/locust_performance',
    packages=find_packages(),
    install_requires=[
        'boto3==1.28.1',
        'botocore==1.31.1',
        'dpath==2.1.6',
        'locust==2.15.1',
        'tinydb==4.8.0',
        # Add any other dependencies here
    ],
    package_data={
        'locust_performance': ['run_locust.sh'],
    },
    entry_points={
        'console_scripts': [
            'run_performance_tests = locust_performance.driver:run_locust',
        ],
    },
)
