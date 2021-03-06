import configparser
from datetime import datetime
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, monotonically_increasing_id
from pyspark.sql.functions import (year,
                                   month,
                                   dayofmonth,
                                   hour,
                                   weekofyear,
                                   dayofweek,
                                   )
from pyspark.sql.types import TimestampType
from schemas import song_data_schema, log_data_schema


config = configparser.ConfigParser()
config.read("dl.cfg")

os.environ["AWS_ACCESS_KEY_ID"] = config["AWS"].get("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = config["AWS"].get("AWS_SECRET_ACCESS_KEY")


def create_spark_session():
    """Creates as Spark Session"""
    spark = SparkSession \
        .builder \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:2.7.0") \
        .getOrCreate()
    return spark


def process_song_data(spark, input_data, output_data):
    """Process song data from S3, generate song and artist data.

    Parameters
    ----------
    spark : SparkSession object
    input_data : string
        S3 URI for song data input
    output_data : string
        S3 URI for song and artist data output
    """

    # Get filepath to song data file and read into dataframe
    song_data = os.path.join(input_data, "song-data", "*", "*", "*", "*.json")
    df = spark.read.json(song_data, schema=song_data_schema)
    # Extract columns to create songs table
    songs_table = df.select("song_id",
                            "title",
                            "artist_id",
                            "year",
                            "duration",
                            ).drop_duplicates()

    # Write songs table to parquet files partitioned by year and artist
    songs_table.write.parquet(
        os.path.join(output_data, "songs_table.parquet"),
        mode="overwrite",
        partitionBy=["year", "artist_id"]
    )

    # Extract columns to create artists table
    artists_table = df.select("artist_id",
                              col("artist_name").alias("name"),
                              col("artist_location").alias("location"),
                              col("artist_latitude").alias("latitude"),
                              col("artist_longitude").alias("longitude")
                              ).drop_duplicates()

    # Write artists table to parquet files
    artists_table.write.parquet(
        os.path.join(output_data, "artists_table.parquet"),
        mode="overwrite"
    )


def process_log_data(spark, input_data, output_data):
    """Process song data from S3, generate users, time and songplays data.

    Parameters
    ----------
    spark : SparkSession object
    input_data : string
        S3 URI for song data input
    output_data : string
        S3 URI for song and artist data output
    """

    # Get filepath to log data file and read into dataframe
    log_data = os.path.join(input_data, "log-data", "*", "*", "*.json")
    df = spark.read.json(log_data, schema=log_data_schema)
    # Filter by actions for song plays
    df = df.filter(col("page") == "NextSong")

    # Extract columns for users table
    users_table = df.select(col("userId").alias("user_id"),
                            col("firstName").alias("first_name"),
                            col("lastName").alias("last_name"),
                            "gender",
                            "level"
                            ).drop_duplicates(["user_id"])

    # Write users table to parquet files
    users_table.write.parquet(
        os.path.join(output_data, "users_table.parquet"),
        mode="overwrite",
    )

    # Create datetime column from original timestamp column
    get_datetime = udf(lambda x: datetime.utcfromtimestamp(x / 1000),
                       TimestampType()
                       )

    df = df.withColumn("start_time", get_datetime("ts"))

    # Extract columns to create time table
    time_table = (df
                  .withColumn("hour", hour("start_time"))
                  .withColumn("day", dayofmonth("start_time"))
                  .withColumn("week", weekofyear("start_time"))
                  .withColumn("month", month("start_time"))
                  .withColumn("year", year("start_time"))
                  .withColumn("weekday", dayofweek("start_time"))
                  .select("start_time",
                          "hour",
                          "day",
                          "week",
                          "month",
                          "year",
                          "weekday"
                          ).drop_duplicates(["year",
                                             "month",
                                             "day",
                                             "hour"]
                                            )
                  )

    # Write time table to parquet files partitioned by year and month
    time_table.write.parquet(
        os.path.join(output_data, "time_table.parquet"),
        mode="overwrite",
        partitionBy=["year", "month"]
    )

    # Read in song data to use for songplays table
    artists_df = spark.read.parquet(
        os.path.join(output_data, "artists_table.parquet")
    )

    songs_df = spark.read.parquet(
        os.path.join(output_data, "songs_table.parquet")
    )

    # Extract columns from joined song and log datasets to create songplays table
    songs = (songs_df
             .join(artists_df, "artist_id", "inner")
             .select("song_id",
                     "title",
                     "artist_id",
                     col("name").alias("artist_name"),
                     "duration"
                     )
             ).drop_duplicates()

    songplays_table = (df
                       .join(songs,
                             [df.song == songs.title,
                              df.artist == songs.artist_name,
                              df.length == songs.duration
                              ], "left")
                       )

    songplays_table = (songplays_table
                       .select(monotonically_increasing_id().alias("songplay_id"),
                               "start_time",
                               col("userId").alias("user_id"),
                               "level",
                               "song_id",
                               "artist_id",
                               col("sessionId").alias("session_id"),
                               "location",
                               col("userAgent").alias("user_agent"),
                               month("start_time").alias("month"),
                               year("start_time").alias("year")
                               )
                       )

    # Write songplays table to parquet files partitioned by year and month
    songplays_table.write.parquet(
        os.path.join(output_data, "songplays_table.parquet"),
        mode="overwrite",
        partitionBy=["year", "month"]
    )


def main():
    """Runs ETL pipeline job."""

    spark = create_spark_session()
    input_data = "s3a://udacity-dend/"
    output_data = "s3a://sparkify-bucket-output/"

    process_song_data(spark, input_data, output_data)
    process_log_data(spark, input_data, output_data)


if __name__ == "__main__":
    main()
