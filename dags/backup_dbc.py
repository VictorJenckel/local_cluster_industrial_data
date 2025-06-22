from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.utils.dates import days_ago
from airflow.exceptions import AirflowFailException

import pandas as pd
import psycopg2
import os
import datetime

#  Datas do trimestre atual
hoje = datetime.date.today()

trimestre = (hoje.month - 1) // 3 + 1
inicio_trimestre = datetime.date(hoje.year, 3 * (trimestre - 1) + 1, 1)
if trimestre < 4:
    fim_trimestre = datetime.date(hoje.year, 3 * trimestre + 1, 1) - datetime.timedelta(days=1)
else:
    fim_trimestre = datetime.date(hoje.year, 12, 31)

periodo = f"{inicio_trimestre}_a_{fim_trimestre}"

#  Conexão PostgreSQL
conn_params = {
    "dbname": "dbc",
    "user": "admin",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
}

#  Lista das tabelas que serão processadas
tabelas = ['inspection_data_eagle_sl2', 'inspection_data_eagle_lra1', 'inspection_data_fsp']

#  Configurações DAG
default_args = {
    'owner': 'cebrace',
    'start_date': days_ago(1),
    'retries': 1,
}

dag = DAG(
    dag_id='backup_e_limpeza_trimestral_multi_tabela',
    default_args=default_args,
    schedule_interval='@quarterly',
    catchup=False,
    tags=['backup', 'parquet', 'postgres', 'multi']
)

#  Função para exportar para parquet
def exporta_para_parquet(tabela):
    pasta_parquet = f"/media/data/parquet/{tabela}/{periodo}"
    os.makedirs(pasta_parquet, exist_ok=True)
    arquivo_parquet = f"{pasta_parquet}/{tabela}_{periodo}.parquet"
    try:
        conn = psycopg2.connect(**conn_params)
        query = f"""
            SELECT * FROM {tabela}
            WHERE data BETWEEN '{inicio_trimestre}' AND '{fim_trimestre}';
        """
        df = pd.read_sql_query(query, conn)
        if df.empty:
            raise AirflowFailException(f"DataFrame vazio para {tabela}! Abortando.")
        df.to_parquet(arquivo_parquet)
        conn.close()
        print(f"Arquivo {arquivo_parquet} gerado com sucesso!")
    except Exception as e:
        raise AirflowFailException(f"Erro exportando {tabela} para parquet: {e}")

#  Função para validar parquet
def valida_parquet(tabela):
    pasta_parquet = f"/media/data/parquet/{tabela}/{periodo}"
    arquivo_parquet = f"{pasta_parquet}/{tabela}_{periodo}.parquet"
    if not os.path.isfile(arquivo_parquet):
        raise AirflowFailException(f"Arquivo {arquivo_parquet} não encontrado!")
    tamanho = os.path.getsize(arquivo_parquet)
    if tamanho < 100:
        raise AirflowFailException(f"Arquivo Parquet de {tabela} suspeito de estar vazio ou corrompido.")
    print(f"Arquivo {arquivo_parquet} validado com sucesso ({tamanho} bytes)")

#  Gerar os tasks dinamicamente
dias = pd.date_range(start=inicio_trimestre, end=fim_trimestre).to_pydatetime().tolist()

for tabela in tabelas:
    exporta = PythonOperator(
        task_id=f'exporta_{tabela}_parquet',
        python_callable=exporta_para_parquet,
        op_args=[tabela],
        dag=dag
    )

    valida = PythonOperator(
        task_id=f'valida_{tabela}_parquet',
        python_callable=valida_parquet,
        op_args=[tabela],
        dag=dag
    )

    exporta >> valida

    # Criando tasks de drop das partições por dia
    for dia in dias:
        nome_particao = f"{tabela}_{dia.strftime('%Y%m%d')}"
        drop = PostgresOperator(
            task_id=f'drop_particao_{nome_particao}',
            postgres_conn_id='seu_conn_id',  # Ajusta no Airflow
            sql=f"DROP TABLE IF EXISTS {nome_particao} CASCADE;",
            dag=dag
        )
        valida >> drop
