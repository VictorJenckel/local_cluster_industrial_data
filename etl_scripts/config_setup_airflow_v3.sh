#!/bin/bash

# Configurações
AIRFLOW_VERSION=2.9.0
PYTHON_VERSION="3.10"
AIRFLOW_HOME="$HOME/dbc/airflow"
VENV_PATH="$HOME/airflow_venv"
USER_NAME="victor_jenckel"

# Função para verificar erros
check_error() {
    if [ $? -ne 0 ]; then
        echo "Erro: $1"
        exit 1
    fi
}

echo "=== Instalação do Apache Airflow ${AIRFLOW_VERSION} ==="

# Verificar se Python 3.10 está disponível
python3 --version | grep -q "3.10" || {
    echo "Aviso: Python 3.10 não detectado. Continuando com a versão disponível..."
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
}

echo "Limpando ambiente antigo..."
rm -rf "$VENV_PATH"

echo "Criando novo ambiente virtual..."
python3 -m venv "$VENV_PATH"
check_error "Falha ao criar ambiente virtual"

echo "Ativando ambiente virtual..."
source "$VENV_PATH/bin/activate"
check_error "Falha ao ativar ambiente virtual"

echo "Instalando Airflow ${AIRFLOW_VERSION} com dependências compatíveis..."
export AIRFLOW_VERSION
export PYTHON_VERSION
export CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install --upgrade pip
check_error "Falha ao atualizar pip"

pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
check_error "Falha ao instalar Airflow"

pip install psycopg2-binary
pip install pandas
pip install apache-airflow-providers-postgres==5.10.0
pip install smbprotocol


echo "Criando pasta do projeto airflow..."
export AIRFLOW_HOME
mkdir -p "$AIRFLOW_HOME"
check_error "Falha ao criar diretório do Airflow"

echo "Salvando AIRFLOW_HOME no .bashrc..."
if ! grep -q "AIRFLOW_HOME" ~/.bashrc; then
    echo "export AIRFLOW_HOME=${AIRFLOW_HOME}" >> ~/.bashrc
    echo "export PATH=\$PATH:${VENV_PATH}/bin" >> ~/.bashrc
    echo "export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://admin:admin@localhost/airflow_db" >> ~/.bashrc
fi

# Configurar Airflow para usar PostgreSQL
echo "Configurando Airflow para usar PostgreSQL..."
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://admin:admin@localhost/airflow_db

echo "Inicializando o banco de dados do Airflow..."
airflow db init
check_error "Falha ao inicializar banco de dados"

echo "Criando usuário Admin do Airflow..."
airflow users create \
    --username admin \
    --firstname Victor \
    --lastname Jenckel \
    --role Admin \
    --email victorjenckel@gmail.com \
    --password admin
check_error "Falha ao criar usuário admin"

echo "Configurando serviços systemd..."

# Parar e remover serviços existentes
sudo systemctl stop airflow-webserver airflow-scheduler 2>/dev/null || true
sudo systemctl disable airflow-webserver airflow-scheduler 2>/dev/null || true
sudo rm -f /etc/systemd/system/airflow-webserver.service
sudo rm -f /etc/systemd/system/airflow-scheduler.service

# Criar arquivo de serviço do webserver
echo "Criando serviço airflow-webserver..."
sudo tee /etc/systemd/system/airflow-webserver.service > /dev/null << EOF
[Unit]
Description=Airflow Webserver
After=network.target
Wants=airflow-scheduler.service

[Service]
User=${USER_NAME}
Group=${USER_NAME}
Environment="AIRFLOW_HOME=${AIRFLOW_HOME}"
Environment="PATH=${VENV_PATH}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${VENV_PATH}/bin/airflow webserver --port 8080 --host 0.0.0.0
Restart=always
RestartSec=5s
WorkingDirectory=${AIRFLOW_HOME}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Criar arquivo de serviço do scheduler
echo "Criando serviço airflow-scheduler..."
sudo tee /etc/systemd/system/airflow-scheduler.service > /dev/null << EOF
[Unit]
Description=Airflow Scheduler
After=network.target

[Service]
User=${USER_NAME}
Group=${USER_NAME}
Environment="AIRFLOW_HOME=${AIRFLOW_HOME}"
Environment="PATH=${VENV_PATH}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=${VENV_PATH}/bin/airflow scheduler
Restart=always
RestartSec=5s
WorkingDirectory=${AIRFLOW_HOME}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recarregar systemd e iniciar serviços
echo "Recarregando configurações do systemd..."
sudo systemctl daemon-reload
check_error "Falha ao recarregar systemd"

sudo systemctl enable airflow-webserver airflow-scheduler
check_error "Falha ao habilitar serviços"

sudo systemctl start airflow-scheduler
check_error "Falha ao iniciar scheduler"

# Aguardar scheduler inicializar antes de iniciar webserver
echo "Aguardando scheduler inicializar..."
sleep 10

sudo systemctl start airflow-webserver
check_error "Falha ao iniciar webserver"

echo ""
echo "=== Setup finalizado com sucesso! ==="
echo "Acesse: http://localhost:8080"
echo "Usuário: admin"
echo "Senha: admin"
echo ""
echo "Para verificar status dos serviços:"
echo "sudo systemctl status airflow-webserver"
echo "sudo systemctl status airflow-scheduler"
echo ""
echo "Para ver logs:"
echo "sudo journalctl -u airflow-webserver -f"
echo "sudo journalctl -u airflow-scheduler -f"
