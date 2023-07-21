from airflow import DAG
from datetime import datetime

# postgres operator
from airflow.providers.postgres.operators.postgres import PostgresOperator

# http sensor
from airflow.sensors.http_sensor import HttpSensor

# http operator
from airflow.providers.http.operators.http import SimpleHttpOperator

# python operator
from airflow.operators.python import PythonOperator

import json
from pandas import json_normalize


def _process_user(ti):
    user = ti.xcom_pull(task_ids="extract_user")
    user = user['results'][0]
    processed_user = json_normalize({
        'firstname': user['name']['first'],
        'lastname': user['name']['last'],
        'country': user['location']['country'],
        'username': user['login']['username'],
        'password': user['login']['password'],
        'email': user['email']
    })
    processed_user.to_csv('/tmp/processed_user.csv', index=None, header=False)


with DAG(
    dag_id="user_processing",
    schedule_interval="@daily",
    start_date=datetime(2021, 1, 1),
    catchup=False,
) as dag:

    create_table = PostgresOperator(
        task_id="create_table",
        postgres_conn_id="postgres",
        sql="""
            CREATE TABLE IF NOT EXISTS users (
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                country TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL
            );
        """
    )

    is_api_available = HttpSensor(
        task_id="is_api_available",
        http_conn_id="user_api",
        endpoint="api/"
    )

    extract_user = SimpleHttpOperator(
        task_id="extract_user",
        http_conn_id="user_api",
        endpoint="api/",
        method="GET",
        response_filter=lambda response: json.loads(response.text),
        log_response=True
    )

    process_user = PythonOperator(
        task_id="_process_user",
        python_callable=_process_user
    )

    extract_user >> process_user
