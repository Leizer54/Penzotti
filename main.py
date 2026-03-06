import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN INICIAL ---
TOKEN = 'TU_TOKEN_DE_BOTFATHER_AQUI' 
ARCHIVO_CREDENCIALES = 'credenciales.json' 
NOMBRE_HOJA = 'DB_Colegio' 

# 🚨 LISTA DE SEGURIDAD 🚨
# Aquí pondrás tu ID de Telegram y el de los otros profesores.
# Por ahora he puesto números de ejemplo.
PROFESORES_AUTORIZADOS = [123456789, 987654321]

bot = telebot.TeleBot(TOKEN)

# Conexión con Google Sheets
permisos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credenciales = ServiceAccountCredentials.from_json_keyfile_name(ARCHIVO_CREDENCIALES, permisos)
cliente_google = gspread.authorize(credenciales)
hoja_datos = cliente_google.open(NOMBRE_HOJA).sheet1

tarea_en_proceso = {}

# --- HERRAMIENTA PARA PROFESORES ---
# Comando oculto para saber tu ID y agregarlo a la lista de seguridad
@bot.message_handler(commands=['mi_id'])
def obtener_id(mensaje):
    id_usuario = mensaje.chat.id
    bot.reply_to(mensaje, f"🕵️‍♂️ Tu ID secreto de Telegram es:\n`{id_usuario}`\n\nCopia este número y ponlo en la lista PROFESORES_AUTORIZADOS del código.", parse_mode="Markdown")

# --- 2. REGISTRO DE ALUMNOS ---
@bot.message_handler(commands=['start'])
def bienvenida(mensaje):
    respuesta = bot.reply_to(mensaje, "¡Hola, Dios te bendiga! Para iniciar, por favor escribe tu *Nombre y Apellido*:")
    bot.register_next_step_handler(respuesta, preguntar_grado)

def preguntar_grado(mensaje):
    nombre_alumno = mensaje.text 
    teclado = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    teclado.add('1ro', '2do', '3ro', '4to', '5to')
    respuesta = bot.send_message(mensaje.chat.id, f"Un gusto, {nombre_alumno}. ¿En qué grado estás?", reply_markup=teclado)
    bot.register_next_step_handler(respuesta, guardar_en_sheets, nombre_alumno)

def guardar_en_sheets(mensaje, nombre_alumno):
    grado_alumno = mensaje.text 
    id_telegram = mensaje.chat.id 
    
    try:
        hoja_datos.append_row([str(id_telegram), nombre_alumno, grado_alumno])
        ocultar_teclado = types.ReplyKeyboardRemove()
        bot.send_message(id_telegram, f"✅ ¡Listo! Te he registrado en {grado_alumno} de secundaria.", reply_markup=ocultar_teclado)
    except Exception as e:
        bot.send_message(id_telegram, "❌ Hubo un error al registrarte. Intenta de nuevo más tarde.")

# --- 3. ENVÍO DE TAREAS (INTERACTIVO Y SEGURO) ---

# Paso 1: El profe escribe /enviar y el bot verifica si tiene permiso
@bot.message_handler(commands=['enviar'])
def iniciar_envio(mensaje):
    id_usuario = mensaje.chat.id
    
    # 🔒 VERIFICACIÓN DE SEGURIDAD 🔒
    if id_usuario not in PROFESORES_AUTORIZADOS:
        bot.reply_to(mensaje, "⛔ *Acceso Denegado*\nNo tienes permiso para enviar tareas. Si eres profesor, usa el comando /mi_id y pide al administrador que te agregue.", parse_mode="Markdown")
        return # Esto detiene el proceso aquí mismo

    # Si pasa la seguridad, mostramos los botones de grados
    teclado = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    teclado.add('1ro', '2do', '3ro', '4to', '5to')
    
    respuesta = bot.send_message(id_usuario, "👨‍🏫 *Modo Profesor Activado*\n¿A qué grado quieres enviar la tarea o aviso?", reply_markup=teclado, parse_mode="Markdown")
    bot.register_next_step_handler(respuesta, seleccionar_curso)

# Paso 2: Seleccionar curso
def seleccionar_curso(mensaje):
    grado_elegido = mensaje.text
    id_profe = mensaje.chat.id
    
    tarea_en_proceso[id_profe] = {'grado': grado_elegido}
    
    teclado = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    teclado.row('Física', 'Química', 'Matemáticas')
    teclado.row('Comunicación', 'Biología', 'Religión')
    teclado.row('Inglés', 'Arte', 'Ed. Cristiana')
    teclado.row('Historia', 'Geografía', 'Economía')
    teclado.row('DPCC', 'Ed. Física', 'Psicología')
    
    respuesta = bot.send_message(id_profe, f"Has elegido *{grado_elegido}*. ¿De qué curso es la actividad?", reply_markup=teclado, parse_mode="Markdown")
    bot.register_next_step_handler(respuesta, pedir_texto_tarea)

# Paso 3: Escribir tarea
def pedir_texto_tarea(mensaje):
    curso_elegido = mensaje.text
    id_profe = mensaje.chat.id
    
    tarea_en_proceso[id_profe]['curso'] = curso_elegido
    
    ocultar_teclado = types.ReplyKeyboardRemove()
    respuesta = bot.send_message(id_profe, f"Perfecto. El curso es *{curso_elegido}*.\n\n✍️ Ahora, escribe la descripción de la tarea o el resumen de tu clase:", reply_markup=ocultar_teclado, parse_mode="Markdown")
    bot.register_next_step_handler(respuesta, enviar_tarea_final)

# Paso 4: Enviar a la base de datos
def enviar_tarea_final(mensaje):
    texto_tarea = mensaje.text
    id_profe = mensaje.chat.id
    
    datos = tarea_en_proceso.get(id_profe)
    grado_destino = datos['grado']
    curso = datos['curso']
    
    try:
        bot.send_message(id_profe, "⏳ Procesando envío... conectando con la base de datos...")
        todos_los_alumnos = hoja_datos.get_all_records()
        contador_envios = 0
        
        for alumno in todos_los_alumnos:
            if str(alumno['Grado']) == grado_destino:
                notificacion = f"🚨 *AVISO DE CLASE: {curso}*\n\n📝 *Detalle:* {texto_tarea}"
                try:
                    bot.send_message(alumno['ID_Telegram'], notificacion, parse_mode="Markdown")
                    contador_envios += 1
                except:
                    pass # Si un alumno bloqueó el bot, lo ignoramos y seguimos
                
        bot.send_message(id_profe, f"🚀 ¡Éxito! Notificación enviada a {contador_envios} alumnos de {grado_destino}.")
        del tarea_en_proceso[id_profe]
        
    except Exception as e:
        bot.send_message(id_profe, "❌ Hubo un error al conectar con la base de datos. Verifica tus credenciales de Google.")

# --- 4. INICIO DEL BOT ---
bot.polling()
