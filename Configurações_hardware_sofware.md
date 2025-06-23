# 📄 Documento de informação de Hardware e Software

## 1. Objetivo
Descrever as cofigurações atuais do cluster que está rodando a solução de engenharia de dados.

---

## 2. Hardware

### 2.1. Servidor Principal
- **Processador:** 12 nucleos i7 3300hz clock
- **Memória RAM:** 16GB 
- **Armazenamento:** sistema com duas SSD 1TB
  - `/` (sistema): 30GB
  - `/backup`: 500GB 
  - `/logs`: 200GB
  - `swap`: 20GB 
- **Disco:** SSD 2x 1TB
- **Rede:** Ethernet 1Gbps 

### 2.2. Máquinas Cliente (Fontes de Dados)
- PCs industriais que exportam arquivos de dados no formato TXT, CSV ou logs.
- Databases
- CLP's
- Conectados via rede interna.

---

## 3. Software

### 3.1. Sistema Operacional
- **Ubuntu Server 22.04 LTS** ou versão equivalente estável.

### 3.2. Serviços e Aplicações
- **PostgreSQL** versão >= 14
- **Apache Airflow** versão >= 2.9
- **Python** versão >= 3.10
- **Docker** versão 28.2.2 
- **Docker-Compose** versão 2.27.0
- **Prometheus e Grafana** (rodando via docker)

### 3.3. Bibliotecas Python 
```plaintext
apache-airflow==2.9.*
pandas
psycopg2-binary
sqlalchemy
python-dotenv


