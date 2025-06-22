#!/bin/bash

# Configurações
DB_NAME="dbc"
DB_USER="admin"
DB_PASSWORD="admin"
POSTGRES_PASSWORD="postgres"
PGADMIN_EMAIL="admin@dbc.com"
PGADMIN_PASSWORD="admin"

# Função para verificar erros
check_error() {
    if [ $? -ne 0 ]; then
        echo "Erro: $1"
        exit 1
    fi
}

echo "=== Instalação e Configuração PostgreSQL + pgAdmin4 ==="

# Atualizar sistema
echo "Atualizando sistema..."
sudo apt update && sudo apt upgrade -y
check_error "Falha ao atualizar sistema"

# Instalar PostgreSQL
echo "Instalando PostgreSQL..."
sudo apt install postgresql postgresql-contrib -y
check_error "Falha ao instalar PostgreSQL"

# Ativar e iniciar o serviço PostgreSQL
echo "Iniciando serviços PostgreSQL..."
sudo systemctl enable postgresql
sudo systemctl start postgresql
check_error "Falha ao iniciar PostgreSQL"

# Configurar senha do usuário postgres
echo "Configurando senha do usuário postgres..."
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$POSTGRES_PASSWORD';"
check_error "Falha ao configurar senha do postgres"

# Criar usuário e databases
echo "Criando usuário e databases..."
sudo -u postgres psql << EOF
-- Criar usuário admin
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';

-- Criar database DBC
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT CREATE ON SCHEMA public TO $DB_USER;

-- Criar database para Airflow
CREATE DATABASE airflow_db OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO $DB_USER;
GRANT CREATE ON SCHEMA public TO $DB_USER;

-- Dar privilégios de superuser para operações do Airflow
ALTER USER $DB_USER CREATEDB;
\q
EOF
check_error "Falha ao criar usuário e databases"

# Configurar PostgreSQL para aceitar conexões
echo "Configurando PostgreSQL para aceitar conexões..."
PG_VERSION=$(sudo -u postgres psql -t -c "SELECT version();" | grep -oP '\d+\.\d+' | head -1)
PG_MAJOR_VERSION=$(echo $PG_VERSION | cut -d. -f1)

# Backup dos arquivos de configuração
sudo cp /etc/postgresql/$PG_MAJOR_VERSION/main/postgresql.conf /etc/postgresql/$PG_MAJOR_VERSION/main/postgresql.conf.backup
sudo cp /etc/postgresql/$PG_MAJOR_VERSION/main/pg_hba.conf /etc/postgresql/$PG_MAJOR_VERSION/main/pg_hba.conf.backup

# Modificar postgresql.conf
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/$PG_MAJOR_VERSION/main/postgresql.conf

# Adicionar configuração de acesso no pg_hba.conf
echo "host    all             all             0.0.0.0/0                md5" | sudo tee -a /etc/postgresql/$PG_MAJOR_VERSION/main/pg_hba.conf

# Reiniciar PostgreSQL
echo "Reiniciando PostgreSQL..."
sudo systemctl restart postgresql
check_error "Falha ao reiniciar PostgreSQL"

# Configurar firewall
echo "Configurando firewall..."
sudo ufw allow 5432/tcp
sudo ufw --force enable

# Instalar dependências para pgAdmin4
echo "Instalando dependências para pgAdmin4..."
sudo apt install curl ca-certificates gnupg apache2 -y
check_error "Falha ao instalar dependências"

# Adicionar repositório pgAdmin4
echo "Adicionando repositório pgAdmin4..."
curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo gpg --dearmor -o /usr/share/keyrings/packages-pgadmin-org.gpg
check_error "Falha ao adicionar chave GPG"

sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/packages-pgadmin-org.gpg] https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list'

# Atualizar lista de pacotes
sudo apt update
check_error "Falha ao atualizar lista de pacotes"

# Instalar pgAdmin4 Web
echo "Instalando pgAdmin4 Web..."
sudo apt install pgadmin4-web -y
check_error "Falha ao instalar pgAdmin4"

# Configurar pgAdmin4 Web automaticamente
echo "Configurando pgAdmin4 Web..."
sudo python3 /usr/pgadmin4/bin/setup-web.py << EOF
$PGADMIN_EMAIL
$PGADMIN_PASSWORD
$PGADMIN_PASSWORD
y
EOF

# Reiniciar Apache
echo "Reiniciando Apache..."
sudo systemctl restart apache2
check_error "Falha ao reiniciar Apache"

sudo systemctl enable apache2


# Configurar backup automático
echo "Configurando backup automático..."
sudo mkdir -p /backups
sudo chown $(whoami):$(whoami) /backups

# Criar script de backup
cat << 'EOF' > /tmp/backup_dbc.sh
#!/bin/bash
BACKUP_DIR="/backups"
DB_NAME="dbc"
DB_USER="admin"
DATE=$(date +%Y%m%d_%H%M%S)

export PGPASSWORD="admin"
pg_dump -h localhost -U $DB_USER -Fc $DB_NAME > $BACKUP_DIR/DBC_backup_$DATE.backup

# Manter apenas os últimos 7 backups
find $BACKUP_DIR -name "DBC_backup_*.backup" -type f -mtime +7 -delete
EOF

sudo mv /tmp/backup_dbc.sh /usr/local/bin/backup_dbc.sh
sudo chmod +x /usr/local/bin/backup_dbc.sh

# Adicionar ao crontab para backup diário às 3h
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/backup_dbc.sh") | crontab -

echo ""
echo "=== Instalação concluída com sucesso! ==="
echo ""
echo "INFORMAÇÕES DE ACESSO:"
echo ""
echo "PostgreSQL:"
echo "  - Host: localhost"
echo "  - Porta: 5432"
echo "  - Database DBC: $DB_NAME"
echo "  - Database Airflow: airflow_db"
echo "  - Usuário: $DB_USER"
echo "  - Senha: $DB_PASSWORD"
echo ""
echo "pgAdmin4 Web:"
echo "  - URL: http://localhost/pgadmin4"
echo "  - Email: $PGADMIN_EMAIL"
echo "  - Senha: $PGADMIN_PASSWORD"
echo ""
echo "Usuário postgres (superuser):"
echo "  - Usuário: postgres"
echo "  - Senha: $POSTGRES_PASSWORD"
echo ""
echo "CONFIGURAÇÃO AIRFLOW:"
echo "Para usar PostgreSQL no Airflow, adicione ao arquivo airflow.cfg:"
echo "sql_alchemy_conn = postgresql+psycopg2://admin:admin@localhost/airflow_db"
echo ""
echo "Ou use a variável de ambiente:"
echo "export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://admin:admin@localhost/airflow_db"
echo ""
echo "COMANDOS ÚTEIS:"
echo "  - Verificar status PostgreSQL: sudo systemctl status postgresql"
echo "  - Verificar status Apache: sudo systemctl status apache2"
echo "  - Conectar via psql DBC: psql -h localhost -U $DB_USER -d $DB_NAME"
echo "  - Conectar via psql Airflow: psql -h localhost -U $DB_USER -d airflow_db"
echo "  - Executar backup manual: /usr/local/bin/backup_dbc.sh"
echo "  - Backup automático configurado para executar diariamente às 3h."
