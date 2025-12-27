import cv2
import pyautogui
import numpy as np
import customtkinter as ctk
import mss
from pynput import keyboard
import threading
import os
import time
import json

# --- CARPETAS ---
for carpeta in ['patrones', 'debug']:
    if not os.path.exists(carpeta): os.makedirs(carpeta)

# --- VARIABLES GLOBALES ---
config_mesa = {"top": 0, "left": 0, "width": 100, "height": 100}
puntos_mesa = []
capturas_puntos = []
coord_item = None
coord_java_txt = None
imagen_full = None

def ordenar_puntos(pts):
    pts = np.array(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def mouse_callback_lupa(event, x, y, flags, param):
    global puntos_mesa, imagen_full
    img_display = imagen_full.copy()
    z_size, p_see = 250, 15
    x1, y1 = max(0, x - p_see), max(0, y - p_see)
    x2, y2 = min(img_display.shape[1], x + p_see), min(img_display.shape[0], y + p_see)
    patch = imagen_full[y1:y2, x1:x2]
    if patch.size > 0:
        lupa = cv2.resize(patch, (z_size, z_size), interpolation=cv2.INTER_NEAREST)
        img_display[20:20+z_size, 20:20+z_size] = lupa
        cv2.rectangle(img_display, (20, 20), (20+z_size, 20+z_size), (255, 255, 255), 2)
        c = 20 + (z_size // 2)
        cv2.line(img_display, (c - 15, c), (c + 15, c), (0, 0, 255), 2)
        cv2.line(img_display, (c, c - 15), (c, c + 15), (0, 0, 255), 2)
    for p in puntos_mesa:
        cv2.circle(img_display, p, 5, (0, 255, 0), -1)
    if event == cv2.EVENT_LBUTTONDOWN:
        puntos_mesa.append((x, y))
        if len(puntos_mesa) == 4: param['terminado'] = True
    cv2.imshow("CALIBRACION MESA", img_display)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MC to Enchantment Cracker Bridge")
        self.geometry("500x850")
        ctk.set_appearance_mode("dark")

        # PASO 1
        ctk.CTkLabel(self, text="Paso 1: Minecraft", font=("Arial", 16, "bold"), text_color="#00FF00").pack(pady=10)
        self.btn_mesa = ctk.CTkButton(self, text="Calibrar Mesa", command=self.calibrar_mesa)
        self.btn_mesa.pack(pady=5)
        
        self.lbl_coords_mesa = ctk.CTkLabel(self, text="Mesa: No calibrada", font=("Arial", 10))
        self.lbl_coords_mesa.pack()

        self.btn_ver = ctk.CTkButton(self, text="Ver Verificación (Mosaico)", fg_color="#333333", command=self.mostrar_marcadores_mesa, state="disabled")
        self.btn_ver.pack(pady=5)

        espaciador = ctk.CTkFrame(self, height=4, fg_color="transparent")
        espaciador.pack(pady=5)

        self.btn_item = ctk.CTkButton(self, text="Calibrar Slot Item", command=self.calibrar_item)
        self.btn_item.pack(pady=5)

        self.lbl_coords_itemslot = ctk.CTkLabel(self, text="Item Slot: No calibrado", font=("Arial", 10))
        self.lbl_coords_itemslot.pack()

        self.btn_ver_itemslot = ctk.CTkButton(self, text="Ver Item Slot", fg_color="#333333", command=self.ver_item_slot, state="disabled")
        self.btn_ver_itemslot.pack(pady=5)

        # PASO 2
        ctk.CTkLabel(self, text="Paso 2: Programa Java", font=("Arial", 16, "bold"), text_color="#5dade2").pack(pady=10)
        self.btn_java = ctk.CTkButton(self, text="Calibrar Textbox Cracker (Fila 1)", fg_color="#2e86c1", command=self.calibrar_java)
        self.btn_java.pack(pady=5)
        
        ctk.CTkLabel(self, text="Offset Vertical (px entre filas):", font=("Arial", 12)).pack(pady=(5,0))
        self.offset_slider = ctk.CTkSlider(self, from_=10, to=40, number_of_steps=30, command=self.actualizar_offset_label)
        self.offset_slider.set(20)
        self.offset_slider.pack(pady=5)
        self.lbl_offset = ctk.CTkLabel(self, text="20 px", font=("Arial", 10))
        self.lbl_offset.pack()

        self.btn_check_points = ctk.CTkButton(self, text="Verificar Puntos Clic", fg_color="#5dade2", text_color="black", command=self.ver_puntos_java)
        self.btn_check_points.pack(pady=5)

        self.lbl_java = ctk.CTkLabel(self, text="Textbox Java: No definido", font=("Arial", 11))
        self.lbl_java.pack()

        # BOTON PRINCIPAL 10 CICLOS
        self.btn_bot = ctk.CTkButton(self, text="INICIAR 10 CICLOS", command=self.toggle_bot, fg_color="green", height=60, font=("Arial", 18, "bold"))
        self.btn_bot.pack(pady=20)

        # --- NUEVO APARTADO: PASO 3 (Advances) ---
        ctk.CTkLabel(self, text="Paso 3: Advances", font=("Arial", 16, "bold"), text_color="#f39c12").pack(pady=15)
        
        self.frame_reseteo = ctk.CTkFrame(self)
        self.frame_reseteo.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(self.frame_reseteo, text="Advances:").pack(side="left", padx=10, pady=10)
        self.txt_cantidad_reseteo = ctk.CTkEntry(self.frame_reseteo, width=60)
        self.txt_cantidad_reseteo.insert(0, "1")
        self.txt_cantidad_reseteo.pack(side="left", padx=10, pady=10)

        self.st_label = ctk.CTkLabel(self, text="Esperando...", text_color="#f39c12")
        self.st_label.pack(pady=10)

        self.btn_reseteo_manual = ctk.CTkButton(self, text="INICIAR", fg_color="#e67e22", hover_color="#d35400", command=self.iniciar_reseteo_thread)
        self.btn_reseteo_manual.pack(pady=10)

        self.bot_activo = False

        self.cargar_config()
        self.protocol("WM_DELETE_WINDOW", self.al_cerrar)
    
    def al_cerrar(self):
        self.guardar_config()
        self.destroy()

    def guardar_config(self):
        config = {
            "mesa": config_mesa,
            "item": coord_item,
            "java": coord_java_txt,
            "offset": self.offset_slider.get()
        }
        with open("config.json", "w") as f:
            json.dump(config, f)
    
    def cargar_config(self):
        global config_mesa, coord_item, coord_java_txt
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                config_mesa = config.get("mesa", config_mesa)
                coord_item = config.get("item", None)
                coord_java_txt = config.get("java", None)
                
                # Actualizar UI si hay datos
                if coord_item:
                    self.lbl_coords_itemslot.configure(text=f"Item: {coord_item}", text_color="green")
                    self.btn_ver_itemslot.configure(state="normal")

                if coord_java_txt:
                    self.lbl_java.configure(text=f"Java: {coord_java_txt}", text_color="green")
                if "offset" in config:
                    self.offset_slider.set(config["offset"])
                    self.actualizar_offset_label(config["offset"])
                if config_mesa["width"] > 100: # Si la mesa ya fue calibrada
                    texto_coords = f"X: {config_mesa['left']} Y: {config_mesa['top']} | W: {config_mesa['width']} H: {config_mesa['height']}"
                    self.lbl_coords_mesa.configure(text=texto_coords, text_color="green")
                    self.btn_ver.configure(state="normal")

    def actualizar_offset_label(self, val):
        self.lbl_offset.configure(text=f"{int(val)} px")

    def ver_puntos_java(self):
        if coord_java_txt is None:
            return
        self.withdraw()
        time.sleep(0.3)
        img = np.array(pyautogui.screenshot())
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        distancia = int(self.offset_slider.get())
        
        for i in range(10):
            px = coord_java_txt[0]
            py = coord_java_txt[1] + (i * distancia)
            cv2.circle(img_bgr, (px, py), 5, (0, 0, 255), -1)
            cv2.putText(img_bgr, str(i+1), (px + 10, py + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        titulo = "PREVISUALIZACION DE CLICS (Cualquier tecla para cerrar)"
        cv2.imshow(titulo, img_bgr)
        cv2.waitKey(0)
        try:
            cv2.destroyWindow(titulo)
        except cv2.error:
            pass
        self.deiconify()

    def esperar_clic(self, img, titulo):
        p = []
        def cb(e, x, y, f, pa):
            if e == cv2.EVENT_LBUTTONDOWN: p.append((x, y))
        cv2.namedWindow(titulo, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(titulo, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setMouseCallback(titulo, cb)
        while not p:
            cv2.imshow(titulo, img)
            if cv2.waitKey(1) & 0xFF == 27: break
        try:
            cv2.destroyWindow(titulo)
        except cv2.error:
            pass
        return p[0] if p else None

    def calibrar_mesa(self):
        global puntos_mesa, imagen_full, config_mesa
        puntos_mesa, params = [], {'terminado': False}
        self.withdraw()
        # Toma la captura solo para dejarte seleccionar los puntos
        img = np.array(pyautogui.screenshot())
        imagen_full = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        cv2.namedWindow("CALIBRACION MESA", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("CALIBRACION MESA", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setMouseCallback("CALIBRACION MESA", mouse_callback_lupa, params)
        
        while not params['terminado']:
            if cv2.waitKey(1) & 0xFF == 27: break
        cv2.destroyAllWindows()
        
        if len(puntos_mesa) == 4:
            pts_ord = ordenar_puntos(puntos_mesa)
            # Guardamos solo las coordenadas
            config_mesa = {
                "top": int(pts_ord[0][1]), 
                "left": int(pts_ord[0][0]), 
                "width": int(pts_ord[2][0] - pts_ord[0][0]), 
                "height": int(pts_ord[2][1] - pts_ord[0][1])
            }

            texto_coords = f"X: {config_mesa['left']} Y: {config_mesa['top']} | W: {config_mesa['width']} H: {config_mesa['height']}"
            self.lbl_coords_mesa.configure(text=texto_coords, text_color="green")

            self.guardar_config()
            self.btn_ver.configure(state="normal") # Ahora este botón llamará a la visualización con marcadores
        self.deiconify()

    # def mostrar_mosaico(self):
    #     if len(capturas_puntos) == 4:
    #         m = np.vstack((np.hstack((capturas_puntos[0], capturas_puntos[1])), np.hstack((capturas_puntos[3], capturas_puntos[2]))))
    #         cv2.imshow("Verificacion de Pixeles", m)
    #         cv2.waitKey(0)
    #         try: cv2.destroyWindow("Verificacion de Pixeles")
    #         except: pass

    def mostrar_marcadores_mesa(self):
        if config_mesa["width"] <= 100: return
        
        self.withdraw()
        time.sleep(0.3)
        img_full = np.array(pyautogui.screenshot())
        img_full = cv2.cvtColor(img_full, cv2.COLOR_RGB2BGR)
        
        x, y = config_mesa["left"], config_mesa["top"]
        w, h = config_mesa["width"], config_mesa["height"]
        
        # Definimos las 4 esquinas exactas guardadas
        puntos = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        lupas = []
        
        for p in puntos:
            px, py = p[0], p[1]
            # Extraer parche de 30x30 alrededor del punto
            y1, y2 = max(0, py - 15), min(img_full.shape[0], py + 15)
            x1, x2 = max(0, px - 15), min(img_full.shape[1], px + 15)
            
            patch = img_full[y1:y2, x1:x2]
            
            # Crear la lupa (Zoom)
            lupa = cv2.resize(patch, (250, 250), interpolation=cv2.INTER_NEAREST)
            
            # Dibujar la cruz roja central (+) en la lupa
            c = 125 # Centro de 250
            cv2.line(lupa, (c - 20, c), (c + 20, c), (0, 0, 255), 2)
            cv2.line(lupa, (c, c - 20), (c, c + 20), (0, 0, 255), 2)
            
            lupas.append(lupa)

        # Crear mosaico 2x2 (Arriba Izq, Arriba Der / Abajo Der, Abajo Izq)
        fila_sup = np.hstack((lupas[0], lupas[1]))
        fila_inf = np.hstack((lupas[3], lupas[2]))
        mosaico = np.vstack((fila_sup, fila_inf))

        # Añadir texto de ayuda
        cv2.putText(mosaico, "ESC para cerrar", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("ZOOM DE COORDENADAS GUARDADAS", mosaico)
        cv2.waitKey(0)
        try:
            cv2.destroyWindow("ZOOM DE COORDENADAS GUARDADAS")
        except:
            pass
        self.deiconify()

    def calibrar_item(self):
        self.withdraw(); time.sleep(0.3)
        img = np.array(pyautogui.screenshot())
        res = self.esperar_clic(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), "CLIC EN EL ITEM DE MINECRAFT")
        if res: 
            global coord_item
            coord_item = res
            self.lbl_coords_itemslot.configure(text=f"Item: {res}", text_color="green")
            self.btn_ver_itemslot.configure(state="normal")
        self.deiconify()

    def calibrar_java(self):
        self.withdraw(); time.sleep(0.3)
        img = np.array(pyautogui.screenshot())
        res = self.esperar_clic(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), "CLIC EN EL TEXTBOX DEL ENCHANT CRACKER")
        if res: 
            global coord_java_txt
            coord_java_txt = res
            self.lbl_java.configure(text=f"Java: {res}", text_color="green")
        self.deiconify()

    def comparar_con_patrones(self, img_bin):
        for filename in os.listdir('patrones'):
            patron = cv2.imread(f'patrones/{filename}', 0)
            if patron is not None and img_bin.shape == patron.shape:
                if cv2.minMaxLoc(cv2.matchTemplate(img_bin, patron, cv2.TM_CCOEFF_NORMED))[1] > 0.98:
                    return filename.replace(".png", "")
        return "0"

    def procesar_un_ciclo(self, i):
        pyautogui.moveTo(coord_item[0], coord_item[1])
        pyautogui.click()
        time.sleep(0.25)
        pyautogui.click()
        pyautogui.moveRel(0, 30) 
        time.sleep(0.25)

        with mss.mss() as sct:
            img = np.array(sct.grab(config_mesa))
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            mask_slots = cv2.inRange(img_bgr, np.array([114, 145, 160])-20, np.array([114, 145, 160])+20)
            cnts, _ = cv2.findContours(mask_slots, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            ranuras = sorted([cv2.boundingRect(c) for c in cnts if cv2.boundingRect(c)[2] > 40], key=lambda r: r[1])
            niveles = []
            for r in ranuras[:3]:
                roi = img_bgr[r[1]:r[1]+r[3], r[0]:r[0]+r[2]]
                mask_num = cv2.inRange(roi, np.array([32, 255, 128])-2, np.array([32, 255, 128])+2)
                coords = cv2.findNonZero(mask_num)
                if coords is not None:
                    rx, ry, rw, rh = cv2.boundingRect(coords)
                    niveles.append(self.comparar_con_patrones(mask_num[ry:ry+rh, rx:rx+rw]))
                else: niveles.append("0")

        distancia = int(self.offset_slider.get())
        pyautogui.click(coord_java_txt[0], coord_java_txt[1] + (i * distancia))
        time.sleep(0.1)
        for idx, val in enumerate(niveles):
            pyautogui.write(str(val))
            if idx < 2: pyautogui.press('tab')
        pyautogui.press('enter')
        
        self.after(0, lambda: self.st_label.configure(text=f"Ciclo {i+1}/10", text_color="cyan"))

    def bucle_10(self):
        time.sleep(0.5)
        for i in range(10):
            if not self.bot_activo: break
            self.procesar_un_ciclo(i)
            # time.sleep(0.4)
        self.after(0, self.toggle_bot)

    def toggle_bot(self):
        self.bot_activo = not self.bot_activo
        self.btn_bot.configure(text="DETENER" if self.bot_activo else "INICIAR 10 CICLOS", 
                               fg_color="red" if self.bot_activo else "green")
        if self.bot_activo: threading.Thread(target=self.bucle_10, daemon=True).start()

    # --- LÓGICA DE RESETEO (PASO 3) ---
    def iniciar_reseteo_thread(self):
        if coord_item is None:
            self.st_label.configure(text="¡Falta calibrar Item!", text_color="red")
            return
        threading.Thread(target=self.ejecutar_reseteo, daemon=True).start()

    def ejecutar_reseteo(self):
        try:
            cantidad = int(self.txt_cantidad_reseteo.get())
        except ValueError:
            self.after(0, lambda: self.st_label.configure(text="Cantidad inválida", text_color="red"))
            return

        self.after(0, lambda: self.st_label.configure(text=f"Reseteando {cantidad} veces...", text_color="orange"))

        time.sleep(0.5)

        for i in range(cantidad+1):
            # Esta línea actualiza el texto de la interfaz en cada vuelta del bucle
            self.after(0, lambda n=i: self.st_label.configure(
                text=f"Terminado: {n} / {cantidad}", 
                text_color="#f39c12"
            ))
            
            pyautogui.moveTo(coord_item[0], coord_item[1])
            pyautogui.click()
            time.sleep(0.25)
            pyautogui.click()
            time.sleep(0.25)
            
        
        self.after(0, lambda: self.st_label.configure(text="Reseteo finalizado", text_color="green"))

    def ver_item_slot(self):
        if coord_item is None:
            return
        
        self.withdraw()
        time.sleep(0.3)
        # Captura instantánea
        img_full = np.array(pyautogui.screenshot())
        img_full = cv2.cvtColor(img_full, cv2.COLOR_RGB2BGR)
        
        px, py = coord_item[0], coord_item[1]
        
        # Coordenada del punto 30px abajo
        px_offset, py_offset = px, py + 30
        
        # Ajustamos el parche para que sea un poco más alto y quepan ambos puntos
        # Extraeremos 80x80 para tener buen margen visual
        y1, y2 = max(0, py - 20), min(img_full.shape[0], py + 60)
        x1, x2 = max(0, px - 40), min(img_full.shape[1], px + 40)
        
        patch = img_full[y1:y2, x1:x2]
        
        # Reescalar para ver el zoom (proporcional al recorte)
        lupa = cv2.resize(patch, (300, 400), interpolation=cv2.INTER_NEAREST)
        
        # --- CÁLCULO DE POSICIONES EN LA LUPA ---
        # El punto original (px, py) estará en una posición relativa dentro del parche
        # multiplicada por el factor de escala
        scale_x = 300 / (x2 - x1)
        scale_y = 400 / (y2 - y1)
        
        # Dibujar Cruz Roja en el punto de clic original (+)
        cx = int((px - x1) * scale_x)
        cy = int((py - y1) * scale_y)
        cv2.line(lupa, (cx - 15, cy), (cx + 15, cy), (0, 0, 255), 2)
        cv2.line(lupa, (cx, cy - 15), (cx, cy + 15), (0, 0, 255), 2)
        
        # Dibujar Punto Amarillo en la posición +30px (donde se mueve el mouse después)
        cx_off = int((px_offset - x1) * scale_x)
        cy_off = int((py_offset - y1) * scale_y)
        cv2.circle(lupa, (cx_off, cy_off), 8, (0, 255, 255), -1) 
        cv2.putText(lupa, "+30px", (cx_off + 15, cy_off), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        cv2.imshow("ZOOM ITEM SLOT Y OFFSET (ESC)", lupa)
        cv2.waitKey(0)
        try:
            cv2.destroyWindow("ZOOM ITEM SLOT Y OFFSET (ESC)")
        except:
            pass
        self.deiconify()


if __name__ == "__main__":
    app = App()
    app.mainloop()