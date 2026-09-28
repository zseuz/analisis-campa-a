"""
ETL - Procesamiento del extracto de mensajería (prueba.txt)

Este script toma el archivo crudo que nos pasaron del sistema transaccional
y lo deja listo para cargar a la base de datos. Básicamente hace 3 cosas:

1. Limpia el archivo (viene con separador '|' y trae basura en los bordes).
2. Saca el error real y la plantilla usada de los mensajes que fallaron
   (esa info viene metida como JSON dentro de un campo de texto).
3. Clasifica los mensajes que nos escriben los clientes por tema, usando
   palabras clave (nada de ML, solo reglas simples).
   
"""

import os
import io
import json
import re
import pandas as pd


# =============================================================================
# 1. LIMPIEZA DEL ARCHIVO
# =============================================================================

def cargar_y_limpiar_transaccional(filepath: str) -> pd.DataFrame:
    """
    Carga el prueba.txt (separado por '|') en un DataFrame ya limpio.

    Cosas que tuve que resolver aquí:
    - El archivo no venía en UTF-8 "de forma automática" para pandas, así
      que lo abro en binario y lo decodifico yo mismo. Si no hacía esto me
      salían las tildes y la ñ todas raras (tipo Ã³, Ã±).
    - Trae líneas que son puro adorno, tipo separadores de tabla
      (|------|------|). Esas no son datos, hay que botarlas antes de que
      pandas intente leerlas o se arma un desastre.
    - Como el texto de los mensajes puede traer comillas sueltas, le puse
      quoting=3 para que pandas no las confunda con delimitadores.
    """
    lineas_limpias = []

    # Abro en binario para controlar yo la decodificación en vez de dejar
    # que el sistema adivine mal la codificación.
    with open(filepath, 'rb') as f:
        contenido_bytes = f.read()

    # Si hay algún byte raro que no decodifica bien, lo reemplaza en vez de
    # tronar todo el script por un solo carácter.
    contenido_texto = contenido_bytes.decode('utf-8', errors='replace')

    for line in contenido_texto.splitlines():
        line_str = line.strip()

        # Descarto líneas vacías y las que son solo '|' y '-' (los
        # separadores de la tabla, no son fila de datos real).
        es_linea_decorativa = set(line_str.replace('|', '').strip()).issubset({'-'})
        if line_str and not es_linea_decorativa:
            lineas_limpias.append(line_str)

    # Armo un buffer en memoria en vez de guardar un archivo temporal aparte.
    buffer_texto = io.StringIO("\n".join(lineas_limpias))

    df = pd.read_csv(
        buffer_texto,
        sep='|',
        dtype=str,           # todo entra como texto, los tipos los ajusto
                              # después en la base de datos.
        engine='python',     # el motor python tolera mejor delimitadores
                              # raros que el motor c.
        quoting=3,            # csv.QUOTE_NONE, ignora comillas como si
                              # fueran texto normal.
        on_bad_lines='skip'   # si alguna fila viene rota, la salto y sigo,
                              # prefiero perder una fila rara que tumbar
                              # todo el proceso.
    )

    # El archivo trae un '|' al inicio y al final de cada línea, entonces
    # queda una columna vacía fantasma a cada lado. Con esto las boto.
    df = df.dropna(how='all', axis=1)

    # Quito espacios de los nombres de columna y descarto las que quedaron
    # sin nombre.
    df.columns = [col.strip() for col in df.columns if col.strip()]

    # Limpio cada celda: espacios, comillas sobrantes, y normalizo los
    # distintos "nulos" (nan, None, vacío) a un None real para que no se
    # traten como texto válido más adelante.
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].str.strip('"').str.strip("'")
        df[col] = df[col].replace({'nan': None, 'None': None, '<NA>': None, '': None})

    return df


# =============================================================================
# 2. SACAR EL ERROR Y LA PLANTILLA DE LOS MENSAJES FALLIDOS
# =============================================================================

def parsear_json_atributos(df: pd.DataFrame) -> pd.DataFrame:
    """
    De los mensajes que fallaron, saca dos cosas que vienen escondidas
    dentro de un JSON metido como texto:

    - error_exacto: el motivo real por el que no llegó el mensaje.
    - nombre_plantilla: qué plantilla de WhatsApp se usó.

    El JSON no siempre viene bien formado (a veces con comillas escapadas
    de más o cortado), así que primero intento parsearlo normal y si eso
    falla busco el dato directo con regex sobre el texto crudo. Prefiero
    esto a simplemente descartar la fila cuando el JSON viene medio raro.
    """

    def _parse_json_field(val):
        """Intenta convertir el texto a dict, si no se puede devuelve {}."""
        if not val or not isinstance(val, str):
            return {}
        # Algunos registros vienen con \" en vez de ", los normalizo antes
        # de intentar parsear.
        val_clean = val.replace('\\"', '"').strip()
        if not val_clean.startswith('{'):
            return {}
        try:
            return json.loads(val_clean)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _obtener_error(row):
        """
        Solo aplica a mensajes con status='failed'. Reviso primero
        'content' y luego 'content_attributes' porque el sistema origen no
        siempre guarda el error en la misma columna.
        """
        if row.get('status') != 'failed':
            return None

        for col in ['content', 'content_attributes']:
            val = row.get(col)
            if val:
                data = _parse_json_field(val)
                if 'external_error' in data:
                    return data['external_error']
                # si el JSON no parseó pero el patrón sí está en el texto
                # crudo, lo saco igual con regex.
                match = re.search(r'"external_error"\s*:\s*"([^"]+)"', str(val))
                if match:
                    return match.group(1)
        return None

    def _obtener_plantilla(row):
        """
        Saca el nombre de la plantilla desde 'additional_attributes'.

        Ojo: el regex de respaldo busca cualquier "name" en el string, no
        solo dentro de template_params. Como solo entra ahí cuando el JSON
        ya falló, el riesgo es bajo, pero si el JSON tuviera otro campo
        "name" (por ejemplo el nombre de un contacto) podría traer el dato
        equivocado. Con datos más limpios valdría la pena acotarlo más.
        """
        val = row.get('additional_attributes')
        if val:
            data = _parse_json_field(val)
            name = data.get('template_params', {}).get('name')
            if name:
                return name
            match = re.search(r'"name"\s*:\s*"([^"]+)"', str(val))
            if match:
                return match.group(1)
        return None

    df['error_exacto'] = df.apply(_obtener_error, axis=1)
    df['nombre_plantilla'] = df.apply(_obtener_plantilla, axis=1)

    return df


# =============================================================================
# 3. CLASIFICAR LOS MENSAJES QUE ESCRIBEN LOS CLIENTES
# =============================================================================

def clasificar_mensajes_incoming(df: pd.DataFrame) -> pd.DataFrame:
    """
    A cada mensaje entrante (message_type='incoming') le asigno una
    categoría según palabras clave. Es un clasificador simple por reglas,
    no un modelo de NLP real, pero para el alcance de este ejercicio
    cumple.

    El orden en que reviso las categorías importa: primero Queja/Reclamo,
    después Pedido/Ventas, y de último Soporte/Información. Lo hice así
    porque una queja normalmente también trae palabras de soporte ("ayuda",
    "asesor"), y prefiero que se marque como queja antes que se pierda en
    una categoría más neutra.

    Nota honesta: al validar contra la base real, como el 87% de los
    mensajes terminó en "Consulta General". Eso me dice que el diccionario
    de palabras todavía es corto y habría que ampliarlo con una muestra más
    grande de mensajes reales (sinónimos, errores de tipeo comunes, etc.)
    antes de confiar en esto para producción.
    """
    reglas = {
        'Queja/Reclamo': re.compile(
            r'\b(cobraron|inconforme|no lleg[oó]|error|factura|mala|cobro|reclamo|fallo)\b',
            re.IGNORECASE
        ),
        'Pedido/Ventas': re.compile(
            r'\b(pedido|comprar|cat[aá]logo|cat[aá]logos|ofertas|precio|agendar|ingreso|compras)\b',
            re.IGNORECASE
        ),
        # Le quité la palabra "como" que tenía antes porque salía en
        # cualquier mensaje ("¿cómo hago un pedido?", "no sé cómo...") y
        # me estaba inflando esta categoría sin que tuviera que ver con
        # soporte de verdad.
        'Soporte/Informacion': re.compile(
            r'\b(hola|ayuda|llame|llamada|informaci[oó]n|asesor|l[ií]der|servicio)\b',
            re.IGNORECASE
        )
    }

    def _categorizar(texto):
        if not texto or pd.isna(texto):
            return "Sin Contenido"

        for categoria, patron in reglas.items():
            if patron.search(str(texto)):
                return categoria

        return "Consulta General"

    df['categoria_cliente'] = df.apply(
        lambda r: _categorizar(r['content']) if r.get('message_type') == 'incoming' else None,
        axis=1
    )

    return df


# =============================================================================
# 4. UN VISTAZO RÁPIDO A CÓMO QUEDÓ TODO
# =============================================================================

def imprimir_diagnostico(df: pd.DataFrame) -> None:
    """
    Solo imprime un resumen para revisar que el proceso corrió bien: cuántas
    filas se procesaron, cuántos errores se lograron extraer, etc. No toca
    el DataFrame, es solo para verificar a simple vista antes de guardar.
    """
    total_filas = len(df)
    total_outgoing = (df['message_type'] == 'outgoing').sum()
    total_incoming = (df['message_type'] == 'incoming').sum()
    total_failed = (df['status'] == 'failed').sum()
    total_error_extraido = df['error_exacto'].notna().sum()
    total_plantilla_extraida = df['nombre_plantilla'].notna().sum()
    total_categorizados = df.loc[
        df['message_type'] == 'incoming', 'categoria_cliente'
    ].notna().sum()

    print("\n" + "=" * 60)
    print("RESUMEN DEL PROCESO")
    print("=" * 60)
    print(f"Total de filas procesadas:            {total_filas}")
    print(f"  - Mensajes outgoing:                 {total_outgoing}")
    print(f"  - Mensajes incoming:                 {total_incoming}")
    print(f"Mensajes con status 'failed':          {total_failed}")
    print(f"  - Con error_exacto extraído:          {total_error_extraido} "
          f"({(total_error_extraido / total_failed * 100 if total_failed else 0):.1f}% de los failed)")
    print(f"Mensajes con nombre_plantilla extraído: {total_plantilla_extraida}")
    print(f"Mensajes incoming categorizados:        {total_categorizados} "
          f"({(total_categorizados / total_incoming * 100 if total_incoming else 0):.1f}% de los incoming)")
    print("=" * 60 + "\n")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    archivo_origen = os.path.join(BASE_DIR, "archivos", "prueba.txt")
    archivo_salida = os.path.join(BASE_DIR, "archivos", "datos_procesados.csv")

    print(f"Iniciando transformación ETL desde: {archivo_origen}")

    # Los 3 pasos, uno detrás del otro.
    df_raw = cargar_y_limpiar_transaccional(archivo_origen)
    df_parsed = parsear_json_atributos(df_raw)
    df_final = clasificar_mensajes_incoming(df_parsed)

    # Reviso el resultado antes de exportar, para asegurarme que quedó
    # bien antes de escribir el CSV.
    imprimir_diagnostico(df_final)

    # Quito saltos de línea sueltos dentro del texto de los mensajes,
    # porque si no se rompe el CSV o se ve feo en Excel.
    for col in df_final.columns:
        df_final[col] = df_final[col].astype(str).str.replace('\n', ' ').str.replace('\r', '')
        df_final[col] = df_final[col].replace({'nan': None, 'None': None})

    # utf-8-sig para que Excel abra bien el archivo sin dañar tildes ni
    # emojis (sin esto Excel a veces muestra los caracteres especiales mal).
    df_final.to_csv(
        archivo_salida,
        index=False,
        encoding='utf-8-sig',
        doublequote=True,
        quoting=1  # QUOTE_ALL, para no tener problemas con comas o saltos
                   # de línea dentro del texto libre de los mensajes.
    )
    print(f"Transformación completada con éxito. Archivo CSV limpio generado en: {archivo_salida}")
