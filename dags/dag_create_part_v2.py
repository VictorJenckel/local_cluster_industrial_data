import sys
import os
import psycopg2
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator



def create_partition():
    """
    Função para criar partição diária da tabela inspection_data
    """
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

        tomorrow = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        partition_name = f"inspection_data_eagle_1_{tomorrow.replace('-', '_')}"

        create_partition_sql = f"""
        CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF inspection_data_eagle1
        FOR VALUES FROM ('{tomorrow} 00:00:00') TO ('{tomorrow} 23:59:59');
        """

        print(f"Criando partição: {partition_name}")
        cursor.execute(create_partition_sql)
        conn.commit()
        print(f"Partição {partition_name} criada com sucesso!")



        partition_name1 = f"inspection_data_eagle_2_{tomorrow.replace('-', '_')}"

        create_partition_sql = f"""
        CREATE TABLE IF NOT EXISTS {partition_name1} PARTITION OF inspection_data_eagle2
        FOR VALUES FROM ('{tomorrow} 00:00:00') TO ('{tomorrow} 23:59:59');
        """

        print(f"Criando partição: {partition_name1}")
        cursor.execute(create_partition_sql)
        conn.commit()
        print(f"Partição {partition_name1} criada com sucesso!")



        partition_name2 = f"inspection_data_fsp_{tomorrow.replace('-', '_')}"

        create_partition_sql = f"""
        CREATE TABLE IF NOT EXISTS {partition_name2} PARTITION OF inspection_data_fsp
        FOR VALUES FROM ('{tomorrow} 00:00:00') TO ('{tomorrow} 23:59:59');
        """

        print(f"Criando partição: {partition_name2}")
        cursor.execute(create_partition_sql)
        conn.commit()
        print(f"Partição {partition_name2} criada com sucesso!")

    except Exception as e:
        print(f"Erro ao criar a partição: {e}")
        raise


      
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Configurações padrão da DAG
default_args = {
    "owner": "Victor_jenckel",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Definição da DAG
with DAG(
    "create_partitions",
    default_args=default_args,
    description="Criação diária de partições para dados de inspeção",
    schedule_interval="30 23 * * *",  # Rodar às 23:30 todos os dias
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:
    
    # Task para criar a partição
    create_partition_task = PythonOperator(
        task_id="create_partition",
        python_callable=create_partition,
    )

    create_partition_task
