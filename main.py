import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. CONFIGURACIÓN INICIAL ---
TOKEN = 'TU_TOKEN_DE_BOTFATHER_AQUI' 
ARCHIVO_CREDENCIALES = 'credenciales.json' 
NOMBRE_HOJA = 'DB_Colegio' 

bot = telebot.TeleBot(TOKEN)

permisos = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credenciales = ServiceAccountCredentials.from_json_keyfile_name(ARCHIVO_CREDENCIALES, permisos)
cliente_google = gspread.authorize(credenciales)
hoja_datos = cliente_google.open(NOMBRE_HOJA).sheet1

# Diccionario temporal para guardar las opciones del profesor mientras navega por los menús
tarea_en_proceso = {}

# --- 2. REGISTRO DE ALUMNOS ---
@bot.message_handler(commands=['start'])
def bienvenida(mensaje):
    respuesta = bot.reply_to(mensaje, "¡Hola! Para iniciar, por favor escribe tu *Nombre y Apellido*:")
    bot.register_next_step_handler(respuesta, preguntar_grado)

def preguntar_grado(mensaje):
    nombre_alumno = mensaje.text 
    teclado = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    teclado.add('1ro', '2do', '3ro', '4to', '5to')
    respuesta = bot.send_message(mensaje.chat.id, f"Un gusto, {nombre_alumno}. ¿En qué grado te encuentras?", reply_markup=teclado)
    bot.register_next_step_handler(respuesta, guardar_en_sheets, nombre_alumno)

def guardar_en_sheets(mensaje, nombre_alumno):
    grado_alumno = mensaje.text 
    id_telegram = mensaje.chat.id 
    hoja_datos.append_row([str(id_telegram), nombre_alumno, grado_alumno])
    
    # Quitamos el teclado de botones de la pantalla del alumno
    ocultar_teclado = types.ReplyKeyboardRemove()
    bot.send_message(id_telegram, f"✅ ¡Listo! Te he registrado en {grado_alumno} de secundaria.", reply_markup=ocultar_teclado)


# --- 3. ENVÍO DE TAREAS (INTERACTIVO PARA PROFESORES) ---

# Paso 1: El profe escribe /enviar y el bot le pregunta el grado con botones
@bot.message_handler(commands=['enviar'])
def iniciar_envio(mensaje):
    teclado = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    teclado.add('1ro', '2do', '3ro', '4to', '5to')
    
    respuesta = bot.send_message(mensaje.chat.id, "👨‍🏫 ¿A qué grado quieres enviar la tarea o aviso?", reply_markup=teclado)
    # Pasamos al siguiente paso
    bot.register_next_step_handler(respuesta, seleccionar_curso)

# Paso 2: El profe seleccionó el grado. Ahora el bot pregunta el curso con botones.
def seleccionar_curso(mensaje):
    grado_elegido = mensaje.text
    id_profe = mensaje.chat.id
    
    # Guardamos el grado temporalmente en la "memoria" del bot
    tarea_en_proceso[id_profe] = {'grado': grado_elegido}
    
    teclado = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    # Agregamos los cursos en filas de a dos o tres para que se vea ordenado en el celular
    teclado.row('Física', 'Química', 'Matemáticas')
    teclado.row('Comunicación', 'Biología', 'Religión')
    teclado.row('Inglés', 'Arte', 'Geografía')
    teclado.row('Ed. Cristiana', 'DPCC', 'Historia')
    teclado.row('Ed. Física', 'Psicología', 'Economía')
    
    respuesta = bot.send_message(id_profe, f"Has elegido *{grado_elegido}*. ¿De qué curso es la actividad?", reply_markup=teclado, parse_mode="Markdown")
    # Pasamos al siguiente paso
    bot.register_next_step_handler(respuesta, pedir_texto_tarea)

# Paso 3: El profe seleccionó el curso. Ahora debe escribir la tarea.
def pedir_texto_tarea(mensaje):
    curso_elegido = mensaje.text
    id_profe = mensaje.chat.id
    
    # Guardamos el curso en la memoria
    tarea_en_proceso[id_profe]['curso'] = curso_elegido
    
    # Ocultamos el teclado de botones para que el profe pueda escribir texto libremente
    ocultar_teclado = types.ReplyKeyboardRemove()
    
    respuesta = bot.send_message(id_profe, f"Perfecto. El curso es *{curso_elegido}*.\n\n✍️ Ahora, escribe la descripción de la tarea o el resumen de tu clase:", reply_markup=ocultar_teclado, parse_mode="Markdown")
    # Pasamos al paso final
    bot.register_next_step_handler(respuesta, enviar_tarea_final)

# Paso 4: El bot recibe el texto escrito, busca a los alumnos en Google Sheets y les envía el mensaje.
def enviar_tarea_final(mensaje):
    texto_tarea = mensaje.text
    id_profe = mensaje.chat.id
    
    # Recuperamos los datos guardados en los pasos anteriores
    datos = tarea_en_proceso.get(id_profe)
    grado_destino = datos['grado']
    curso = datos['curso']
    
    try:
        # Descargamos los registros de la base de datos
        todos_los_alumnos = hoja_datos.get_all_records()
        contador_envios = 0
        
        # Buscamos a los alumnos que coincidan con el grado elegido
        for alumno in todos_los_alumnos:
            if str(alumno['Grado']) == grado_destino:
                # Armamos el mensaje final bonito
                notificacion = f"🚨 *AVISO DE CLASE: {curso}*\n\n📝 *Detalle:* {texto_tarea}"
                # Lo enviamos
                bot.send_message(alumno['ID_Telegram'], notificacion, parse_mode="Markdown")
                contador_envios += 1
                
        # Le confirmamos al profesor que todo salió bien
        bot.send_message(id_profe, f"🚀 ¡Éxito! Notificación enviada a {contador_envios} alumnos de {grado_destino}.")
        
        # Limpiamos la memoria de este profesor para su próxima tarea
        del tarea_en_proceso[id_profe]
        
    except Exception as e:
        bot.send_message(id_profe, "❌ Hubo un error al conectar con la base de datos de alumnos.")

# --- 4. INICIO DEL BOT ---
bot.polling()

