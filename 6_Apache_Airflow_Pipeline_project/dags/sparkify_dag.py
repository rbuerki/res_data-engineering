from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators import (StageToRedshiftOperator,
                               LoadFactOperator,
                               LoadDimensionOperator,
                               DataQualityOperator
                               )
from helpers import SqlQueries, DataChecks

# Note: Credentials are set with Airflow Hooks
# config = configparser.ConfigParser()
# config.read("aws.cfg")
# os.environ["AWS_KEY"] = config["AWS"].get("AWS_ACCESS_KEY_ID")
# os.environ["AWS_SECRET"] = config["AWS"].get("AWS_SECRET_ACCESS_KEY")

# Define DAG

default_args = {
    "owner": "rbuerki",
    "depends_on_past": False,
    'start_date': datetime(2018, 11, 1),
    'end_date': datetime(2018, 11, 2),
    "retries": 5,
    "retry_delay": timedelta(minutes=5),
    "catchup": False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG('sparkify_dag',
          default_args=default_args,
          description='Load and transform data in Redshift with Airflow',
          schedule_interval='0 * * * *'
          )

# Define Tasks

start_operator = DummyOperator(
    task_id='Begin_execution',
    dag=dag
)

stage_events_to_redshift = StageToRedshiftOperator(
    task_id='Stage_events',
    dag=dag,
    provide_context=True,  # not to forget
    table="staging_events",
    redshift_conn_id="redshift",
    aws_credentials_id="aws_credentials",
    s3_bucket="udacity-dend",
    # load data based on execution time only
    s3_key="log_data/{execution_date.year}/{execution_date.month}/{ds}-events.json",
    json_format="'s3://udacity-dend/log_json_path.json'"
)

stage_songs_to_redshift = StageToRedshiftOperator(
    task_id='Stage_songs',
    dag=dag,
    provide_context=True,  # not necessary here
    table="staging_songs",
    redshift_conn_id="redshift",
    aws_credentials_id="aws_credentials",
    s3_bucket="udacity-dend",
    s3_key="song_data/A/A/A/"  # Load only a small subset
)

load_songplays_table = LoadFactOperator(
    task_id='Load_songplays_fact_table',
    dag=dag,
    redshift_conn_id="redshift",
    destination_table="songplays",
    sql_statement=SqlQueries.songplay_table_insert
)

load_user_dimension_table = LoadDimensionOperator(
    task_id='Load_user_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    destination_table="users",
    sql_statement=SqlQueries.user_table_insert,
    update_mode="insert"
)

load_song_dimension_table = LoadDimensionOperator(
    task_id='Load_song_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    destination_table="songs",
    sql_statement=SqlQueries.song_table_insert,
    update_mode="insert"
)

load_artist_dimension_table = LoadDimensionOperator(
    task_id='Load_artist_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    destination_table="artists",
    sql_statement=SqlQueries.artist_table_insert,
    update_mode="insert"
)

load_time_dimension_table = LoadDimensionOperator(
    task_id='Load_time_dim_table',
    dag=dag,
    redshift_conn_id="redshift",
    destination_table="time",
    sql_statement=SqlQueries.time_table_insert,
    update_mode="insert"
)

run_quality_checks = DataQualityOperator(
    task_id='Run_data_quality_checks',
    dag=dag,
    redshift_conn_id="redshift",
    sql_query_list=[DataChecks.empty_table_check,
                    DataChecks.empty_table_check,
                    DataChecks.empty_table_check,
                    DataChecks.songplay_id_check,
                    ],
    table=["staging_events",
           "staging_songs",
           "songplays",
           "",
           ],
    expected_result=[1, 1, 1, 1]
)

end_operator = DummyOperator(
    task_id='Stop_execution',
    dag=dag
)

# Define dependencies

start_operator >> stage_events_to_redshift
start_operator >> stage_songs_to_redshift
stage_events_to_redshift >> load_songplays_table
stage_songs_to_redshift >> load_songplays_table
load_songplays_table >> load_song_dimension_table
load_songplays_table >> load_user_dimension_table
load_songplays_table >> load_artist_dimension_table
load_songplays_table >> load_time_dimension_table
load_song_dimension_table >> run_quality_checks
load_user_dimension_table >> run_quality_checks
load_artist_dimension_table >> run_quality_checks
load_time_dimension_table >> run_quality_checks
run_quality_checks >> end_operator
