from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import subprocess
import re
import os
import pandas as pd
import glob
import psycopg2


# Configurações padrão da DAG
default_args = {
    'owner': 'victor_jenckel',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Definição da DAG
dag = DAG(
    'platelog_processing',
    default_args=default_args,
    description='Download e processamento de arquivos PlateLog a cada 5 minutos',
    schedule_interval=timedelta(minutes=5), 
    catchup=False, 
    max_active_runs=1, 
)

# === CONFIGURAÇÕES ===
SERVIDOR = "192.168.0.1"
COMPARTILHAMENTO = "Logs"
USUARIO = "viewer"
SENHA = "viewer"
PASTA_LOCAL = "/home/c/dbc/temp"
ARQUIVO_LOCAL_PATTERN = "*PlateLog.txt"

def obter_data_arquivo():
    """
    Determina qual data usar baseada no horário atual:
    - Antes das 6h: usa data do dia anterior
    - Após as 6h: usa data do dia atual
    """
    agora = datetime.now()
    
    if agora.hour < 6:
        # Antes das 6h da manhã, usa arquivo do dia anterior
        data_arquivo = (agora - timedelta(days=1)).date()
    else:
        # Após as 6h da manhã, usa arquivo do dia atual
        data_arquivo = agora.date()
    
    return data_arquivo.strftime("%Y-%m-%d")

def limpar_arquivos_antigos():
    """Remove todos os arquivos PlateLog.txt existentes na pasta local"""
    arquivos_existentes = glob.glob(os.path.join(PASTA_LOCAL, ARQUIVO_LOCAL_PATTERN))
    
    for arquivo in arquivos_existentes:
        try:
            os.remove(arquivo)
            print(f"Arquivo antigo removido: {os.path.basename(arquivo)}")
        except Exception as e:
            print(f"Erro ao remover {arquivo}: {e}")

def download_platelog_file(**context):
    """
    Task do Airflow para baixar arquivo PlateLog com lógica de data inteligente
    """
    try:
        # Garante que a pasta local exista
        os.makedirs(PASTA_LOCAL, exist_ok=True)
        os.chdir(PASTA_LOCAL)
        
        # Determina a data do arquivo que deve ser buscado
        data_busca = obter_data_arquivo()
        nome_arquivo_esperado = f"{data_busca}-PlateLog.txt"
        pasta_remota = datetime.now().strftime("%Y-%m")
        
        print(f"Horário atual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Buscando arquivo: {nome_arquivo_esperado}")
        
        # === PASSO 1: LISTAR ARQUIVOS ===
        print(" Listando arquivos no compartilhamento remoto...")
        
        comando_ls = [
            "smbclient",
            f"//{SERVIDOR}/{COMPARTILHAMENTO}",
            "-U", f"{USUARIO}%{SENHA}",
            "-c", f"cd {pasta_remota}; ls"
        ]
        
        resultado_ls = subprocess.run(comando_ls, capture_output=True, text=True)
        
        if resultado_ls.returncode != 0:
            error_msg = f" Erro ao listar arquivos: {resultado_ls.stderr}"
            print(error_msg)
            raise Exception(error_msg)
        
        # Procura especificamente pelo arquivo da data correta
        linhas = resultado_ls.stdout.splitlines()
        arquivo_encontrado = None
        
        for linha in linhas:
            partes = linha.strip().split()
            if len(partes) >= 1:
                nome_arquivo = partes[0]
                if nome_arquivo == nome_arquivo_esperado:
                    arquivo_encontrado = nome_arquivo
                    break
        
        if not arquivo_encontrado:
            print(f"Arquivo '{nome_arquivo_esperado}' não encontrado.")
            print("Arquivos disponíveis:")
            arquivos_disponiveis = []
            for linha in linhas:
                partes = linha.strip().split()
                if len(partes) >= 1 and partes[0].endswith("PlateLog.txt"):
                    arquivos_disponiveis.append(partes[0])
                    print(f"   - {partes[0]}")
            
            # Se não encontrou o arquivo esperado, ainda assim tenta pegar o mais recente
            if arquivos_disponiveis:
                arquivo_encontrado = max(arquivos_disponiveis)
                print(f"Usando arquivo mais recente disponível: {arquivo_encontrado}")
            else:
                raise Exception("Nenhum arquivo PlateLog.txt encontrado no diretório remoto")
        
        print(f"Arquivo selecionado: {arquivo_encontrado}")
        
        # === PASSO 2: SEMPRE BAIXAR PARA MANTER ATUALIZADO ===
        arquivo_local_path = os.path.join(PASTA_LOCAL, arquivo_encontrado)
        
        # Como o arquivo remoto se atualiza constantemente com o mesmo nome,
        # sempre fazemos o download para manter os dados atualizados
        print("Arquivo será baixado/atualizado para manter dados sincronizados")
        # === PASSO 3: LIMPAR ARQUIVOS ANTIGOS ===
        print("Removendo arquivos antigos da pasta local...")
        limpar_arquivos_antigos()
        
        # === PASSO 4: BAIXAR/ATUALIZAR O ARQUIVO ===
        print("Baixando/atualizando arquivo para a pasta local...")
        
        comando_get = [
            "smbclient",
            f"//{SERVIDOR}/{COMPARTILHAMENTO}",
            "-U", f"{USUARIO}%{SENHA}",
            "-c", f"cd {pasta_remota}; get {arquivo_encontrado} {arquivo_encontrado}"
        ]
        
        resultado_get = subprocess.run(comando_get, capture_output=True, text=True)
        
        if resultado_get.returncode == 0:
            print(f"Arquivo '{arquivo_encontrado}' atualizado com sucesso!")
            print(f"Localização: {arquivo_local_path}")
        else:
            error_msg = f"Erro ao copiar o arquivo: {resultado_get.stderr}"
            print(error_msg)
            raise Exception(error_msg)
        
        # Retorna o caminho do arquivo para a próxima task
        return arquivo_local_path
        
    except Exception as e:
        print(f"Erro na task de download: {str(e)}")
        raise

def padronizar_colunas_fino(df):
    """Padroniza nomes das colunas do DataFrame"""
    substituicoes_especificas = {
        'Date': 'date', 'Rej': 'rej', 'Warn': 'warn', 'O/P': 'op', 'Action': 'action',
        'Thick': 'thick', 'Type': 'type', 'Wid': 'wid', 'W Cor': 'w_cor', 'Len': 'len',
        'L Cor': 'l_cor', 'Sq': 'sq', 'Sk': 'sk', 'CAng 1': 'cang_1', 'CAng 2': 'cang_2',
        'CAng 3': 'cang_3', 'CAng 4': 'cang_4', 'Defect': 'defect', 'Thresh': 'thresh',
        'PLC W': 'plc_w', 'PLC L': 'plc_l', 'W Dev': 'w_dev', 'L Dev': 'l_dev',
        'Ang 1': 'ang_1', 'Ang 2': 'ang_2', 'Ang 3': 'ang_3', 'Ang4': 'ang_4',
        'Del 1': 'del_1', 'Del 2': 'del_2', 'Del 3': 'del_3', 'Del 4': 'del_4',
        'Ink X': 'ink_x', 'Ink Y': 'ink_y', 'Qual': 'qual', 'GrpID': 'grpid',
        'PltID': 'pltid', 'Stream': 'stream', 'Split': 'split', 'HeadCrossCut': 'head_cross_cut',
        'TailCrossCut': 'tail_cross_cut', 'LongCut': 'long_cut', 'Dest': 'dest',
        'Align0': 'align0', 'Skew0': 'skew0', 'Align1': 'align1', 'Skew1': 'skew1',
        'CPU()': 'cpu', 'CPU-pk': 'cpu_pk', 'AvailRAM': 'avail_ram', 'TotalMEM': 'total_mem',
        'AvailMEM': 'avail_mem', 'ProcessMEM': 'process_mem', 'Defect X': 'defect_x',
        'Defect Y': 'defect_y', 'HeadXCutB': 'headx_cutb', 'HeadXCutH': 'headx_cuth',
        'TailXCutB': 'tailx_cutb', 'TailXCutH': 'tailx_cuth', 'LeftYCutB': 'lefty_cutb',
        'LeftYCutH': 'lefty_cuth', 'RightYCutB': 'righty_cutb', 'RightYCutH': 'righty_cuth',
    }

    def tratar_nome(col):
        if col in substituicoes_especificas:
            return substituicoes_especificas[col]
        col = col.lower()
        col = re.sub(r'[^\w]+', '_', col)
        col = re.sub(r'_+', '_', col)
        return col.strip('_')

    df.columns = [tratar_nome(col) for col in df.columns]
    return df

def transform_data_pandas(df):
    """Converte colunas que começam com 'dat' para datetime"""
    for col_name in df.columns:
        if col_name.lower().startswith('dat') and df[col_name].dtype == 'object':
            try:
                df[col_name] = pd.to_datetime(df[col_name], format='%Y/%m/%d %H:%M:%S', errors='coerce')
                print(f" Coluna {col_name} convertida para datetime")
            except Exception as e:
                print(f" Erro ao converter coluna {col_name}: {e}")
    return df

def limpar_valores_invalidos(df):
    """Substitui valores não numéricos inválidos por NaN"""
    padroes_invalidos = ["-1.#J", "1.#J", "NaN", "1.#QNAN", "-1.#IND", "-1.#INF", "1.#INF"]
    df.replace(padroes_invalidos, pd.NA, inplace=True)

    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass
    return df

def write_to_postgres(df):
    """Escreve DataFrame no PostgreSQL"""
    try:
        conn = psycopg2.connect(
            dbname="dbc",
            user="admin",
            password="admin",
            host="127.0.0.1",
            port=5432
        )
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO inspection_data_eagle (
            date, rej, warn, op, action, thick, type, wid, w_cor, len, l_cor, sq, sk, cang_1, cang_2, cang_3, cang_4,
            defect, thresh, plc_w, plc_l, w_dev, l_dev, ang_1, ang_2, ang_3, ang_4, del_1, del_2, del_3, del_4,
            ink_x, ink_y, qual, grpid, pltid, stream, split, head_cross_cut, tail_cross_cut, long_cut, dest,
            align0, skew0, align1, skew1, cpu, cpu_pk, avail_ram, total_mem, avail_mem, process_mem,
            defect_x, defect_y, headx_cutb, headx_cuth, tailx_cutb, tailx_cuth, lefty_cutb, lefty_cuth,
            righty_cutb, righty_cuth
        )
        VALUES (
            %(date)s, %(rej)s, %(warn)s, %(op)s, %(action)s, %(thick)s, %(type)s, %(wid)s, %(w_cor)s, %(len)s, %(l_cor)s, %(sq)s, %(sk)s, %(cang_1)s, %(cang_2)s, %(cang_3)s, %(cang_4)s,
            %(defect)s, %(thresh)s, %(plc_w)s, %(plc_l)s, %(w_dev)s, %(l_dev)s, %(ang_1)s, %(ang_2)s, %(ang_3)s, %(ang_4)s, %(del_1)s, %(del_2)s, %(del_3)s, %(del_4)s,
            %(ink_x)s, %(ink_y)s, %(qual)s, %(grpid)s, %(pltid)s, %(stream)s, %(split)s, %(head_cross_cut)s, %(tail_cross_cut)s, %(long_cut)s, %(dest)s,
            %(align0)s, %(skew0)s, %(align1)s, %(skew1)s, %(cpu)s, %(cpu_pk)s, %(avail_ram)s, %(total_mem)s, %(avail_mem)s, %(process_mem)s,
            %(defect_x)s, %(defect_y)s, %(headx_cutb)s, %(headx_cuth)s, %(tailx_cutb)s, %(tailx_cuth)s, %(lefty_cutb)s, %(lefty_cuth)s,
            %(righty_cutb)s, %(righty_cuth)s
        )
        ON CONFLICT (pltid, date) DO UPDATE SET
            rej = EXCLUDED.rej,
            warn = EXCLUDED.warn,
            op = EXCLUDED.op,
            action = EXCLUDED.action,
            thick = EXCLUDED.thick,
            type = EXCLUDED.type,
            wid = EXCLUDED.wid,
            w_cor = EXCLUDED.w_cor,
            len = EXCLUDED.len,
            l_cor = EXCLUDED.l_cor,
            sq = EXCLUDED.sq,
            sk = EXCLUDED.sk,
            cang_1 = EXCLUDED.cang_1,
            cang_2 = EXCLUDED.cang_2,
            cang_3 = EXCLUDED.cang_3,
            cang_4 = EXCLUDED.cang_4,
            defect = EXCLUDED.defect,
            thresh = EXCLUDED.thresh,
            plc_w = EXCLUDED.plc_w,
            plc_l = EXCLUDED.plc_l,
            w_dev = EXCLUDED.w_dev,
            l_dev = EXCLUDED.l_dev,
            ang_1 = EXCLUDED.ang_1,
            ang_2 = EXCLUDED.ang_2,
            ang_3 = EXCLUDED.ang_3,
            ang_4 = EXCLUDED.ang_4,
            del_1 = EXCLUDED.del_1,
            del_2 = EXCLUDED.del_2,
            del_3 = EXCLUDED.del_3,
            del_4 = EXCLUDED.del_4,
            ink_x = EXCLUDED.ink_x,
            ink_y = EXCLUDED.ink_y,
            qual = EXCLUDED.qual,
            grpid = EXCLUDED.grpid,
            stream = EXCLUDED.stream,
            split = EXCLUDED.split,
            head_cross_cut = EXCLUDED.head_cross_cut,
            tail_cross_cut = EXCLUDED.tail_cross_cut,
            long_cut = EXCLUDED.long_cut,
            dest = EXCLUDED.dest,
            align0 = EXCLUDED.align0,
            skew0 = EXCLUDED.skew0,
            align1 = EXCLUDED.align1,
            skew1 = EXCLUDED.skew1,
            cpu = EXCLUDED.cpu,
            cpu_pk = EXCLUDED.cpu_pk,
            avail_ram = EXCLUDED.avail_ram,
            total_mem = EXCLUDED.total_mem,
            avail_mem = EXCLUDED.avail_mem,
            process_mem = EXCLUDED.process_mem,
            defect_x = EXCLUDED.defect_x,
            defect_y = EXCLUDED.defect_y,
            headx_cutb = EXCLUDED.headx_cutb,
            headx_cuth = EXCLUDED.headx_cuth,
            tailx_cutb = EXCLUDED.tailx_cutb,
            tailx_cuth = EXCLUDED.tailx_cuth,
            lefty_cutb = EXCLUDED.lefty_cutb,
            lefty_cuth = EXCLUDED.lefty_cuth,
            righty_cutb = EXCLUDED.righty_cutb,
            righty_cuth = EXCLUDED.righty_cuth;
        """

        rows_inserted = 0
        rows_updated = 0

        for _, row in df.iterrows():
            try:
                cursor.execute(insert_query, row.to_dict())
                if cursor.rowcount > 0:
                    
                    rows_inserted += 1
                else:
                    rows_updated += 1
            except Exception as e:
                print(f" Erro ao inserir linha: {e}")
                conn.rollback()
                continue

        conn.commit()
        cursor.close()
        conn.close()

        print(f" {rows_inserted} registros processados com sucesso no PostgreSQL")
        print("Registros foram inseridos ou atualizados conforme necessário")
        
        return rows_inserted

    except Exception as e:
        print(f"Erro ao conectar/escrever no PostgreSQL: {e}")
        raise

def process_platelog_data(**context):
    """
    Task do Airflow para processar dados do PlateLog
    """
    try:
        # Pega o caminho do arquivo da task anterior
        task_instance = context['task_instance']
        arquivo_path = task_instance.xcom_pull(task_ids='download_platelog')
        
        # Se não conseguiu pegar via XCom, usa o padrão
        if not arquivo_path:
            # Procura por qualquer arquivo PlateLog na pasta
            arquivos_platelog = glob.glob(os.path.join(PASTA_LOCAL, ARQUIVO_LOCAL_PATTERN))
            if not arquivos_platelog:
                raise Exception("Nenhum arquivo PlateLog encontrado na pasta local")
            arquivo_path = max(arquivos_platelog, key=os.path.getmtime)  # Pega o mais recente
        
        print(f" Processando arquivo: {arquivo_path}")

        if not os.path.exists(arquivo_path):
            raise Exception(f"Arquivo não encontrado: {arquivo_path}")

        # Lê o arquivo CSV
        df = pd.read_csv(arquivo_path, sep='\t', header=0)
        print(f"Arquivo lido com sucesso. {len(df)} linhas encontradas.")

        if len(df) == 0:
            print("Arquivo está vazio, pulando processamento")
            return 0

        # Processa os dados
        df = padronizar_colunas_fino(df)
        df = transform_data_pandas(df)
        df = limpar_valores_invalidos(df)

        # Escreve no banco
        result = write_to_postgres(df)
        
        print(f"Processamento concluído com sucesso: {result} registros inseridos")
        return result

    except Exception as e:
        print(f"Erro ao processar dados: {str(e)}")
        raise

# Definindo as tasks da DAG
download_task = PythonOperator(
    task_id='download_platelog',
    python_callable=download_platelog_file,
    dag=dag,
)

process_task = PythonOperator(
    task_id='process_platelog_data',
    python_callable=process_platelog_data,
    dag=dag,
)

# Definindo a dependência entre as tasks
download_task >> process_task
