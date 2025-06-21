#  Projeto Data Lake Local com PostgreSQL + Apache Airflow

Este projeto implementa um **mini Data Lake local** rodando em um servidor Linux, com banco de dados **PostgreSQL** e orquestração de processos via **Apache Airflow**.  
O objetivo é criar uma infraestrutura robusta e escalável para integrar e armazenar dados industriais, aplicando boas práticas de engenharia de dados

---

##  Motivação

Este projeto foi criado como parte da minha jornada de transição da área de automação industrial para engenharia de dados.
Com mais de 15 anos de experiência em chão de fábrica e sistemas industriais (especialmente Siemens PLCs), 
minha missão é integrar esse conhecimento com pipelines de dados, ETL, e Machine Learning, começando por uma base sólida de ingestão e orquestração.

---

##  Stack Utilizada

| Camada               | Ferramenta        | Função                                                                 |
|----------------------|-------------------|------------------------------------------------------------------------|
| SO                   | Linux (Ubuntu)    | Ambiente principal                                                     |
| Banco de Dados       | PostgreSQL        | Armazenamento dos dados particionados por data                        |
| Orquestração         | Apache Airflow    | Agendamento e execução das pipelines                                  |
| Automação de Backup  | crontab           | Backups automáticos do banco de dados                                  |
| Scripts ETL          | Python            | Ingestão e transformação de dados brutos (TXT, CSV, sensores, etc.)   |

---

##  Estrutura do Projeto

datalake_local/

![ArqDBC_airflow](https://github.com/user-attachments/assets/40c52b16-ab68-4e3f-bbf0-dbcaadb4347a)


##  Funcionamento

### 1. Automações
- criados serviços usando o systemd para rodar o aiflow webserver e scheduler automaticamente ao inciar a maquina

### 2. ETL das Máquinas

- A **Máquina 1** gera arquivos logs `.txt` . (rodando windows xp) - 
- arquivos sao copiados para pasta local (temp) usando smbclient - DAG airflow
- uma outra dag usando rsync monitora a pasta temp como sensor de alteração de dados
- Scripts em Python leem os arquivos, tratam os dados e inserem no PostgreSQL

### 3. Particionamento

- Tabelas são **particionadas por data**
- Uma DAG no Airflow roda todo dia à 23:30 para criar a partição do dia consecutivo

### 4. Backup Diário

- Script no `crontab` gera backup `.sql` do banco todos os dias à 02:00
- Os arquivos de backup são salvos na partição dedicada do servidor

### 4.1 Backup dos dados -trimestral

- Dag do airflow roda a cada 3 meses salvando os dados como Parquet, verificando a integridade e excluindo partições ja salvas
- Os arquivos parquet de backup são salvos na partição dedicada do servidor


### 5. Orquestração com Airflow

- O Airflow roda os servicos scheduler e webserver 
- Logs são registrados localmente para análise de falhas
- Monitoramento inicial feito com uso de **Prometheus + Grafana**


### 6. Rede

- Por rodar em uma industria esse servidor foi implementado para rodar em uma rede local, e terá acesso a camada P2 da rede, a camada superior acessará ele atraves de um gateway preexistente
- o firewall foi implementado para abrir as portas:
- 8080/tcp - Airflow Web
- 5050/tcp - postgres web
- 5432/tcp - acesso a databse
- 22/tcp - acesso remoto via ssh
- 3000/tcp - acesso grafana web
---

##  Como Rodar
- o processo roda automaticamente como um ETL, realiza busca do arquivo log nas maquinas host, cria uma copia temporaria no servidor, faz o tratamento dos dados
- escreve dados no banco de dados postgres e exclui arquivo temporario.
- Todo acesso é realizado atraves de interface web rodando no servidor , airflow roda em http:\\localhost:8080, postgres roda em http:\\localhost:5050 e grafana roda em http:\\localhost:3000
- esses links locais podem ser acessados por outros pc's da rede local utilizando ip fixo do servidor 

### Requisitos

- Ubuntu 20.04+
- Python 3.10+
- PostgreSQL 14+
- Apache Airflow 2.9 

