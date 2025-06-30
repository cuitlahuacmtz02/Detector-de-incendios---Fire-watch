import tkinter as tk
from tkinter import messagebox, ttk
from ttkbootstrap import Style
import paho.mqtt.client as mqtt
import pandas as pd
import os
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Configuración del broker y variables
broker = "broker.emqx.io"
access_code_topic = "accessCodeTopic"
connected = False

# Inicialización de listas para almacenar los datos de los sensores
gas_data = []
temp_data = []
ir_data = []
dates = []
timestamps = []

class MQTTApp:
    def __init__(self, master):
        self.root = root
        self.master = master
        self.master.title("Fire Watch IoT")
        self.root.geometry("1400x900")
        self.root.config(bg="#2E2E2E")

        # Inicializar el diccionario para almacenar los datos temporales
        self.temp_data_buffer = {"gas": None, "temp": None, "ir": None}
        self.data_buffer = []
        self.code_input = [1,2,3,4]


        # Establecer el estilo de ttkbootstrap
        self.style = Style(theme='darkly')

        # Estilo de fuente
        self.font_large = ('Trebuchet MS', 13, "bold")
        self.font_normal = ('Helvetica', 10, "bold")  # Fuente normal
    # Colores de interfaz    
        self.color_1 = ("#1E1E1E") #color de fondo
        self.color_3 = ("gainsboro") #color de fuente
    # Crear los elementos de la interfaz gráfica

        style = ttk.Style()
        style.configure("Custom.TButton", font=('Trebuchet MS', 13, "bold"))

        BTconf = {
            "fg" : "#B5CEA8", 
            "bg" : "gray19", 
            "activebackground" : "gray19", 
            "activeforeground": "gainsboro",    
            "font": ('Trebuchet MS', 15, "bold")
        }    

        LBconf = {
            "fg" : "gainsboro", 
            "bg" : "#1E1E1E", 
            "font": ('Trebuchet MS', 15, "bold")
        }

        ENTconf = {
            "fg" : "gainsboro", 
            "bg" : "#1E1E1E", 
            "font": ('Trebuchet MS', 15, "bold"), 
            "insertbackground" : "white", 
            "highlightbackground" : "yellow2", 
            "highlightcolor" : "yellow2", 
            "highlightthickness" : "0.5"
        }
        
        self.root.grid_columnconfigure(0, weight=1, minsize=300)  # Columna para controles
        self.root.grid_columnconfigure(1, weight=2, minsize=500)  # Columna para gráficas (más grande)
        self.root.grid_columnconfigure(2, weight=1, minsize=300)  # Columna para labels y barras de progreso

        # Marco principal para contener todo
        frame = tk.Frame(self.master, bg=self.color_1)
        frame.grid(row=0, column=0, columnspan=3, pady=10, sticky="nsew")  # Ajuste proporcional de todo el marco

       # Configuración de marcos dentro del marco principal
        control_frame = tk.Frame(frame, bg="#2E2E2E")
        control_frame.grid(row=0, column=0, padx=100, sticky="nsew", pady=200)  # Ajuste de la proporción de este marco


        # Configuración de widgets en el marco de control
        self.status_label = ttk.Label(control_frame, text="Estado de conexión: Desconectado", bootstyle="danger", font=('Trebuchet MS', 15, "bold"))
        self.status_label.grid(row=0, column=0, pady=5)

        self.connect_button = tk.Button(control_frame, text="Iniciar Conexión", **BTconf, command=self.connect_broker).grid(row=3, column=0, pady=10)
        self.disconnect_button = tk.Button(control_frame, text="Cerrar Conexión", **BTconf,command=self.disconnect_broker).grid(row=4, column=0, pady=10)
        self.save_button = tk.Button(control_frame, text="Guardar Datos", **BTconf, command=self.save_data).grid(row=5, column=0, pady=10)

        # Marco central para gráficas
        graph_frame = tk.Frame(frame, bg="#2E2E2E")
        graph_frame.grid(row=0, column=1, padx=50, pady=10, sticky="nsew")  # Ajuste proporcional para gráficos

        # Configuración de las gráficas en tiempo real
        self.fig, (self.ax_gas, self.ax_temp, self.ax_ir) = plt.subplots(3, 1, figsize=(6.5, 9.5))
        self.fig.patch.set_facecolor("#2E2E2E")
        self.fig.tight_layout(pad=4.0)

        for ax, ylabel in zip([self.ax_gas, self.ax_temp, self.ax_ir], ["CO (ppm)", "Temperatura (°C)", "IR"]):
            ax.set_facecolor("#2E2E2E")
            ax.set_ylabel(ylabel, color="white")
            ax.tick_params(colors="white")
            for spine in ax.spines.values():
                spine.set_color("white")

        # Configuración de cada eje Y
        self.ax_gas.set_ylim(0, 1000)  # Límite del eje Y para el gráfico de gas
        self.ax_gas.set_ylabel("CO (ppm)", color="white", fontsize=13)
        self.ax_gas.set_yticks(range(0, 1100, 200))  # Intervalo de 5 en 5 en el eje Y

        self.ax_temp.set_ylim(0, 100)  # Límite del eje Y para el gráfico de temperatura
        self.ax_temp.set_ylabel("Temperatura (°C)", color="white", fontsize=13)
        self.ax_temp.set_yticks(range(0, 101, 20))  # Intervalo de 20 en 20 en el eje Y

        self.ax_ir.set_ylim(0, 1500)  # Límite del eje Y para el gráfico de infrarrojo
        self.ax_ir.set_ylabel("IR", color="white", fontsize=13)
        self.ax_ir.set_yticks(range(0, 1600, 300))  # Intervalo de 300 en 300 en el eje Y

        #Agregar cuadrícula a cada gráfico
        self.ax_gas.grid(True, which='both', axis='both', color='gray', linestyle='--', linewidth=0.5)
        self.ax_temp.grid(True, which='both', axis='both', color='gray', linestyle='--', linewidth=0.5)
        self.ax_ir.grid(True, which='both', axis='both', color='gray', linestyle='--', linewidth=0.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0)
        graph_frame.grid_rowconfigure(0, weight=1)
        graph_frame.grid_columnconfigure(0, weight=1)

        # Marco derecho para los indicadores y barras de progreso
        indicator_frame = tk.Frame(frame, bg="#2E2E2E")
        indicator_frame.grid(row=0, column=2, padx=100, pady=185, sticky="nsew")  # Ajuste proporcional para indicadores

        self.esp32_label_3 = ttk.Label(indicator_frame, text="Estado del Area: Libre de Riesgo", bootstyle="success", font=('Trebuchet MS', 15, "bold"), width=30)
        self.esp32_label_3.grid(row=0, column=0)

        self.correo_estatus = ttk.Label(indicator_frame, text="Correo electronico: En espera....", bootstyle="PRIMARY", font=('Trebuchet MS', 15, "bold"), width=30)
        self.correo_estatus.grid(row=1, column=0)

        self.gas_label = tk.Label(indicator_frame, text="Nivel de Humo (CO): ---", **LBconf, width=30, height=2)
        self.gas_label.grid(row=2, column=0, pady=5)
        self.gas_progress = ttk.Progressbar(indicator_frame, orient="horizontal", length=200, mode="determinate", maximum=1500)
        self.gas_progress.grid(row=3, column=0, pady=5)
        self.gas_progress.configure(style="gas.Horizontal.TProgressbar")

        self.temp_label = tk.Label(indicator_frame, text="Temperatura (°C): ---", **LBconf, width=30, height=2)
        self.temp_label.grid(row=4, column=0, pady=5)
        self.temp_progress = ttk.Progressbar(indicator_frame, orient="horizontal", length=200, mode="determinate", maximum=100)
        self.temp_progress.grid(row=5, column=0, pady=5)
        self.temp_progress.configure(style="temp.Horizontal.TProgressbar")

        self.ir_label = tk.Label(indicator_frame, text="Radiación Infrarroja: ---", **LBconf, width=30, height=2)
        self.ir_label.grid(row=6, column=0, pady=5)
        self.ir_progress = ttk.Progressbar(indicator_frame, orient="horizontal", length=200, mode="determinate", maximum=1400)
        self.ir_progress.grid(row=7, column=0, pady=5)
        self.ir_progress.configure(style="ir.Horizontal.TProgressbar")

        style = ttk.Style()
        style.configure("gas.Horizontal.TProgressbar", troughcolor="#2E2E2E", background="red")
        style.configure("temp.Horizontal.TProgressbar", troughcolor="#2E2E2E", background="green")
        style.configure("ir.Horizontal.TProgressbar", troughcolor="#2E2E2E", background="blue")


    def connect_broker(self):
        global connected
        access_code = 1234

        if not connected:
            self.client = mqtt.Client(client_id="", clean_session=True)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.connect(broker, 1883, 60)
            self.client.loop_start()
            self.client.publish(access_code_topic, access_code)
            self.status_label.config(text="Verificando acceso...",  bootstyle="PRIMARY", font=('Trebuchet MS', 15, "bold"))

    def disconnect_broker(self):
        global connected
        if connected:
            self.client.unsubscribe("outTopic1")
            self.client.unsubscribe("outTopic2")
            self.client.unsubscribe("outTopic3")
            self.client.unsubscribe("connectionStatus")
            self.client.loop_stop()
            self.client.disconnect()
            connected = False
            self.status_label.config(text="Estado de conexión: Desconectado", bootstyle="danger", font=('Trebuchet MS', 15, "bold"))

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe("outTopic1")
        self.client.subscribe("outTopic2")
        self.client.subscribe("outTopic3")
        self.client.subscribe("connectionStatus")
        self.client.subscribe("alertTopic")  # Suscribirse al tópico de alerta

    def on_message(self, client, userdata, msg):
        global connected
        message = msg.payload.decode().strip()  # Decodificar y eliminar espacios en blanco

        if msg.topic == "connectionStatus":
            if message == "Access Granted":
                connected = True
                self.status_label.config(text="Estado de conexión: Conectado", bootstyle="success", font=('Trebuchet MS', 15, "bold"))
                print("Acceso concedido, conexión establecida.")
            else:
                connected = False
                self.status_label.config(text="Acceso denegado", bootstyle="danger", font=('Trebuchet MS', 15, "bold"))
                messagebox.showerror("Error", "Código de acceso inválido. Por favor, inténtelo de nuevo.")

        if msg.topic in ["outTopic1", "outTopic2", "outTopic3"] and connected == True:
            # Extraer el valor numérico del mensaje
            try:
                if ":" in message:  # Si el mensaje tiene formato clave:valor
                    _, value_str = message.split(":")  # Dividir en clave y valor
                    value = float(value_str.strip())   # Convertir el valor a float
                else:
                    value = float(message)  # Intentar convertir directamente si es un número

                # Actualizar el dato y la interfaz según el tópico
                if msg.topic == "outTopic1":
                    self.gas_label.config(text=f"Nivel de CO: {value} ppm")
                    self.gas_progress['value'] = value
                    self.temp_data_buffer["gas"] = value
                elif msg.topic == "outTopic2":
                    self.temp_label.config(text=f"Temperatura: {value} °C")
                    self.temp_progress['value'] = value
                    self.temp_data_buffer["temp"] = value
                elif msg.topic == "outTopic3":
                    self.ir_label.config(text=f"Radiación Infrarroja: {value}")
                    self.ir_progress['value'] = value
                    self.temp_data_buffer["ir"] = value

            except ValueError:
                print(f"Mensaje inválido recibido en {msg.topic}: {message}")

        elif msg.topic == "alertTopic" and connected == True:
            print(f"Mensaje de alerta recibido: {message}")
            if message == "AL1":
                alerta = "Incendio detectado. Verifique el área 1."
                self.esp32_label_3.config(text="Estado del Area: Incendio detectado", bootstyle="danger", font=('Trebuchet MS', 15, "bold"))
            elif message == "AL2":
                alerta = "Incendio detectado. Verifique el área 2."
                self.esp32_label_3.config(text="Estado del Area: Incendio detectado", bootstyle="danger", font=('Trebuchet MS', 15, "bold"))
            elif message == "AL3":
                alerta = "Incendio detectado. Verifique el área 3."
                self.esp32_label_3.config(text="Estado del Area: Incendio detectado", bootstyle="danger", font=('Trebuchet MS', 15, "bold"))
            else:
                alerta = f"Código de alerta desconocido: {message}"

            self.send_email_alert(alerta)
            messagebox.showwarning("Alerta del Sistema", alerta)

        # Si todos los datos han sido recibidos, actualiza las gráficas
        if all(self.temp_data_buffer.values()) and connected == True:
            gas_data.append(self.temp_data_buffer["gas"])
            temp_data.append(self.temp_data_buffer["temp"])
            ir_data.append(self.temp_data_buffer["ir"])
            timestamps.append(datetime.datetime.now().strftime('%H:%M:%S'))
            dates.append(datetime.datetime.now().strftime('%Y-%m-%d'))
            self.temp_data_buffer = {"gas": None, "temp": None, "ir": None}
            self.update_graph()
            

    def send_email_alert(self, alert_message):
        PASSWORD_APP = 'XXXXXXX'  # Usa la contraseña de aplicación generada
        EMAIL = 'XXXXXXX'  # Dirección de correo del remitente
        # Configuración del servidor SMTP
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        try:
            # Crear mensaje de correo
            subject = "Alerta del Sistema de Detección de Incendios, Fire Watch IoT"
            body = f"Se recibió una alerta de incendio en el area, Dirección: Cam. Arenero 1101, 45019 Zapopan, Jal. Hay mulples personas en peligro"
            msg = MIMEText(body, "plain")
            msg["Subject"] = subject
            msg["From"] = EMAIL
            msg["To"] = "XXXXXXXXXX"  # Destinatario
            # Establecer conexión con el servidor SMTP
            conexion = smtplib.SMTP(host=smtp_server, port=smtp_port)
            conexion.ehlo()
            conexion.starttls()
            conexion.login(user=EMAIL, password=PASSWORD_APP)
            # Enviar correo
            conexion.sendmail(from_addr=EMAIL, to_addrs="XXXXXXXXXXX", msg=msg.as_string())
            conexion.quit()
            print("Correo enviado con éxito.")
            self.correo_estatus.config(text="Correo electronico: enviado", bootstyle="success", font=('Trebuchet MS', 15, "bold"), width=30)
        except Exception as e:
            print(f"Error al enviar el correo: {e}")
            self.correo_estatus.config(text="Correo electronico: error, no se envio", bootstyle="danger", font=('Trebuchet MS', 15, "bold"), width=30)

    def update_graph(self):
        # Limpiar y actualizar cada gráfico con nuevos datos
        self.ax_gas.cla()  # Limpiar gráfico de gas
        self.ax_temp.cla()  # Limpiar gráfico de temperatura
        self.ax_ir.cla()  # Limpiar gráfico de IR

         # Crear un rango de índices para el eje X
        x_vals = range(len(temp_data[-30:]))  # Últimos 30 datos

        # Mostrar solo los últimos 30 datos
        self.ax_gas.plot(x_vals, gas_data[-30:], color="red")
        self.ax_temp.plot(x_vals, temp_data[-30:], color="green")
        self.ax_ir.plot(x_vals, ir_data[-30:], color="blue")

       # Reconfigurar ejes Y para mantener los parámetros deseados
        self.ax_gas.set_ylim(0, 1000)
        self.ax_gas.set_ylabel("CO (ppm)", color="white", fontsize=13)
        self.ax_gas.set_yticks(range(0, 1100, 200))

        self.ax_temp.set_ylim(0, 100)
        self.ax_temp.set_ylabel("Temperatura (°C)", color="white", fontsize=13)
        self.ax_temp.set_yticks(range(0, 101, 20))

        self.ax_ir.set_ylim(0, 1400)
        self.ax_ir.set_ylabel("IR", color="white", fontsize=13)
        self.ax_ir.set_yticks(range(0, 1500, 300))

         #Agregar cuadrícula a cada gráfico
        self.ax_gas.grid(True, which='both', axis='both', color='gray', linestyle='--', linewidth=0.5)
        self.ax_temp.grid(True, which='both', axis='both', color='gray', linestyle='--', linewidth=0.5)
        self.ax_ir.grid(True, which='both', axis='both', color='gray', linestyle='--', linewidth=0.5)

        # Actualizar el canvas de la gráfica
        self.canvas.draw()

    def save_data(self):
        if gas_data and temp_data and ir_data:
            df = pd.DataFrame({
                'Fecha': dates,
                'Hora': timestamps,
                'Nivel de CO': gas_data,
                'Temperatura': temp_data,
                'Radiación Infrarroja': ir_data
            })

            file_path = "sensor_data.xlsx"
            if os.path.exists(file_path):
                existing_data = pd.read_excel(file_path)
                df = pd.concat([existing_data, df], ignore_index=True)

            df.to_excel(file_path, index=False)
            messagebox.showinfo("Éxito", "Datos guardados correctamente.")
        else:
            messagebox.showerror("Error", "No hay datos para guardar.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MQTTApp(root)
    root.mainloop()
