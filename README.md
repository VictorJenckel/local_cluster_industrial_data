# 🏭 Projeto Data Lake Local com PostgreSQL + Apache Airflow

Este projeto implementa um **mini Data Lake local** rodando em um servidor Linux, com banco de dados **PostgreSQL** e orquestração de processos via **Apache Airflow**.  
O objetivo é criar uma infraestrutura robusta e escalável para integrar e armazenar dados industriais, aplicando boas práticas de engenharia de dados

---

## 🧠 Motivação

Este projeto foi criado como parte da minha jornada de transição da área de automação industrial para engenharia de dados.
Com mais de 15 anos de experiência em chão de fábrica e sistemas industriais (especialmente Siemens PLCs), 
minha missão é integrar esse conhecimento com pipelines de dados, ETL, e Machine Learning, começando por uma base sólida de ingestão e orquestração.

---

## ⚙️ Stack Utilizada

| Camada               | Ferramenta        | Função                                                                 |
|----------------------|-------------------|------------------------------------------------------------------------|
| SO                   | Linux (Ubuntu)    | Ambiente principal                                                     |
| Banco de Dados       | PostgreSQL        | Armazenamento dos dados particionados por data                        |
| Orquestração         | Apache Airflow    | Agendamento e execução das pipelines                                  |
| Automação de Backup  | crontab           | Backups automáticos do banco de dados                                  |
| Scripts ETL          | Python            | Ingestão e transformação de dados brutos (TXT, CSV, sensores, etc.)   |

---

## 🧱 Estrutura do Projeto

datalake_local/
├── dags/
│ ├── criar_particoes_diarias.py
│ └── etl_maquina1.py
├── etl/
│ ├── processa_maquina1.py
├── sql/
│ ├── criar_tabelas.sql
│ └── criar_particao.sql
├── backups/
│ └── (arquivos de backup .sql diários)
├── logs/
│ └── (logs de execução)
├── crontab/
│ └── backup_postgres.sh

## 🔄 Funcionamento

### 1. Automações
- criados serviços usando o systemd para rodar o aiflow webserver e scheduler automaticamente ao inciar a maquina

### 2. ETL das Máquinas

- A **Máquina 1** gera arquivos logs `.txt` . (rodando windows xp) - 
- arquivos sao copiados para pasta local (temp) usando smbclient - DAG airflow
- uma outra dag usando rsync monitora a pasta temp como sensor de alteração de dados
- Scripts em Python leem os arquivos, tratam os dados e inserem no PostgreSQL

### 3. Particionamento

- Tabelas são **particionadas por data**
- Uma DAG no Airflow roda todo dia à 00:00 para criar a partição do dia atual

### 4. Backup Diário

- Script no `crontab` gera backup `.sql` do banco todos os dias à 01:00
- Os arquivos de backup são salvos na partição dedicada do servidor

### 5. Orquestração com Airflow

- O Airflow roda os servicos scheduler e webserver 
- Logs são registrados localmente para análise de falhas
- Monitoramento inicial feito manualmente, com planos futuros para uso de **Prometheus + Grafana**

---

## 🛠️ Como Rodar

### Requisitos

- Ubuntu 20.04+
- Python 3.10+
- PostgreSQL 14+
- Apache Airflow 2.9 (instalado via `pip`)
- Permissão para editar crontab
