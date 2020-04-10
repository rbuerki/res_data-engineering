from db_connect import connect, close
from sql_queries import create_table_queries, drop_table_queries


def drop_tables(cur, conn):
    for query in drop_table_queries:
        cur.execute(query)


def create_tables(cur, conn):
    for query in create_table_queries:
        cur.execute(query)


def main():
    cur, conn = connect()
    drop_tables(cur, conn)
    create_tables(cur, conn)
    close()


if __name__ == "__main__":
    main()
