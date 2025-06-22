import psycopg2
from datetime import datetime, timedelta

def create_partition():
    try:
        print("Conectando ao banco de dados...")
        conn = psycopg2.connect(
            dbname="dbc",
            user="admin",
            password="admin",
            host="127.0.0.1",
            port=5432
        )
        cursor = conn.cursor()

        today = datetime.today().strftime('%Y-%m-%d')
        yesterday = (datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.today()+timedelta(days=1)).strftime('%Y-%m-%d')

        partition_name = f"inspection_data_fsp_{today.replace('-', '_')}"

        create_partition_sql = f"""
        CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF inspection_data_fsp
        FOR VALUES FROM ('{today} 00:00:00') TO ('{today} 23:59:59');
        """

        print(f"Criando partição: {partition_name}")
        cursor.execute(create_partition_sql)
        conn.commit()
        print(f"Partição {partition_name} criada com sucesso!")

    except Exception as e:
        print(f"Erro ao criar a partição: {e}")
        raise

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == "__main__":
    create_partition()

