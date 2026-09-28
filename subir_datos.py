import os
import pandas as pd
import mysql.connector
from mysql.connector import Error

# Configuración de conexión a MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',  # Tu contraseña de MySQL
    'database': 'dev',
    'charset': 'utf8mb4'
}

NOMBRE_TABLA = "mensajeria"

# Lista oficial de las 27 columnas válidas de la tabla
COLUMNAS_ESQUEMA = [
    'id', 'content', 'account_id', 'inbox_id', 'conversation_id', 
    'message_type', 'created_at', 'updated_at', 'private', 'status', 
    'source_id', 'content_type', 'content_attributes', 'sender_type', 
    'sender_id', 'additional_attributes', 'processed_message_content', 
    'sentiment', 'contact_id', 'sistema_lead_id', 'conversation_display_id', 
    'id_sistema', 'id_db_externa', 'id_leads_db_externa', 
    'error_exacto', 'nombre_plantilla', 'categoria_cliente'
]

SQL_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {NOMBRE_TABLA} (
    id VARCHAR(50),
    content TEXT,
    account_id VARCHAR(50),
    inbox_id VARCHAR(50),
    conversation_id VARCHAR(50),
    message_type VARCHAR(50),
    created_at DATETIME,
    updated_at DATETIME,
    private VARCHAR(20),
    status VARCHAR(50),
    source_id TEXT,
    content_type VARCHAR(50),
    content_attributes TEXT,
    sender_type VARCHAR(50),
    sender_id VARCHAR(50),
    additional_attributes TEXT,
    processed_message_content TEXT,
    sentiment TEXT,
    contact_id VARCHAR(50),
    sistema_lead_id VARCHAR(50),
    conversation_display_id VARCHAR(50),
    id_sistema VARCHAR(50),
    id_db_externa VARCHAR(50),
    id_leads_db_externa VARCHAR(50),
    error_exacto TEXT,
    nombre_plantilla VARCHAR(255),
    categoria_cliente VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

def asegurar_base_de_datos():
    """Crea la base de datos si no existe."""
    config_temp = DB_CONFIG.copy()
    db_name = config_temp.pop('database')
    
    try:
        conn = mysql.connector.connect(**config_temp)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error al verificar base de datos: {e}")

def cargar_csv_a_mysql(filepath: str):
    """
    Crea la tabla si no existe, descarta columnas fantasmas, 
    limpia registros antiguos e inserta los datos en MySQL.
    """
    asegurar_base_de_datos()
    
    if not os.path.exists(filepath):
        print(f"Error: No se encuentra el archivo CSV en: {filepath}")
        return

    # 1. Leer el CSV
    df = pd.read_csv(filepath, dtype=str)

    # 2. Filtrar únicamente las columnas reales que pertenecen a la tabla MySQL
    columnas_validas = [col for col in COLUMNAS_ESQUEMA if col in df.columns]
    df = df[columnas_validas]

    # 3. Reemplazar valores nulos/vacíos por None para insertar NULL en SQL
    df = df.replace({r'^(nan|NaN|None|<NA>|NULL|null|)$': None}, regex=True)
    df = df.where(pd.notnull(df), None)

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Crear la tabla si no existe
        cursor.execute(SQL_CREATE_TABLE)
        print(f"Tabla '{NOMBRE_TABLA}' verificada/creada correctamente.")

        # Limpiar datos previos
        cursor.execute(f"TRUNCATE TABLE {NOMBRE_TABLA};")
        print(f"Registros antiguos limpiados (TRUNCATE {NOMBRE_TABLA}).")

        # Construir consulta SQL con columnas limpias
        columnas_sql = ", ".join([f"`{col}`" for col in columnas_validas])
        placeholders = ", ".join(["%s"] * len(columnas_validas))
        sql_insert = f"INSERT INTO {NOMBRE_TABLA} ({columnas_sql}) VALUES ({placeholders})"
        
        # Convertir datos a lista de tuplas
        valores = [
            tuple(None if pd.isna(val) else str(val) for val in row) 
            for row in df.values
        ]

        # Inserción masiva
        cursor.executemany(sql_insert, valores)
        conn.commit()

        print(f"¡Éxito! Se insertaron {cursor.rowcount} filas en la tabla '{NOMBRE_TABLA}'.")

        cursor.close()
        conn.close()

    except Error as e:
        print(f"Error durante la carga a MySQL: {e}")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    archivo_csv = os.path.join(BASE_DIR, "archivos", "datos_procesados.csv")
    
    print("Iniciando conexión y migración a MySQL...")
    cargar_csv_a_mysql(archivo_csv)